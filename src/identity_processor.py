from typing import Dict, List, Set
import json
from xmlschema.validators.identities import XsdKey, XsdUnique, XsdKeyref

try:
    from .utils import local_name
except ImportError:
    from utils import local_name


class IdentityProcessor:
    def __init__(self, linkml_schema: Dict, reference_resolver, ensure_class_func, add_attribute_func, add_unique_key_func):
        self.linkml_schema = linkml_schema
        self.reference_resolver = reference_resolver
        self.ensure_class = ensure_class_func
        self.add_attribute = add_attribute_func
        self.add_unique_key = add_unique_key_func
    
    def apply_local_identities(self, class_name: str, elem_def):
        local_ids = getattr(elem_def, "identities", None)
        if not local_ids:
            return
        
        cls = self.ensure_class(class_name)
        annotations = cls.setdefault("annotations", {})
        for ident in local_ids:
            try:
                ident_name = local_name(getattr(ident, "name", "") or "local_identity")
                selector_path = getattr(getattr(ident, "selector", None), "path", "") or ""
                field_paths = [getattr(field, "path", "") for field in getattr(ident, "fields", []) or []]
                annotations[f"local_identity_{ident_name}"] = {
                    "tag": "local_identity",
                    "value": json.dumps({
                        "type": ident.__class__.__name__,
                        "selector": selector_path,
                        "fields": field_paths
                    })
                }
            except Exception:
                continue
    
    def process_identities(self, xsd):
        identities = getattr(xsd, "identities", None)
        key_target_map: Dict[str, Set[str]] = {}
        
        if identities:
            for ident_name, ident in identities.items():
                if isinstance(ident, (XsdKey, XsdUnique)):
                    selector = getattr(ident, "selector", None)
                    if selector is None:
                        continue
                    selector_path = getattr(selector, "path", "") or ""
                    selector_paths = [p.strip() for p in selector_path.split("|")] if selector_path else []
                    if not selector_paths:
                        selector_paths = [selector_path]
                    
                    slot_names: List[str] = []
                    for field in getattr(ident, "fields", []) or []:
                        field_path = getattr(field, "path", "") or ""
                        if not field_path:
                            continue
                        field_segment = field_path.split("/")[-1]
                        if field_segment.startswith("@"):
                            field_segment = field_segment[1:]
                        field_segment = local_name(field_segment)
                        if field_segment:
                            slot_names.append(field_segment)
                    
                    if not slot_names:
                        continue
                    
                    key_local_name = local_name(ident_name)
                    for path in selector_paths:
                        path = path.strip()
                        if not path:
                            continue
                        segments = [seg for seg in path.replace("//", "/").split("/") if seg and seg != "."]
                        if not segments:
                            continue
                        target_segment = segments[-1]
                        if target_segment in ("*", "."):
                            continue
                        target_class = local_name(target_segment)
                        if not target_class:
                            continue
                        key_target_map.setdefault(key_local_name, set()).add(target_class)
                        self.add_unique_key(target_class, key_local_name, slot_names)
                
                elif isinstance(ident, XsdKeyref):
                    refer = getattr(ident, "refer", None)
                    if refer is None:
                        continue
                    refer_name = getattr(refer, "name", None)
                    refer_key = local_name(refer_name) if refer_name else local_name(refer)
                    target_classes = key_target_map.get(refer_key) or set()
                    selector = getattr(ident, "selector", None)
                    selector_path = getattr(selector, "path", "") if selector else ""
                    segments = [seg for seg in selector_path.replace("//", "/").split("/") if seg and seg != "."]
                    if not segments:
                        continue
                    source_segment = segments[-1]
                    if source_segment in ("*", "."):
                        continue
                    source_class = local_name(source_segment)
                    range_target = self.reference_resolver.select_keyref_range(target_classes)
                    for field in getattr(ident, "fields", []) or []:
                        field_path = getattr(field, "path", "") or ""
                        if not field_path:
                            continue
                        field_segment = field_path.split("/")[-1]
                        if field_segment.startswith("@"):
                            field_segment = field_segment[1:]
                        slot_name = local_name(field_segment)
                        if not slot_name or not range_target:
                            continue
                        slot_def = {
                            "range": range_target,
                            "annotations": {
                                f"references_{range_target}": {
                                    "tag": "references",
                                    "value": range_target
                                }
                            }
                        }
                        self.add_attribute(source_class, slot_name, slot_def)

