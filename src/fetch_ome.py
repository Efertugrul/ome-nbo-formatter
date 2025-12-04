#!/usr/bin/env python3
"""
Fetch OME XSD schema files from the official OME repository or URL.
"""
import os
import sys
import argparse
import urllib.request
from pathlib import Path

# OME XSD URLs
OME_XSD_URLS = {
    "2016-06": "http://www.openmicroscopy.org/Schemas/OME/2016-06/ome.xsd",
    "latest": "http://www.openmicroscopy.org/Schemas/OME/2016-06/ome.xsd",  # Currently latest
}

# GitHub repo alternative (if needed)
OME_GITHUB_REPO = "https://github.com/ome/ome-model.git"
OME_GITHUB_XSD_PATH = "src/xsd/ome.xsd"


def download_xsd(url: str, dest_path: str):
    """Download XSD file from URL."""
    print(f"Downloading OME XSD from {url}...")
    os.makedirs(os.path.dirname(dest_path) if os.path.dirname(dest_path) else ".", exist_ok=True)
    
    try:
        urllib.request.urlretrieve(url, dest_path)
        print(f"Successfully downloaded to {dest_path}")
        return True
    except Exception as e:
        print(f"Error downloading from URL: {e}")
        return False


def fetch_from_github(repo_url: str, ref: str, xsd_path: str, dest: str):
    """Fetch XSD from GitHub using sparse checkout (similar to fetch_nbo.py)."""
    import subprocess
    
    def sh(cmd, cwd=None):
        res = subprocess.run(cmd, cwd=cwd, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        return res.stdout
    
    os.makedirs(dest, exist_ok=True)
    
    if not os.path.exists(os.path.join(dest, ".git")):
        sh(["git", "init"], cwd=dest)
        try:
            sh(["git", "remote", "remove", "origin"], cwd=dest)
        except Exception:
            pass
        sh(["git", "remote", "add", "origin", repo_url])
        sh(["git", "sparse-checkout", "init", "--cone"], cwd=dest)
    
    sh(["git", "sparse-checkout", "set", xsd_path], cwd=dest)
    sh(["git", "fetch", "--depth", "1", "origin", ref], cwd=dest)
    sh(["git", "checkout", "FETCH_HEAD"], cwd=dest)
    
    # Copy to final destination
    src_file = os.path.join(dest, xsd_path)
    if os.path.exists(src_file):
        return src_file
    return None


def main():
    parser = argparse.ArgumentParser(description="Fetch OME XSD schema")
    parser.add_argument("--version", default="latest", choices=list(OME_XSD_URLS.keys()) + ["github"],
                       help="OME schema version (default: latest)")
    parser.add_argument("--dest", default="OMESchemas", help="Destination directory")
    parser.add_argument("--output", help="Output file path (if not specified, uses dest/ome.xsd)")
    parser.add_argument("--ref", default="master", help="Git ref for GitHub fetch (default: master)")
    
    args = parser.parse_args()
    
    if args.version == "github":
        # Fetch from GitHub
        dest_dir = args.dest
        xsd_file = fetch_from_github(OME_GITHUB_REPO, args.ref, OME_GITHUB_XSD_PATH, dest_dir)
        if xsd_file:
            if args.output:
                import shutil
                shutil.copy2(xsd_file, args.output)
                print(f"Copied to {args.output}")
            else:
                print(f"OME XSD available at {xsd_file}")
        else:
            print("Failed to fetch from GitHub")
            sys.exit(1)
    else:
        # Download from URL
        url = OME_XSD_URLS[args.version]
        output_path = args.output or os.path.join(args.dest, "ome.xsd")
        if download_xsd(url, output_path):
            print(f"OME XSD saved to {output_path}")
        else:
            print("Failed to download OME XSD")
            sys.exit(1)


if __name__ == "__main__":
    main()

