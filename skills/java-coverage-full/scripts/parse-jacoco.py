#!/usr/bin/env python3
"""
Parses a JaCoCo XML report and outputs coverage per class.
Usage: python3 parse-jacoco.py <jacoco_xml_path> [--class <ClassName>] [--classes <A,B,C>]
Output format (stdout): CLASS | LINES% | BRANCHES% | LINE_DELTA | BR_DELTA | STATUS
Gates: lines >= 92%, branches >= 90%
"""

import sys
import os
import xml.etree.ElementTree as ET

LINE_GATE = 92
BRANCH_GATE = 90


def parse(xml_path, filter_classes=None):
    if not os.path.isfile(xml_path):
        print("REPORT_NOT_FOUND", file=sys.stderr)
        sys.exit(1)

    try:
        tree = ET.parse(xml_path)
    except ET.ParseError as e:
        print(f"ERROR: failed to parse JaCoCo XML — {e}", file=sys.stderr)
        sys.exit(1)

    root = tree.getroot()
    results = []

    for package in root.findall("package"):
        for cls in package.findall("sourcefile") or package.findall("class"):
            name_attr = cls.get("name", "")
            class_name = os.path.basename(name_attr).replace(".java", "").replace("/", ".")

            if filter_classes and class_name not in filter_classes:
                continue

            lines_missed = lines_covered = 0
            branches_missed = branches_covered = 0

            for counter in cls.findall("counter"):
                ctype = counter.get("type", "")
                missed = int(counter.get("missed", 0))
                covered = int(counter.get("covered", 0))
                if ctype == "LINE":
                    lines_missed, lines_covered = missed, covered
                elif ctype == "BRANCH":
                    branches_missed, branches_covered = missed, covered

            total_lines = lines_missed + lines_covered
            total_branches = branches_missed + branches_covered

            lines_pct = round(lines_covered / total_lines * 100) if total_lines > 0 else 0
            branches_pct = (
                round(branches_covered / total_branches * 100) if total_branches > 0 else 0
            )

            line_delta = max(0, LINE_GATE - lines_pct)
            branch_delta = max(0, BRANCH_GATE - branches_pct)

            if lines_pct >= LINE_GATE and branches_pct >= BRANCH_GATE:
                status = "GATE_MET"
            else:
                status = "BELOW_GATE"

            results.append(
                (class_name, lines_pct, branches_pct, line_delta, branch_delta, status)
            )

    if not results:
        print("ERROR: no classes found in report", file=sys.stderr)
        sys.exit(1)

    # header
    print(f"{'CLASS':<45} | {'LINES%':>6} | {'BRANCHES%':>9} | {'LINE_DELTA':>10} | {'BR_DELTA':>8} | STATUS")
    print("-" * 105)
    for class_name, lp, bp, ld, bd, status in sorted(results):
        ld_str = f"+{ld}%" if ld > 0 else "—"
        bd_str = f"+{bd}%" if bd > 0 else "—"
        print(f"{class_name:<45} | {lp:>5}% | {bp:>8}% | {ld_str:>10} | {bd_str:>8} | {status}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            "ERROR: jacoco xml path required.\n"
            "Usage: python3 parse-jacoco.py <jacoco_xml_path> [--class <Name>] [--classes <A,B>]",
            file=sys.stderr,
        )
        sys.exit(1)

    xml_path = sys.argv[1]
    filter_classes = None

    if "--class" in sys.argv:
        idx = sys.argv.index("--class")
        filter_classes = {sys.argv[idx + 1]}
    elif "--classes" in sys.argv:
        idx = sys.argv.index("--classes")
        filter_classes = set(sys.argv[idx + 1].split(","))

    parse(xml_path, filter_classes)
