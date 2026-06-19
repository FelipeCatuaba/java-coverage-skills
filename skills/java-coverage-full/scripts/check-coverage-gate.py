#!/usr/bin/env python3
"""
Reads JaCoCo XML and checks which classes meet the coverage gate.
Usage: python check-coverage-gate.py <project_root> <jacoco_xml> [--class Name] [--classes A,B]

Rule:
- LINE gate is always required.
- BRANCH gate is required only when branch counter exists (>0 branches).
"""
import os
import sys
import xml.etree.ElementTree as ET

LINE_GATE = 92
BRANCH_GATE = 90


def parse_coverage(xml_path, filter_classes=None):
    if not os.path.isfile(xml_path):
        print(f"REPORT_NOT_FOUND: {xml_path}", file=sys.stderr)
        sys.exit(1)

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"REPORT_NOT_FOUND: could not parse XML - {e}", file=sys.stderr)
        sys.exit(1)

    results = []
    for package in root.findall('.//package'):
        for cls in package.findall('class'):
            name = cls.get('name', '').replace('/', '.').split('.')[-1]
            if filter_classes and name not in filter_classes:
                continue

            lines_covered = lines_missed = branches_covered = branches_missed = 0
            for counter in cls.findall('counter'):
                ctype = counter.get('type')
                covered = int(counter.get('covered', 0))
                missed = int(counter.get('missed', 0))
                if ctype == 'LINE':
                    lines_covered, lines_missed = covered, missed
                elif ctype == 'BRANCH':
                    branches_covered, branches_missed = covered, missed

            total_lines = lines_covered + lines_missed
            total_branches = branches_covered + branches_missed

            line_pct = round(lines_covered / total_lines * 100) if total_lines > 0 else 0

            if total_branches > 0:
                branch_pct = round(branches_covered / total_branches * 100)
                branch_display = f"{branch_pct}%"
                gate_met = line_pct >= LINE_GATE and branch_pct >= BRANCH_GATE
            else:
                branch_pct = None
                branch_display = 'N/A'
                gate_met = line_pct >= LINE_GATE

            status = 'GATE_MET' if gate_met else 'BELOW_GATE'
            results.append({'class': name, 'lines': line_pct, 'branches': branch_display, 'status': status})

    return results


def main(project_root, xml_path, filter_classes=None):
    _ = project_root  # reserved for compatibility
    results = parse_coverage(xml_path, filter_classes)

    header = f"{'CLASS':<40} | {'LINES%':>6} | {'BRANCHES%':>9} | STATUS"
    print(header)
    print('-' * len(header))
    for r in results:
        print(f"{r['class']:<40} | {r['lines']:>5}% | {r['branches']:>9} | {r['status']}")


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: check-coverage-gate.py <project_root> <jacoco_xml> [--class Name] [--classes A,B]', file=sys.stderr)
        sys.exit(1)

    project_root = sys.argv[1]
    xml_path = sys.argv[2]
    filter_classes = None

    i = 3
    while i < len(sys.argv):
        if sys.argv[i] == '--class' and i + 1 < len(sys.argv):
            filter_classes = {sys.argv[i + 1]}
            i += 2
        elif sys.argv[i] == '--classes' and i + 1 < len(sys.argv):
            filter_classes = set(sys.argv[i + 1].split(','))
            i += 2
        else:
            i += 1

    main(project_root, xml_path, filter_classes)
