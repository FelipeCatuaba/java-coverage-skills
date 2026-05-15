#!/usr/bin/env python3
"""
Finds all test class files for a given production class name.
Usage: python3 find-test-classes.py <project_root> <ClassName>
Stdout: one file path per line, or NO_TEST_CLASS_FOUND
Stderr: error messages
"""
import sys
import os
import re

def find_test_classes(project_root, class_name):
    test_root = os.path.join(project_root, 'src', 'test', 'java')
    if not os.path.isdir(test_root):
        print(f"NO_TEST_CLASS_FOUND: src/test/java not found in {project_root}", file=sys.stderr)
        return []

    base = class_name.replace('.java', '')
    pattern = re.compile(
        rf'^{re.escape(base)}(_ESTest|Test\d*|CoverageTest|Tests)?(\.java)?$',
        re.IGNORECASE
    )

    found = []
    for root_dir, _, files in os.walk(test_root):
        for fname in files:
            if not fname.endswith('.java'):
                continue
            stem = fname.replace('.java', '')
            if pattern.match(stem) or stem == f"{base}Test":
                found.append(os.path.join(root_dir, fname))

    return found

def main(project_root, class_name):
    if not os.path.isdir(project_root):
        print(f"ERROR: project root not found: {project_root}", file=sys.stderr)
        sys.exit(1)

    results = find_test_classes(project_root, class_name)
    if not results:
        print("NO_TEST_CLASS_FOUND")
    else:
        for path in results:
            print(path)

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: find-test-classes.py <project_root> <ClassName>", file=sys.stderr)
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
