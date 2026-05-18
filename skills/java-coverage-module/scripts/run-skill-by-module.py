#!/usr/bin/env python3
"""
Lists or selects modules in a multimodule Maven project.
Usage:
  python3 run-skill-by-module.py --list <project_root>
  python3 run-skill-by-module.py --select <module_name> <project_root>
"""

import sys
import os
import xml.etree.ElementTree as ET

NS = {"m": "http://maven.apache.org/POM/4.0.0"}


def find_modules(project_root):
    pom_path = os.path.join(project_root, "pom.xml")
    if not os.path.isfile(pom_path):
        print(f"ERROR: pom.xml not found in {project_root}", file=sys.stderr)
        sys.exit(1)

    try:
        tree = ET.parse(pom_path)
    except ET.ParseError as e:
        print(f"ERROR: failed to parse pom.xml â€” {e}", file=sys.stderr)
        sys.exit(1)

    root = tree.getroot()
    modules = []

    for mod_el in root.findall(".//m:module", NS) or root.findall(".//module"):
        mod_name = mod_el.text.strip()
        mod_path = os.path.join(project_root, mod_name)
        if os.path.isdir(mod_path):
            modules.append((mod_name, mod_path))

    return modules


def cmd_list(project_root):
    modules = find_modules(project_root)
    if not modules:
        print("ERROR: no modules found â€” confirm this is a multimodule project", file=sys.stderr)
        sys.exit(1)

    print(f"MODULES FOUND: {len(modules)}")
    for i, (name, path) in enumerate(modules, start=1):
        print(f"  [{i}] {name:<30} â†’ {path}")


def cmd_select(module_name, project_root):
    modules = find_modules(project_root)
    match = next((m for m in modules if m[0] == module_name), None)

    if not match:
        available = ", ".join(m[0] for m in modules)
        print(
            f"ERROR: module '{module_name}' not found. Available: {available}",
            file=sys.stderr,
        )
        sys.exit(1)

    name, mod_path = match
    pom_path = os.path.join(mod_path, "pom.xml")
    jacoco_path = os.path.join(mod_path, "target", "site", "jacoco", "jacoco.xml")

    print(f"MODULE: {name}")
    print(f"ROOT: {mod_path}")
    print(f"POM: {pom_path}")
    print(f"JACOCO: {jacoco_path if os.path.isfile(jacoco_path) else 'NOT_FOUND - run scripts/run-jacoco-report.py <module_path>'}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(
            "ERROR: mode and project root required.\n"
            "Usage:\n"
            "  python3 run-skill-by-module.py --list <project_root>\n"
            "  python3 run-skill-by-module.py --select <module_name> <project_root>",
            file=sys.stderr,
        )
        sys.exit(1)

    mode = sys.argv[1]

    if mode == "--list":
        cmd_list(sys.argv[2])
    elif mode == "--select":
        if len(sys.argv) < 4:
            print(
                "ERROR: module name and project root required for --select.",
                file=sys.stderr,
            )
            sys.exit(1)
        cmd_select(sys.argv[2], sys.argv[3])
    else:
        print(f"ERROR: unknown mode '{mode}'. Use --list or --select.", file=sys.stderr)
        sys.exit(1)

