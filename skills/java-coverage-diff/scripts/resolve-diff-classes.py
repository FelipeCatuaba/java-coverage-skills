#!/usr/bin/env python3
"""
Resolves Java production classes changed in the current git diff.
Excludes test files. Returns only src/main/java files.
Usage: python3 resolve-diff-classes.py <project_root> [--base <branch>]
Default base branch: main
"""

import sys
import os
import subprocess


def resolve(project_root, base_branch="main"):
    if not os.path.isdir(os.path.join(project_root, ".git")):
        print("NOT_A_GIT_REPO", file=sys.stderr)
        sys.exit(1)

    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", base_branch, "HEAD"],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=True,
        )
        changed = result.stdout.strip().splitlines()
    except subprocess.CalledProcessError as e:
        # Fallback: staged + unstaged
        try:
            r1 = subprocess.run(
                ["git", "diff", "--name-only"],
                cwd=project_root, capture_output=True, text=True, check=True
            )
            r2 = subprocess.run(
                ["git", "diff", "--name-only", "--cached"],
                cwd=project_root, capture_output=True, text=True, check=True
            )
            changed = list(set(
                r1.stdout.strip().splitlines() + r2.stdout.strip().splitlines()
            ))
        except subprocess.CalledProcessError as e2:
            print(f"ERROR: git diff failed — {e2.stderr}", file=sys.stderr)
            sys.exit(1)

    production = [
        f for f in changed
        if f.endswith(".java")
        and "src/main/java" in f
        and "Test" not in os.path.basename(f)
    ]

    if not production:
        only_tests = [f for f in changed if f.endswith(".java")]
        if only_tests:
            print("DIFF SCOPE — only test files changed, nothing to generate")
        else:
            print("DIFF EMPTY — no Java production classes changed")
        sys.exit(0)

    print(f"DIFF SCOPE: {len(production)} class(es)")
    for i, path in enumerate(sorted(production), start=1):
        full = os.path.join(project_root, path)
        print(f"  [{i}] {full}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            "ERROR: project root required.\n"
            "Usage: python3 resolve-diff-classes.py <project_root> [--base <branch>]",
            file=sys.stderr,
        )
        sys.exit(1)

    root = sys.argv[1]
    base = "main"

    if "--base" in sys.argv:
        idx = sys.argv.index("--base")
        base = sys.argv[idx + 1]

    resolve(root, base)
