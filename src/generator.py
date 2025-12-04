import argparse
import os
import xmlschema
from typing import Dict, List, Optional
import yaml
from pathlib import Path
import json
import logging

try:
    from src.xsdtojson import xsd_to_json_schema
except ImportError:
    from xsdtojson import xsd_to_json_schema

try:
    from .xsd_converter import LinkMLConverter
    from .utils import ensure_schema_serializable
except ImportError:
    from xsd_converter import LinkMLConverter
    from utils import ensure_schema_serializable

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_doc_overrides(path: Optional[Path] = None) -> Dict:
    candidate_paths: List[Path] = []
    if path:
        candidate_paths.append(Path(path))
    else:
        default_path = Path(__file__).resolve().parent / "config" / "doc_overrides.yaml"
        candidate_paths.append(default_path)
    
    for candidate in candidate_paths:
        try:
            if candidate and candidate.exists():
                with candidate.open("r") as fh:
                    data = yaml.safe_load(fh) or {}
                    logger.debug(f"Loaded documentation overrides from {candidate}")
                    return data
        except Exception as exc:
            logger.warning(f"Failed to load documentation overrides from {candidate}: {exc}")
    return {}


def filter_json_schema(json_schema: Dict, top_level_elements: List[str]) -> Dict:
    filtered_props = {}
    filtered_defs = {}
    
    for element in top_level_elements:
        if element in json_schema.get("properties", {}):
            filtered_props[element] = json_schema["properties"][element]
        
        if "definitions" in json_schema:
            for def_name, def_value in json_schema["definitions"].items():
                if def_name.startswith(element) or def_name in [
                    ref.split("/")[-1] for ref in filtered_props.get(element, {}).get("$ref", "").split()
                ]:
                    filtered_defs[def_name] = def_value
    
    json_schema["properties"] = filtered_props
    if filtered_defs:
        json_schema["definitions"] = filtered_defs
    
    return json_schema


def write_json_schema(json_schema: Dict, output_path: str):
    try:
        out_dir = os.path.dirname(output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(output_path, 'w') as jf:
            json.dump(json_schema, jf, indent=2)
    except Exception as e:
        logger.warning(f"Failed writing JSON Schema to {output_path}: {e}")


def partition_schema(linkml_schema: Dict, output_path: str):
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    
    for class_name, class_def in list(linkml_schema["classes"].items()):
        partitioned_schema = {
            "id": linkml_schema["id"],
            "name": linkml_schema["name"],
            "title": linkml_schema["title"],
            "description": linkml_schema["description"],
            "license": linkml_schema["license"],
            "version": linkml_schema["version"],
            "prefixes": linkml_schema["prefixes"],
            "default_prefix": linkml_schema["default_prefix"],
            "types": linkml_schema.get("types", {}),
            "classes": {class_name: class_def},
            "slots": {}
        }
        
        class_slots = set(class_def.get("slots", []) or [])
        slot_registry = linkml_schema.get("slots", {})
        for slot_name in class_slots:
            if slot_name in slot_registry:
                partitioned_schema["slots"][slot_name] = slot_registry[slot_name]
        
        referenced_classes = set()
        for slot_name in class_slots:
            slot_def = slot_registry.get(slot_name, {})
            rng = slot_def.get("range")
            if rng and rng in linkml_schema["classes"] and rng not in partitioned_schema["classes"]:
                referenced_classes.add(rng)
        
        for ref_cls in referenced_classes:
            partitioned_schema["classes"][ref_cls] = linkml_schema["classes"][ref_cls]
        
        class_file_path = os.path.join(output_path, f"{class_name}.yaml")
        with open(class_file_path, 'w') as f:
            yaml.dump(partitioned_schema, f, sort_keys=False)
    
    logger.info(f"Successfully partitioned schema into {len(linkml_schema['classes'])} files in {output_path}")


def write_linkml_schema(linkml_schema: Dict, output_path: str):
    if not output_path.endswith('.yaml') and not output_path.endswith('.yml'):
        output_path = f"{output_path}.yaml"
    
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
    
    with open(output_path, 'w') as f:
        yaml.dump(linkml_schema, f, sort_keys=False, default_flow_style=False)
    
    logger.info(f"Successfully generated LinkML schema at {output_path}")


def generate_linkml_schema(
    ome_xsd_path: str,
    output_path: Optional[str] = None,
    top_level_elements: Optional[List[str]] = None,
    partition: bool = False,
    schema_id: Optional[str] = None,
    schema_name: Optional[str] = None,
    schema_title: Optional[str] = None,
    default_prefix: Optional[str] = None,
    extra_prefixes: Optional[Dict[str, str]] = None,
    json_output_path: Optional[str] = None,
    doc_overrides_path: Optional[str] = None
) -> Dict:
    try:
        xsd = xmlschema.XMLSchema(ome_xsd_path)
        json_schema = xsd_to_json_schema(ome_xsd_path)
        
        if top_level_elements:
            json_schema = filter_json_schema(json_schema, top_level_elements)
        
        if json_output_path:
            write_json_schema(json_schema, json_output_path)
        
        metadata = {
            "schema_id": schema_id,
            "schema_name": schema_name,
            "schema_title": schema_title,
            "default_prefix": default_prefix,
            "extra_prefixes": extra_prefixes or {}
        }
        
        doc_overrides = load_doc_overrides(doc_overrides_path)
        converter = LinkMLConverter(json_schema, xsd, metadata, doc_overrides)
        linkml_schema = converter.convert()
        
        if output_path:
            if partition and "classes" in linkml_schema:
                partition_schema(linkml_schema, output_path)
            else:
                write_linkml_schema(linkml_schema, output_path)
        
        return linkml_schema
    
    except Exception as e:
        logger.error(f"Error generating LinkML schema: {str(e)}")
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate LinkML schema from an XSD")
    parser.add_argument("xsd_path", help="Path to the XSD file")
    parser.add_argument("--output", help="Output path for the LinkML schema")
    parser.add_argument("--elements", help="Comma-separated list of top-level elements to include")
    parser.add_argument("--partition", action="store_true", help="Partition the schema into separate files")
    parser.add_argument("--schema-id", help="Override schema id (default derives from target namespace)")
    parser.add_argument("--name", dest="schema_name", help="Override schema name (default derives from namespace)")
    parser.add_argument("--title", dest="schema_title", help="Override schema title")
    parser.add_argument("--default-prefix", dest="default_prefix", help="Override default prefix")
    parser.add_argument("--extra-prefix", action='append', default=[], 
                       help="Extra prefix mapping in form prefix=URI; can be repeated")
    parser.add_argument("--json-out", dest="json_output", help="Optional path to write the intermediate JSON Schema")
    parser.add_argument("--doc-overrides", dest="doc_overrides", help="Path to YAML file with documentation overrides")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    top_level_elements = args.elements.split(",") if args.elements else None
    
    extra_prefixes = {}
    for item in args.extra_prefix:
        try:
            k, v = item.split('=', 1)
            extra_prefixes[k.strip()] = v.strip()
        except ValueError:
            logger.warning(f"Invalid --extra-prefix value (expected prefix=URI): {item}")
    
    generate_linkml_schema(
        args.xsd_path,
        args.output,
        top_level_elements,
        args.partition,
        schema_id=args.schema_id,
        schema_name=args.schema_name,
        schema_title=args.schema_title,
        default_prefix=args.default_prefix,
        extra_prefixes=extra_prefixes if extra_prefixes else None,
        json_output_path=args.json_output,
        doc_overrides_path=args.doc_overrides,
    )
