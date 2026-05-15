#!/usr/bin/env python3
"""
Checks coverage gate only for uncommitted diff lines in production Java files.
Scope: staged + unstaged + untracked lines.

Usage:
  python3 check-diff-line-gate.py <project_root> <jacoco_xml>

Stdout:
  table with one row per changed class and status GATE_MET / BELOW_GATE
Stderr:
  REPORT_NOT_FOUND | NOT_A_GIT_REPO | NO_DIFF_LINES
"""
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

LINE_GATE = 92
BRANCH_GATE = 90


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


def parse_unified_zero_context(diff_text):
    changed = {}
    current_file = None

    for raw in diff_text.splitlines():
        line = raw.rstrip("\n")
        if line.startswith("+++ b/"):
            current_file = line[6:]
            changed.setdefault(current_file, set())
            continue

        if not line.startswith("@@") or current_file is None:
            continue

        # @@ -a,b +c,d @@
        m = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", line)
        if not m:
            continue
        start = int(m.group(1))
        count = int(m.group(2) or "1")
        if count == 0:
            continue
        for ln in range(start, start + count):
            changed[current_file].add(ln)

    return changed


def collect_changed_lines(project_root):
    # Staged + unstaged hunks for tracked files
    unstaged_patch = run_git(project_root, ["diff", "-U0", "--", "src/main/java"])
    staged_patch = run_git(project_root, ["diff", "--cached", "-U0", "--", "src/main/java"])

    changed = {}
    for parsed in (parse_unified_zero_context(unstaged_patch), parse_unified_zero_context(staged_patch)):
        for path, lines in parsed.items():
            if not path.endswith(".java") or "src/test/" in path:
                continue
            changed.setdefault(path, set()).update(lines)

    # Untracked java files: all lines are considered new diff lines
    untracked = run_git(project_root, ["ls-files", "--others", "--exclude-standard", "--", "src/main/java"])
    for rel in untracked.splitlines():
        rel = rel.strip()
        if not rel.endswith(".java") or "src/test/" in rel:
            continue
        abs_path = os.path.join(project_root, rel)
        if not os.path.isfile(abs_path):
            continue
        line_count = 0
        with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
            for _ in f:
                line_count += 1
        changed[rel] = set(range(1, line_count + 1))

    # Keep only files that still exist and have at least one changed line
    filtered = {}
    for rel, lines in changed.items():
        if not lines:
            continue
        if not os.path.isfile(os.path.join(project_root, rel)):
            continue
        filtered[rel] = lines
    return filtered


def class_to_path(class_name):
    return "src/main/java/" + class_name + ".java"


def parse_jacoco_lines(xml_path):
    if not os.path.isfile(xml_path):
        print(f"REPORT_NOT_FOUND: {xml_path}", file=sys.stderr)
        sys.exit(1)

    try:
        root = ET.parse(xml_path).getroot()
    except ET.ParseError as err:
        print(f"REPORT_NOT_FOUND: could not parse XML — {err}", file=sys.stderr)
        sys.exit(1)

    # map: rel_path -> line_number -> (ci, mi, cb, mb)
    data = {}
    for package in root.findall(".//package"):
        pkg_name = package.get("name", "")
        pkg_path = pkg_name.replace(".", "/")
        for cls in package.findall("class"):
            class_name = cls.get("name", "")
            rel = class_to_path(class_name)
            if pkg_path and not rel.startswith("src/main/java/" + pkg_path):
                # keep as-is; class name already contains package segments
                pass
            lines = {}
            for ln in cls.findall("line"):
                nr = int(ln.get("nr", "0"))
                ci = int(ln.get("ci", "0"))
                mi = int(ln.get("mi", "0"))
                cb = int(ln.get("cb", "0"))
                mb = int(ln.get("mb", "0"))
                lines[nr] = (ci, mi, cb, mb)
            data[rel] = lines
    return data


def evaluate(changed_lines, jacoco_lines):
    rows = []
    for rel_path, line_numbers in sorted(changed_lines.items()):
        line_cov = line_miss = 0
        branch_cov = branch_miss = 0

        class_lines = jacoco_lines.get(rel_path, {})
        for ln in sorted(line_numbers):
            ci, mi, cb, mb = class_lines.get(ln, (0, 0, 0, 0))
            # If JaCoCo doesn't have line entry, treat as uncovered diff line.
            if (ci, mi, cb, mb) == (0, 0, 0, 0):
                line_miss += 1
                continue
            line_cov += 1 if ci > 0 else 0
            line_miss += 1 if mi > 0 and ci == 0 else 0
            branch_cov += cb
            branch_miss += mb

        total_lines = line_cov + line_miss
        total_branches = branch_cov + branch_miss

        line_pct = round((line_cov / total_lines) * 100) if total_lines > 0 else 0
        if total_branches > 0:
            branch_pct = round((branch_cov / total_branches) * 100)
            gate_met = line_pct >= LINE_GATE and branch_pct >= BRANCH_GATE
            branch_display = f"{branch_pct}%"
        else:
            # no branch opportunities in diff lines -> gate by lines only
            branch_pct = None
            gate_met = line_pct >= LINE_GATE
            branch_display = "N/A"

        rows.append(
            {
                "class": os.path.basename(rel_path).replace(".java", ""),
                "file": rel_path,
                "diff_lines": total_lines,
                "line_pct": line_pct,
                "branch_display": branch_display,
                "status": "GATE_MET" if gate_met else "BELOW_GATE",
            }
        )
    return rows


def main(project_root, jacoco_xml):
    if not os.path.isdir(os.path.join(project_root, ".git")):
        print("NOT_A_GIT_REPO: .git directory not found", file=sys.stderr)
        sys.exit(1)

    try:
        changed_lines = collect_changed_lines(project_root)
    except FileNotFoundError:
        print("NOT_A_GIT_REPO: git command not found", file=sys.stderr)
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("ERROR: git diff timed out", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as err:
        print(f"ERROR: git commands failed — {err}", file=sys.stderr)
        sys.exit(1)

    if not changed_lines:
        print("NO_DIFF_LINES: no uncommitted production Java lines found", file=sys.stderr)
        sys.exit(1)

    jacoco_lines = parse_jacoco_lines(jacoco_xml)
    rows = evaluate(changed_lines, jacoco_lines)

    header = f"{'CLASS':<32} | {'DIFF_LINES':>10} | {'LINES%':>6} | {'BRANCHES%':>9} | STATUS"
    lines = [header, "-" * len(header)]
    for row in rows:
        lines.append(
            f"{row['class']:<32} | {row['diff_lines']:>10} | {row['line_pct']:>5}% | "
            f"{row['branch_display']:>9} | {row['status']}"
        )

    output = "\n".join(lines)
    print(output)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: check-diff-line-gate.py <project_root> <jacoco_xml>", file=sys.stderr)
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
