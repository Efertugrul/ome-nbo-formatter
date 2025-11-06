import os
import sys
import glob
import yaml
import argparse
from typing import List, Dict, Any

# Robust imports whether run as module or script
try:
    from src.generator import generate_linkml_schema
except ImportError:
    from generator import generate_linkml_schema

try:
    from src.verify_equivalence import (
        load_xsd_structure_via_json,
        load_linkml_classes_and_slots,
        compare_sets,
    )
except ImportError:
    from verify_equivalence import (
        load_xsd_structure_via_json,
        load_linkml_classes_and_slots,
        compare_sets,
    )

def resolve_paths(nbo_root_arg: str = None, out_dir_arg: str = None) -> (str, str):
	env_root = os.getenv("MED_RESEARCH_ROOT")
	# Default repo root from this file location: .../ome-nbo-formatter/src -> go up two levels
	default_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
	root = env_root if env_root else default_root
	nbo_root = nbo_root_arg if nbo_root_arg else os.path.join(root, "NBOMicroscopyMetadataSpecs")
	out_dir = out_dir_arg if out_dir_arg else os.path.join(root, "_nbo_batch")
	os.makedirs(out_dir, exist_ok=True)
	return nbo_root, out_dir


def find_nbo_xsds(nbo_root: str) -> List[str]:
	patterns = [
		os.path.join(nbo_root, "**", "NBO_MicroscopyMetadataSpecifications_ALL.xsd"),
	]
	paths: List[str] = []
	for pat in patterns:
		paths.extend(glob.glob(pat, recursive=True))
	return sorted(paths)


def summarize(xsd_path: str, yaml_path: str) -> Dict[str, Any]:
	x_classes, x_attrs, x_children = load_xsd_structure_via_json(xsd_path)
	l_classes, l_attrs, l_children = load_linkml_classes_and_slots(yaml_path)
	class_diff = compare_sets(x_classes, l_classes)
	common = x_classes & l_classes
	mismatch = 0
	for cname in common:
		a_diff = compare_sets(x_attrs.get(cname, set()), l_attrs.get(cname, set()))
		c_diff = compare_sets(x_children.get(cname, set()), l_children.get(cname, set()))
		if a_diff["missing"] or a_diff["extra"] or c_diff["missing"] or c_diff["extra"]:
			mismatch += 1
	return {
		"xsd": xsd_path,
		"yaml": yaml_path,
		"xsd_classes": len(x_classes),
		"linkml_classes": len(l_classes),
		"missing_classes": len(class_diff["missing"]),
		"extra_classes": len(class_diff["extra"]),
		"per_class_mismatches": mismatch,
	}



def main():
	parser = argparse.ArgumentParser(description="Batch generate and verify LinkML from all NBO XSDs")
	parser.add_argument("--nbo-root", help="Path to NBOMicroscopyMetadataSpecs directory")
	parser.add_argument("--out-dir", help="Output directory for generated LinkML files")
	parser.add_argument("--auto-fetch", action="store_true", help="If no XSDs found, fetch NBO via git sparse checkout")
	args = parser.parse_args()

	nbo_root, out_dir = resolve_paths(args.nbo_root, args.out_dir)
	xsds = find_nbo_xsds(nbo_root)
	if not xsds and args.auto_fetch:
		# Try to fetch default paths
		try:
			from src.fetch_nbo import fetch_repo, DEFAULT_REPO, DEFAULT_REF, DEFAULT_PATHS
		except ImportError:
			from fetch_nbo import fetch_repo, DEFAULT_REPO, DEFAULT_REF, DEFAULT_PATHS
		print("No XSDs found; fetching NBO repo ...")
		fetch_repo(DEFAULT_REPO, DEFAULT_REF, DEFAULT_PATHS, nbo_root)
		xsds = find_nbo_xsds(nbo_root)
	rows: List[Dict[str, Any]] = []
	for xsd in xsds:
		base = os.path.basename(os.path.dirname(xsd)) or "root"
		out_yaml = os.path.join(out_dir, f"{base}.yaml")
		# generate
		generate_linkml_schema(xsd, out_yaml)
		# summarize
		rows.append(summarize(xsd, out_yaml))
	# print summary table
	print("schema\txsd_classes\tlinkml_classes\tmissing\textra\tmismatches")
	for r in rows:
		label = os.path.relpath(os.path.dirname(r["xsd"]), nbo_root)
		print(f"{label}\t{r['xsd_classes']}\t{r['linkml_classes']}\t{r['missing_classes']}\t{r['extra_classes']}\t{r['per_class_mismatches']}")


if __name__ == "__main__":
	main()
