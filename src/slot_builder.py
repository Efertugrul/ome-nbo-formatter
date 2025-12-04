from typing import Dict, List, Optional

try:
    from .utils import local_name, map_xsd_primitive, PRIMITIVE_RANGES, sanitize_enum_name
    from .documentation import get_documentation, apply_doc_metadata, apply_appinfo_metadata
except ImportError:
    from utils import local_name, map_xsd_primitive, PRIMITIVE_RANGES, sanitize_enum_name
    from documentation import get_documentation, apply_doc_metadata, apply_appinfo_metadata


class SlotBuilder:
    def __init__(self, linkml_schema: Dict, reference_resolver, attr_description_overrides: Dict):
        self.linkml_schema = linkml_schema
        self.reference_resolver = reference_resolver
        self.attr_description_overrides = attr_description_overrides
    
    def ensure_enum_for_slot(self, class_name: str, attr_name: str, values: List) -> str:
        enum_name = sanitize_enum_name(class_name, attr_name)
        if enum_name not in self.linkml_schema["enums"]:
            self.linkml_schema["enums"][enum_name] = {
                "permissible_values": {str(v): {} for v in values}
            }
        return enum_name
    
    def slot_from_attribute(self, owner_class: str, attr_name: str, attr_obj) -> Dict:
        slot = {"range": "string"}
        attr_type = getattr(attr_obj, "type", None)
        slot["range"] = map_xsd_primitive(attr_type)
        type_name_local = local_name(getattr(attr_type, "name", None))
        attr_name_lower = attr_name.lower()
        
        if attr_name_lower == "id" and self.reference_resolver.class_is_ref_like(owner_class):
            target_candidate = self.reference_resolver.reference_target_for_class(owner_class, type_name_local)
            if target_candidate:
                slot["range"] = target_candidate
        
        doc = get_documentation(getattr(attr_obj, "annotation", None))
        custom_doc = self.attr_description_overrides.get(owner_class, {}).get(attr_name)
        apply_doc_metadata(slot, doc)
        if custom_doc:
            slot["description"] = custom_doc
        apply_appinfo_metadata(slot, getattr(attr_obj, "annotation", None))
        
        enum_values = []
        if attr_type is not None:
            enum_values = [str(v) for v in getattr(attr_type, "enumeration", []) or []]
        if enum_values:
            slot["range"] = self.ensure_enum_for_slot(owner_class, attr_name, enum_values)
        
        facets = getattr(attr_type, "facets", {}) if attr_type is not None else {}
        pattern_facet = facets.get("{http://www.w3.org/2001/XMLSchema}pattern")
        if pattern_facet is not None:
            pattern_value = getattr(pattern_facet, "pattern", None)
            if not pattern_value:
                facet_patterns = getattr(pattern_facet, "patterns", None)
                if facet_patterns:
                    pattern_value = getattr(facet_patterns[0], "pattern", None)
            if not pattern_value:
                facet_regexps = getattr(pattern_facet, "regexps", None)
                if facet_regexps:
                    pattern_value = getattr(facet_regexps[0], "pattern", None)
            if pattern_value:
                slot["pattern"] = pattern_value
        
        min_inclusive = getattr(attr_type, "min_value", None)
        if min_inclusive is not None:
            slot["minimum_value"] = min_inclusive
        
        max_inclusive = getattr(attr_type, "max_value", None)
        if max_inclusive is not None:
            slot["maximum_value"] = max_inclusive
        
        if getattr(attr_obj, "use", None) == "required":
            slot["required"] = True
        
        if attr_name_lower == "id" or (type_name_local and type_name_local.endswith("ID")):
            slot["identifier"] = True
        
        return slot
    
    def build_child_element_slot(self, parent_class: str, child_qname, child) -> Optional[tuple]:
        raw_name = child_qname or getattr(child, "name", None)
        child_name = local_name(raw_name)
        if not child_name:
            child_name = local_name(getattr(child, "name", None))
        if not child_name:
            return None
        
        child_doc = get_documentation(getattr(child, "annotation", None))
        slot_def: Dict[str, any] = {}
        child_range = None
        
        ref_target = getattr(child, "ref", None)
        if ref_target is not None:
            ref_name = getattr(ref_target, "name", None)
            child_range = local_name(ref_name if ref_name else ref_target)
        else:
            child_type = getattr(child, "type", None)
            if child_type is not None and getattr(child_type, "is_complex", lambda: False)():
                if getattr(child_type, "name", None):
                    child_range = local_name(child_type.name)
                else:
                    child_range = child_name
            elif child_type is not None:
                child_range = map_xsd_primitive(child_type)
        
        slot_def["range"] = child_range if child_range else "string"
        
        mino = getattr(child, "min_occurs", None)
        maxo = getattr(child, "max_occurs", None)
        occurs = getattr(child, "occurs", None)
        occurs_tuple = None
        if isinstance(occurs, tuple):
            occurs_tuple = occurs
        elif hasattr(occurs, "__iter__"):
            occurs_tuple = tuple(occurs)
        
        if maxo is None and occurs_tuple:
            try:
                maxo = occurs_tuple[-1]
            except IndexError:
                maxo = None
        
        if isinstance(mino, int) and mino >= 1:
            slot_def["required"] = True
        if maxo == "unbounded" or (maxo is None and occurs_tuple and occurs_tuple[-1] is None) or (isinstance(maxo, int) and maxo > 1):
            slot_def["multivalued"] = True
        
        if child_doc:
            apply_doc_metadata(slot_def, child_doc)
        else:
            slot_def.setdefault("description", f"Child element {child_name} of {parent_class}")
        
        apply_appinfo_metadata(slot_def, getattr(child, "annotation", None))
        return slot_def, child_name, child_range

