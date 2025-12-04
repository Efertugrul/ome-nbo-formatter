from typing import Dict, Optional, Set

try:
    from .utils import local_name
except ImportError:
    from utils import local_name


class ReferenceResolver:
    def __init__(self, linkml_schema: Dict, inheritance_map: Dict[str, str], known_class_names: Set[str]):
        self.linkml_schema = linkml_schema
        self.inheritance_map = inheritance_map
        self.known_class_names = known_class_names
    
    def class_is_ref_like(self, class_name: Optional[str]) -> bool:
        if not class_name:
            return False
        visited: Set[str] = set()
        current = class_name
        while current:
            if current.endswith("Ref") or current == "Reference":
                return True
            if current in visited:
                break
            visited.add(current)
            cls_def = self.linkml_schema["classes"].get(current)
            base = None
            if cls_def:
                base = cls_def.get("is_a")
            if not base:
                base = self.inheritance_map.get(current)
            current = base
        return False
    
    def reference_target_for_class(self, owner_class: str, type_name_local: Optional[str]) -> Optional[str]:
        if owner_class and owner_class.endswith("Ref"):
            candidate = owner_class[:-3]
            if candidate in self.known_class_names:
                return candidate
        
        visited: Set[str] = set()
        current = owner_class
        while current:
            if current in visited:
                break
            visited.add(current)
            cls_def = self.linkml_schema["classes"].get(current)
            base = None
            if cls_def:
                base = cls_def.get("is_a")
                if base and base.endswith("Ref"):
                    candidate = base[:-3]
                    if candidate in self.known_class_names:
                        return candidate
            if not base:
                base = self.inheritance_map.get(current)
            current = base
        
        if type_name_local and type_name_local.endswith("ID"):
            candidate = type_name_local[:-2]
            if candidate in self.known_class_names:
                return candidate
        return None
    
    def select_keyref_range(self, target_classes: Set[str]) -> Optional[str]:
        if not target_classes:
            return None
        if len(target_classes) == 1:
            return next(iter(target_classes))
        
        from typing import List
        ancestor_lists: List[List[str]] = []
        for cls_name in target_classes:
            if not cls_name:
                continue
            ancestors: List[str] = []
            current = cls_name
            visited: Set[str] = set()
            while current and current not in visited:
                ancestors.append(current)
                visited.add(current)
                cls_def = self.linkml_schema["classes"].get(current)
                base = None
                if cls_def:
                    base = cls_def.get("is_a")
                if not base:
                    base = self.inheritance_map.get(current)
                current = base
            if ancestors:
                ancestor_lists.append(ancestors)
        
        if not ancestor_lists:
            return None
        
        common = set(ancestor_lists[0])
        for ancestors in ancestor_lists[1:]:
            common.intersection_update(ancestors)
            if not common:
                break
        
        if not common:
            return None
        
        for ancestor in ancestor_lists[0]:
            if ancestor in common:
                return ancestor
        return None

