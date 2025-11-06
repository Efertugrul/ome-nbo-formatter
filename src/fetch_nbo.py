import os
import sys
import subprocess
import argparse
from typing import List

DEFAULT_REPO = os.getenv("NBO_REPO_URL", "https://github.com/WU-BIMAC/NBOMicroscopyMetadataSpecs.git")
DEFAULT_REF = os.getenv("NBO_REF", "master")
DEFAULT_PATHS = [
	"Model/stable version/v02-01",
	"Model/in progress/v02-10",
]


def sh(cmd: List[str], cwd: str = None):
	res = subprocess.run(cmd, cwd=cwd, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
	return res.stdout


def fetch_repo(repo_url: str, ref: str, paths: List[str], dest: str):
	os.makedirs(dest, exist_ok=True)
	# Initialize repo if not exists or not a git repo
	if not os.path.exists(os.path.join(dest, ".git")):
		sh(["git", "init"], cwd=dest)
		# set origin
		try:
			sh(["git", "remote", "remove", "origin"], cwd=dest)
		except Exception:
			pass
		sh(["git", "remote", "add", "origin", repo_url], cwd=dest)
		# sparse checkout
		sh(["git", "sparse-checkout", "init", "--cone"], cwd=dest)
	# set sparse paths
	if paths:
		sh(["git", "sparse-checkout", "set", *paths], cwd=dest)
	# fetch and checkout
	sh(["git", "fetch", "--depth", "1", "origin", ref], cwd=dest)
	sh(["git", "checkout", "FETCH_HEAD"], cwd=dest)


def main():
	parser = argparse.ArgumentParser(description="Fetch NBO NBOMicroscopyMetadataSpecs via git sparse checkout")
	parser.add_argument("--repo-url", default=DEFAULT_REPO, help="Upstream repository URL")
	parser.add_argument("--ref", default=DEFAULT_REF, help="Branch/tag/SHA to fetch (default: env NBO_REF or main)")
	parser.add_argument("--dest", default="NBOMicroscopyMetadataSpecs", help="Destination directory (default: NBOMicroscopyMetadataSpecs)")
	parser.add_argument("--path", action="append", help="Path(s) within repo to include (repeatable)")
	args = parser.parse_args()
	paths = args.path if args.path else DEFAULT_PATHS
	print(f"Fetching {args.repo_url} ref={args.ref} to {args.dest} paths={paths}")
	fetch_repo(args.repo_url, args.ref, paths, args.dest)
	print("Done.")


if __name__ == "__main__":
	main()
