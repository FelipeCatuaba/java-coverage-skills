#!/usr/bin/env python3
"""
Lists production Java files changed but NOT committed yet.
Scope: staged + unstaged + untracked files.
Usage: python3 resolve-git-diff.py <project_root>
Stdout: one file path per line
Stderr: NO_JAVA_FILES | NOT_A_GIT_REPO
"""
import os
import subprocess
import sys


def run_git(project_root, args):
    result = subprocess.run(
        ["git"] + args,
        cwd=project_root,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git command failed")
    return result.stdout


def main(project_root):
    if not os.path.isdir(project_root):
        print(f"ERROR: project root not found: {project_root}", file=sys.stderr)
        sys.exit(1)

    if not os.path.isdir(os.path.join(project_root, ".git")):
        print("NOT_A_GIT_REPO: .git directory not found", file=sys.stderr)
        sys.exit(1)

    try:
        unstaged = run_git(project_root, ["diff", "--name-only"])
        staged = run_git(project_root, ["diff", "--name-only", "--cached"])
        untracked = run_git(project_root, ["ls-files", "--others", "--exclude-standard"])
    except FileNotFoundError:
        print("NOT_A_GIT_REPO: git command not found", file=sys.stderr)
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("ERROR: git diff timed out", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as err:
        print(f"ERROR: git commands failed — {err}", file=sys.stderr)
        sys.exit(1)

    changed_paths = set()
    for chunk in (unstaged, staged, untracked):
        for line in chunk.splitlines():
            line = line.strip()
            if line:
                changed_paths.add(line)

    changed = sorted(
        path
        for path in changed_paths
        if path.endswith(".java")
        and "src/main/java" in path
        and "src/test/" not in path
    )

    if not changed:
        print("NO_JAVA_FILES: no uncommitted production .java files found", file=sys.stderr)
        sys.exit(1)

    for path in changed:
        print(path)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: resolve-git-diff.py <project_root>", file=sys.stderr)
        sys.exit(1)
    main(sys.argv[1])
