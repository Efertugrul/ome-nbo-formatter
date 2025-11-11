import argparse
import os
import yaml
import json
from typing import Dict, Set, Tuple

# Reuse converter without circular imports risk
try:
	from src.xsdtojson import xsd_to_json_schema
except Exception:
	from xsdtojson import xsd_to_json_schema


def load_linkml_classes_and_slots(linkml_yaml_path: str) -> Tuple[Set[str], Dict[str, Set[str]], Dict[str, Set[str]]]:
	"""Load class names, attribute slot names, and child slot names from LinkML YAML we generate."""
	with open(linkml_yaml_path, "r") as f:
		lm = yaml.safe_load(f)
	classes = lm.get("classes", {}) or {}
	slots = lm.get("slots", {}) or {}
	class_names: Set[str] = set(classes.keys())
	class_to_attrs: Dict[str, Set[str]] = {}
	class_to_children: Dict[str, Set[str]] = {}
	for cname, cdef in classes.items():
		cslots = set(cdef.get("slots", []) or [])
		attrs = set()
		children = set()
		for s in cslots:
			if s.startswith("attr_"):
				attrs.add(s)
			else:
				children.add(s)
		class_to_attrs[cname] = attrs
		class_to_children[cname] = children
	return class_names, class_to_attrs, class_to_children


def load_xsd_structure_via_json(xsd_path: str) -> Tuple[Set[str], Dict[str, Set[str]], Dict[str, Set[str]]]:
	"""Use xsdtojson to approximate element/class, attributes, and child elements per element."""
	js = xsd_to_json_schema(xsd_path)
	props = js.get("properties", {}) or {}
	class_names = set(props.keys())
	class_to_attrs: Dict[str, Set[str]] = {}
	class_to_children: Dict[str, Set[str]] = {}
	for pname, pdef in props.items():
		pprops = (pdef or {}).get("properties", {}) or {}
		attrs = set()
		children = set()
		for k in pprops.keys():
			if k.startswith("@"):
				attrs.add(f"attr_{k[1:].lower()}")
			else:
				children.add(k)
		class_to_attrs[pname] = attrs
		class_to_children[pname] = children
	return class_names, class_to_attrs, class_to_children


def compare_sets(expected: Set[str], actual: Set[str]) -> Dict[str, Set[str]]:
	return {
		"missing": expected - actual,
		"extra": actual - expected
	}


def generate_report(xsd_path: str, linkml_yaml_path: str) -> str:
	x_classes, x_attrs, x_children = load_xsd_structure_via_json(xsd_path)
	l_classes, l_attrs, l_children = load_linkml_classes_and_slots(linkml_yaml_path)

	report = []
	report.append(f"XSD file: {xsd_path}")
	report.append(f"LinkML schema: {linkml_yaml_path}")
	report.append("")
	# Classes
	class_diff = compare_sets(x_classes, l_classes)
	report.append("== Classes ==")
	report.append(f"XSD classes: {len(x_classes)} | LinkML classes: {len(l_classes)}")
	report.append(f"Missing in LinkML: {len(class_diff['missing'])}")
	if class_diff['missing']:
		report.append(", ".join(sorted(list(class_diff['missing']))[:40]) + (" ..." if len(class_diff['missing'])>40 else ""))
	report.append(f"Extra in LinkML: {len(class_diff['extra'])}")
	if class_diff['extra']:
		report.append(", ".join(sorted(list(class_diff['extra']))[:40]) + (" ..." if len(class_diff['extra'])>40 else ""))
	report.append("")
	# Per-class attributes/children, only for intersection
	common = x_classes & l_classes
	report.append(f"== Per-class checks (intersection {len(common)}) ==")
	mismatch_count = 0
	for cname in sorted(list(common))[:200]:
		a_diff = compare_sets(x_attrs.get(cname, set()), l_attrs.get(cname, set()))
		c_diff = compare_sets(x_children.get(cname, set()), l_children.get(cname, set()))
		if a_diff["missing"] or a_diff["extra"] or c_diff["missing"] or c_diff["extra"]:
			mismatch_count += 1
			report.append(f"-- {cname}")
			if a_diff["missing"]:
				report.append(f"   attrs missing: {sorted(list(a_diff['missing']))[:20]}")
			if a_diff["extra"]:
				report.append(f"   attrs extra: {sorted(list(a_diff['extra']))[:20]}")
			if c_diff["missing"]:
				report.append(f"   children missing: {sorted(list(c_diff['missing']))[:20]}")
			if c_diff["extra"]:
				report.append(f"   children extra: {sorted(list(c_diff['extra']))[:20]}")
	report.append("")
	report.append(f"Classes with mismatches (first 200 checked): {mismatch_count}")
	return "\n".join(report)


def main():
	p = argparse.ArgumentParser(description="Verify structural equivalence between XSD and generated LinkML YAML")
	p.add_argument("xsd", help="Path to source XSD")
	p.add_argument("linkml", help="Path to generated LinkML YAML")
	args = p.parse_args()
	print(generate_report(args.xsd, args.linkml))


if __name__ == "__main__":
	main()
