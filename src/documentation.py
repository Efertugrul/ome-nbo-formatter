from typing import Dict, List, Optional
from collections import defaultdict

try:
    from .utils import extract_text, local_name
except ImportError:
    from utils import extract_text, local_name

TIER_SUBSET_LOOKUP = {
    "1": "NBO_Tier1",
    "2": "NBO_Tier2",
    "3": "NBO_Tier3"
}


def split_doc_metadata(doc_text: str) -> tuple[str, Dict[str, List[str]]]:
    metadata: Dict[str, List[str]] = defaultdict(list)
    description_lines: List[str] = []
    
    for raw_line in doc_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        
        if "=" in line:
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if not key:
                description_lines.append(line)
                continue
            if key.lower() == "description":
                description_lines.append(value)
            else:
                metadata[key].append(value)
        else:
            description_lines.append(line)
    
    description = "\n".join(description_lines).strip()
    return description, metadata


def apply_metadata_to_target(target: Dict, metadata: Dict[str, List[str]]):
    if not metadata:
        return
    
    tier_values: List[str] = []
    for key in list(metadata.keys()):
        if key.lower() == "tier":
            tier_values.extend(metadata.pop(key) or [])
    
    if tier_values:
        subset_list = target.setdefault("in_subset", [])
        for raw_value in tier_values:
            if not raw_value:
                continue
            for token in raw_value.replace(",", " ").split():
                subset_name = TIER_SUBSET_LOOKUP.get(token.strip())
                if subset_name and subset_name not in subset_list:
                    subset_list.append(subset_name)
    
    if not metadata:
        return
    
    annotations = target.setdefault("annotations", {})
    for key, values in metadata.items():
        if not values:
            continue
        ann_base = key.replace(" ", "_")
        for idx, value in enumerate(values):
            ann_key = ann_base if idx == 0 and ann_base not in annotations else f"{ann_base}_{idx}"
            annotations[ann_key] = {
                "tag": key,
                "value": value
            }


def record_appinfo_entry(target: Dict, node):
    if node is None:
        return
    
    name = local_name(node.tag)
    value = (node.text or "").strip() or "true"
    annotations = target.setdefault("annotations", {})
    key = name if name not in annotations else f"{name}_{len(annotations)}"
    annotations[key] = {
        "tag": name,
        "value": value
    }


def apply_appinfo_metadata(target: Dict, annotation):
    if annotation is None:
        return
    
    elem = getattr(annotation, "elem", None)
    if elem is None:
        return
    
    try:
        for appinfo in elem.findall('.//{*}appinfo'):
            for node in list(appinfo):
                if local_name(node.tag).lower() == "xsdfu":
                    for child in list(node):
                        record_appinfo_entry(target, child)
                else:
                    record_appinfo_entry(target, node)
    except Exception:
        pass


def apply_doc_metadata(target: Dict, doc_value):
    if not doc_value:
        return
    
    clean_text = coerce_description(doc_value)
    if not clean_text:
        return
    
    description, metadata = split_doc_metadata(clean_text)
    if description:
        target["description"] = description
    
    apply_metadata_to_target(target, metadata)


def coerce_description(value) -> str:
    try:
        if value is None:
            return ""
        return extract_text(value)
    except Exception:
        return extract_text(value)


def get_documentation(annotation) -> Optional[str]:
    if not annotation:
        return None
    
    texts = []
    
    try:
        if hasattr(annotation, 'documentation'):
            doc = annotation.documentation
            if doc:
                texts.append(extract_text(doc))
    except Exception:
        pass
    
    try:
        if hasattr(annotation, 'elem') and annotation.elem is not None:
            for child in annotation.elem:
                if str(child.tag).endswith('documentation'):
                    texts.append((child.text or "").strip())
    except Exception:
        pass
    
    try:
        if hasattr(annotation, 'elem') and hasattr(annotation.elem, 'findall'):
            doc_elems = annotation.elem.findall('.//{*}documentation')
            for de in doc_elems:
                texts.append((de.text or "").strip())
    except Exception:
        pass
    
    if not texts:
        try:
            annotation_str = str(annotation)
            if 'documentation' in annotation_str:
                import re
                match = re.search(r'<documentation>(.*?)</documentation>', annotation_str, re.DOTALL)
                if match:
                    texts.append(match.group(1).strip())
        except Exception:
            pass
    
    merged = "\n".join([t for t in texts if t])
    return merged or None

