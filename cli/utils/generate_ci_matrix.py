#!/usr/bin/env python3
# Copyright 2026 Iguazio
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""
Script to generate CI matrix grouped by Python versions.
This groups items by their required Python versions for efficient testing.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List
import yaml
from packaging import version


def get_python_versions_for_mlrun(mlrun_version_str: str) -> List[str]:
    """
    Determine Python versions based on MLRun version.

    Rules:
    - MLRun version < 1.9.0: Python 3.9 only
    - MLRun version >= 1.9.0 and < 1.10.0: Python 3.9 and 3.11
    - MLRun version >= 1.10.0: Python 3.11 only
    """
    mlrun_version_clean = mlrun_version_str.split("-")[0]

    try:
        mlrun_ver = version.parse(mlrun_version_clean)
        v_1_9_0 = version.parse("1.9.0")
        v_1_10_0 = version.parse("1.10.0")

        if mlrun_ver < v_1_9_0:
            return ["3.10.17"]
        elif v_1_9_0 <= mlrun_ver < v_1_10_0:
            return ["3.10.17", "3.11"]
        else:  # >= 1.10.0
            return ["3.11"]
    except Exception:
        return ["3.9"]


def generate_matrix(packages: List[str]) -> Dict:
    """
    Generate a matrix grouped by Python version.

    Returns a dictionary like:
    {
        "include": [
            {
                "python-version": "3.9",
                "packages": ["functions/src/aggregate", "functions/src/batch_inference", ...]
            },
            {
                "python-version": "3.11",
                "packages": ["functions/src/translate", "modules/src/vllm_module", ...]
            }
        ]
    }
    """
    # Group packages by Python version
    version_groups: Dict[str, List[str]] = {}

    for pkg in packages:
        if not pkg:
            continue

        item_yaml = Path(pkg) / "item.yaml"
        if not item_yaml.exists():
            continue

        try:
            with open(item_yaml, 'r') as f:
                item_data = yaml.safe_load(f)

            mlrun_version_str = item_data.get("mlrunVersion", "1.7.0")
            python_versions = get_python_versions_for_mlrun(mlrun_version_str)

            # Add package to each required Python version group
            for py_ver in python_versions:
                if py_ver not in version_groups:
                    version_groups[py_ver] = []
                version_groups[py_ver].append(pkg)
        except Exception as e:
            print(f"Warning: Error processing {pkg}: {e}", file=sys.stderr)
            continue

    # Convert to matrix format
    matrix_entries = []
    for py_ver in sorted(version_groups.keys()):
        if version_groups[py_ver]:  # Only include if there are packages
            matrix_entries.append({
                "python-version": py_ver,
                "packages": version_groups[py_ver]
            })

    return {"include": matrix_entries}


def main():
    """
    Read packages from stdin (one per line) and output JSON matrix to stdout.
    """
    # Read packages from stdin
    packages = []
    for line in sys.stdin:
        line = line.strip()
        if line:
            packages.append(line)

    if not packages:
        # Empty matrix
        print(json.dumps({"include": []}, separators=(',', ':')))
        return 0

    # Generate matrix
    matrix = generate_matrix(packages)

    # Output as compact JSON
    print(json.dumps(matrix, separators=(',', ':')))
    return 0


if __name__ == "__main__":
    sys.exit(main())

