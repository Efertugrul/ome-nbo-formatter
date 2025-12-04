from typing import Dict, List, Set, Tuple
from collections import defaultdict
from xmlschema.validators.groups import XsdGroup
from xmlschema.validators.elements import XsdElement

try:
    from .utils import local_name
except ImportError:
    from utils import local_name


class ChoiceConstraintHandler:
    def __init__(self, linkml_schema: Dict):
        self.linkml_schema = linkml_schema
        self.choice_slot_membership: Dict[str, Set[str]] = defaultdict(set)
        self.choice_repeat_membership: Dict[str, Set[str]] = defaultdict(set)
    
    def choice_is_repeating(self, group: XsdGroup) -> bool:
        maxo = getattr(group, "max_occurs", None)
        occurs = getattr(group, "occurs", None)
        occurs_tuple = None
        if isinstance(occurs, tuple):
            occurs_tuple = occurs
        elif hasattr(occurs, "__iter__"):
            occurs_tuple = tuple(occurs)
        if maxo == "unbounded" or (isinstance(maxo, int) and maxo > 1):
            return True
        if maxo is None and occurs_tuple and occurs_tuple[-1] is None:
            return True
        return False
    
    def collect_choice_constraints(self, class_name: str, content):
        if content is None:
            return
        if not hasattr(content, "iter_model"):
            return
        if isinstance(content, XsdGroup) and content.model == 'choice':
            branches = self.extract_choice_branches(content)
            self.apply_choice_constraint(class_name, branches, self.choice_is_repeating(content))
        for item in content.iter_model():
            if isinstance(item, XsdGroup) and item.model == 'choice':
                branches = self.extract_choice_branches(item)
                self.apply_choice_constraint(class_name, branches, self.choice_is_repeating(item))
    
    def extract_choice_branches(self, group: XsdGroup) -> List[List[Tuple[str, bool]]]:
        branches: List[List[Tuple[str, bool]]] = []
        for item in group.iter_model():
            if isinstance(item, XsdGroup):
                if item.model == 'choice':
                    branches.extend(self.extract_choice_branches(item))
                else:
                    branches.append(self.collect_branch_slots(item))
            elif isinstance(item, XsdElement):
                branches.append(self.collect_branch_slots(item))
        return [branch for branch in branches if branch]
    
    def collect_branch_slots(self, node) -> List[Tuple[str, bool]]:
        slots: List[Tuple[str, bool]] = []
        
        def _visit(item):
            if isinstance(item, XsdElement):
                slot_name = local_name(getattr(item, "name", None) or 
                                      getattr(getattr(item, "ref", None), "name", None))
                if slot_name:
                    required = bool(getattr(item, "min_occurs", 0))
                    slots.append((slot_name, required))
            elif isinstance(item, XsdGroup):
                for sub in item.iter_model():
                    _visit(sub)
        
        _visit(node)
        return slots
    
    def apply_choice_constraint(self, class_name: str, branches: List[List[Tuple[str, bool]]], repeating: bool = False):
        if len(branches) < 2:
            return
        
        cls = self.linkml_schema["classes"].setdefault(class_name, {})
        slot_sets = [set(slot for slot, _ in branch) for branch in branches]
        universe = set().union(*slot_sets)
        
        if all(len(slot_set) == 1 for slot_set in slot_sets):
            group: List[str] = []
            for slot_set in slot_sets:
                slot_name = next(iter(slot_set))
                if slot_name not in group:
                    group.append(slot_name)
            
            existing = cls.setdefault("exactly_one_of", [])
            for slot_name in group:
                expr = {
                    "slot_conditions": {
                        slot_name: {"required": True}
                    }
                }
                if expr not in existing:
                    existing.append(expr)
            
            self.choice_slot_membership[class_name].update(universe)
            if repeating:
                self.choice_repeat_membership[class_name].update(universe)
            return
        
        self.choice_slot_membership[class_name].update(universe)
        if repeating:
            self.choice_repeat_membership[class_name].update(universe)
    
    def relax_choice_constraints(self):
        for class_name, slot_names in self.choice_slot_membership.items():
            cls = self.linkml_schema["classes"].get(class_name)
            if not cls:
                continue
            attrs = cls.get("attributes", {})
            for slot_name in slot_names:
                slot = attrs.get(slot_name)
                if not slot:
                    continue
                slot.pop("required", None)
        
        for class_name, slot_names in self.choice_repeat_membership.items():
            cls = self.linkml_schema["classes"].get(class_name)
            if not cls:
                continue
            attrs = cls.get("attributes", {})
            for slot_name in slot_names:
                slot = attrs.get(slot_name)
                if not slot:
                    continue
                slot["multivalued"] = True

