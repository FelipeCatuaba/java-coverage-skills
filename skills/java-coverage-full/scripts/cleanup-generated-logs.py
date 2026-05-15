#!/usr/bin/env python3
"""
Removes temporary coverage tracker and log files generated during the skill run.
Usage: python3 cleanup-generated-logs.py <project_root>
Stdout: CLEANUP OK — removed: <N> files
Stderr: error messages
"""
import sys
import os
import glob

PATTERNS = [
    '**/.coverage-tracker.txt',
    '**/coverage-tracker-*.txt',
    '**/.skill-run-*.log',
]

def main(project_root):
    if not os.path.isdir(project_root):
        print(f"ERROR: project root not found: {project_root}", file=sys.stderr)
        sys.exit(1)

    removed = 0
    for pattern in PATTERNS:
        for fpath in glob.glob(os.path.join(project_root, pattern), recursive=True):
            try:
                os.remove(fpath)
                removed += 1
            except OSError as e:
                print(f"WARNING: could not remove {fpath} — {e}", file=sys.stderr)

    print(f"CLEANUP OK — removed: {removed} files")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: cleanup-generated-logs.py <project_root>", file=sys.stderr)
        sys.exit(1)
    main(sys.argv[1])
