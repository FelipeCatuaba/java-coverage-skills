#!/usr/bin/env python3
"""
Lists all Maven modules in a multi-module project.
Usage: python3 resolve-module.py <project_root> [module_name]
Stdout: MODULES FOUND: list, or TARGET MODULE: <name> — root: <path>
Stderr: NO_MODULES_FOUND
"""
import sys
import os
import xml.etree.ElementTree as ET

def get_ns(root):
    return f'{{{root.tag.split("}")[0][1:]}}}' if '}' in root.tag else ''

def count_java_classes(module_path):
    src = os.path.join(module_path, 'src', 'main', 'java')
    if not os.path.isdir(src):
        return 0
    return sum(1 for _, _, files in os.walk(src) for f in files if f.endswith('.java'))

def find_modules(project_root):
    pom_path = os.path.join(project_root, 'pom.xml')
    if not os.path.isfile(pom_path):
        return []

    try:
        tree = ET.parse(pom_path)
        root = tree.getroot()
        ns = get_ns(root)
        modules_el = root.find(f'{ns}modules')
        if modules_el is None:
            return []
        return [m.text.strip() for m in modules_el.findall(f'{ns}module') if m.text]
    except ET.ParseError:
        return []

def main(project_root, requested_module=None):
    if not os.path.isdir(project_root):
        print(f"ERROR: project root not found: {project_root}", file=sys.stderr)
        sys.exit(1)

    modules = find_modules(project_root)
    if not modules:
        print("NO_MODULES_FOUND: project has no <modules> section in pom.xml", file=sys.stderr)
        sys.exit(1)

    if requested_module:
        match = next((m for m in modules if m == requested_module or m.endswith(requested_module)), None)
        if not match:
            print(f"NO_MODULES_FOUND: module '{requested_module}' not in pom.xml modules list", file=sys.stderr)
            sys.exit(1)
        module_path = os.path.join(project_root, match)
        print(f"TARGET MODULE: {match} — root: {module_path}")
        return

    print("MODULES FOUND:")
    for i, module in enumerate(modules):
        module_path = os.path.join(project_root, module)
        count = count_java_classes(module_path)
        print(f"[{i}] {module:<40} ({count} classes)")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: resolve-module.py <project_root> [module_name]", file=sys.stderr)
        sys.exit(1)
    requested = sys.argv[2] if len(sys.argv) >= 3 else None
    main(sys.argv[1], requested)
