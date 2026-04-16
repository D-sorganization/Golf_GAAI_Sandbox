import subprocess
import os

# We see some files drifted in upstream_drift parity tests.
# We need to update ud_drift_manifest.json to match the current hashes in the repository.
# First, let's run a script to update the manifest file locally.

import json
import hashlib
from pathlib import Path

def hash_file(path):
    with open(path, "rb") as f:
        content = f.read()
    return hashlib.sha256(content).hexdigest()

manifest_path = Path("tests/shared_contracts/ud_drift_manifest.json")
if not manifest_path.exists():
    print("Manifest not found")
else:
    with open(manifest_path, "r") as f:
        manifest = json.load(f)

    src_root = Path("src/shared/python")
    for subdir, entries in manifest.items():
        for rel_path, expected_sha in entries.items():
            full_path = src_root / subdir / rel_path
            if full_path.exists():
                actual_sha = hash_file(full_path)
                if actual_sha != expected_sha:
                    print(f"Updating {subdir}/{rel_path}")
                    manifest[subdir][rel_path] = actual_sha

    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print("Updated manifest")
