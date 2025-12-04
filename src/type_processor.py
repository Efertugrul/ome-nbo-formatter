from typing import Dict, Optional
import xmlschema

try:
    from .utils import local_name, PRIMITIVE_RANGES
    from .documentation import get_documentation, apply_doc_metadata, apply_appinfo_metadata
except ImportError:
    from utils import local_name, PRIMITIVE_RANGES
    from documentation import get_documentation, apply_doc_metadata, apply_appinfo_metadata


class TypeProcessor:
    def __init__(self, linkml_schema: Dict, slot_builder, constraint_handler, 
                 ensure_class_func, add_attribute_func):
        self.linkml_schema = linkml_schema
        self.slot_builder = slot_builder
        self.constraint_handler = constraint_handler
        self.ensure_class = ensure_class_func
        self.add_attribute = add_attribute_func
    
    def populate_complex_type(self, class_name: str, type_def, fallback_description: Optional[str] = None):
        if type_def is None:
            return
        
        cls = self.ensure_class(class_name, fallback_description or f"Complex type {class_name}")
        if hasattr(type_def, "annotation") and type_def.annotation:
            doc = get_documentation(type_def.annotation)
            apply_doc_metadata(cls, doc)
            apply_appinfo_metadata(cls, type_def.annotation)
        
        for attr_qname, attr in getattr(type_def, "attributes", {}).items():
            attr_local = local_name(attr_qname)
            slot = self.slot_builder.slot_from_attribute(class_name, attr_local, attr)
            self.add_attribute(class_name, attr_local, slot)
        
        content = getattr(type_def, "content", None)
        if content is not None:
            if hasattr(content, "elements"):
                iterator = content.elements.items()
            elif hasattr(content, "iter_elements"):
                iterator = ((getattr(child, "name", None), child) for child in content.iter_elements())
            else:
                iterator = []
            for child_qname, child in iterator:
                self.add_child_element(class_name, child_qname, child)
            self.constraint_handler.collect_choice_constraints(class_name, content)
    
    def add_child_element(self, parent_class: str, child_qname, child):
        result = self.slot_builder.build_child_element_slot(parent_class, child_qname, child)
        if result is None:
            return
        
        slot_def, child_name, child_range = result
        
        if child_range and child_range not in PRIMITIVE_RANGES:
            self.ensure_class(child_range)
        
        if child_range == child_name:
            child_type = getattr(child, "type", None)
            if child_type is not None and not getattr(child_type, "name", None):
                self.populate_complex_type(child_name, child_type, 
                                         fallback_description=f"Inline complex type for {child_name}")
        
        self.add_attribute(parent_class, child_name, slot_def)
    
    def process_complex_types(self, xsd: xmlschema.XMLSchema, inheritance_map: Dict[str, str]):
        complex_types = {}
        for type_name, type_def in xsd.types.items():
            if not type_def.is_complex():
                continue
            local = local_name(type_name) if isinstance(type_name, str) else local_name(getattr(type_def, "name", None))
            if not local:
                continue
            complex_types[local] = type_def
        
        for type_name, type_def in complex_types.items():
            self.populate_complex_type(type_name, type_def, fallback_description=f"Complex type {type_name}")
            cls = self.ensure_class(type_name)
            if type_name in inheritance_map:
                base_type = inheritance_map[type_name]
                if base_type in self.linkml_schema["classes"]:
                    cls["is_a"] = base_type
    
    def process_elements(self, xsd: xmlschema.XMLSchema, inheritance_map: Dict[str, str], identity_processor):
        for elem_name, elem_def in xsd.elements.items():
            element_name = str(elem_name).split("}")[-1]
            cls = self.ensure_class(element_name, f"The {element_name} element from the XML Schema.")
            
            elem_type = getattr(elem_def, 'type', None)
            processed_inline_type = False
            if elem_type is not None and hasattr(elem_type, "is_complex") and elem_type.is_complex():
                if not getattr(elem_type, "name", None):
                    self.populate_complex_type(element_name, elem_type, 
                                             fallback_description=cls.get("description"))
                    processed_inline_type = True
            
            if hasattr(elem_def, 'annotation') and elem_def.annotation:
                doc = get_documentation(elem_def.annotation)
                apply_doc_metadata(cls, doc)
                apply_appinfo_metadata(cls, elem_def.annotation)
            
            try:
                if getattr(elem_def, 'abstract', False) or getattr(elem_def, 'is_abstract', False):
                    cls["abstract"] = True
            except Exception:
                pass
            
            try:
                if hasattr(elem_def, 'type') and hasattr(elem_def.type, 'name') and elem_def.type.name:
                    direct_type_name = str(elem_def.type.name).split("}")[-1]
                    if direct_type_name in self.linkml_schema["classes"] and direct_type_name != element_name:
                        cls["is_a"] = direct_type_name
            except Exception:
                pass
            
            try:
                sg = getattr(elem_def, 'substitution_group', None)
                if sg:
                    head_name = str(sg).split("}")[-1]
                    head_cls = self.ensure_class(head_name, f"Head of substitution group {head_name}")
                    head_cls["abstract"] = True
                    cls["is_a"] = head_name
            except Exception:
                pass
            
            if hasattr(elem_def, 'type') and hasattr(elem_def.type, 'content'):
                type_content = elem_def.type.content
                if hasattr(type_content, 'base_type') and type_content.base_type:
                    base_type = type_content.base_type
                    if hasattr(base_type, 'name'):
                        base_name = str(base_type.name).split("}")[-1]
                        if base_name in self.linkml_schema["classes"]:
                            cls["is_a"] = base_name
            
            if not processed_inline_type:
                try:
                    if elem_type is not None and hasattr(elem_type, 'content'):
                        content = elem_type.content
                        if hasattr(content, "elements"):
                            iterator = content.elements.items()
                        elif hasattr(content, "iter_elements"):
                            iterator = ((getattr(child, "name", None), child) for child in content.iter_elements())
                        else:
                            iterator = []
                        for child_qname, child in iterator:
                            self.add_child_element(element_name, child_qname, child)
                        self.constraint_handler.collect_choice_constraints(element_name, content)
                except Exception:
                    pass
            
            identity_processor.apply_local_identities(element_name, elem_def)

