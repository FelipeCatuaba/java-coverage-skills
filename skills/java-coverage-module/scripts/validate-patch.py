#!/usr/bin/env python3
"""
Validates a patch file for BOM and CRLF issues.
Usage: python3 validate-patch.py <patch_file>
Stdout: PATCH OK
Stderr: BOM_DETECTED at <file>:<line> | CRLF_DETECTED at <file>:<line>
"""
import sys
import os

def validate(patch_path):
    if not os.path.isfile(patch_path):
        print(f"ERROR: patch file not found: {patch_path}", file=sys.stderr)
        sys.exit(1)

    with open(patch_path, 'rb') as f:
        raw = f.read()

    errors = []

    if raw.startswith(b'\xef\xbb\xbf'):
        errors.append(f"BOM_DETECTED at {patch_path}:1 — file starts with UTF-8 BOM (EF BB BF)")

    lines = raw.split(b'\n')
    for i, line in enumerate(lines, 1):
        if line.endswith(b'\r'):
            errors.append(f"CRLF_DETECTED at {patch_path}:{i} — line ends with \\r\\n")
            break

    # Boundary check: patch must never target src/main/
    text = raw.decode('utf-8', errors='replace')
    for i, line in enumerate(text.splitlines(), 1):
        if line.startswith('---') or line.startswith('+++ '):
            if 'src/main/' in line:
                errors.append(
                    f"BOUNDARY_VIOLATION at {patch_path}:{i} — "
                    f"patch targets src/main/ which is forbidden: {line.strip()}"
                )

    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        sys.exit(1)

    print("PATCH OK")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: validate-patch.py <patch_file>", file=sys.stderr)
        sys.exit(1)
    validate(sys.argv[1])
