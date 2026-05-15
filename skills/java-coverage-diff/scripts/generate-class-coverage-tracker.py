#!/usr/bin/env python3
"""
Reads a JaCoCo XML report and generates a coverage tracker table.
Usage: python3 generate-class-coverage-tracker.py <jacoco_xml> <project_root> [--class ClassName] [--classes A,B,C] [--src-root path] [--report-name filename.md]
Output: <project_root>/docs/<report-name>.md (created automatically)
Stdout: summary + tracker table + saved path
Stderr: REPORT_NOT_FOUND or CLASS_NOT_FOUND
"""
import sys
import os
import re
import xml.etree.ElementTree as ET

LINE_GATE = 92
BRANCH_GATE = 90

BRANCH_LOGIC_PATTERN = re.compile(r'\bif\b|\bswitch\b|\bfor\b|\bwhile\b|\bdo\b|\?\s*[^:]|\&\&|\|\|')

def has_branch_logic(src_root, class_name):
    """Return True if branch coverage applies to this class.
    Only interfaces and enums/abstract classes without any conditional
    operators are exempt. POJOs, DTOs and Lombok classes are NOT exempt
    because equals/hashCode, Bean Validation and @Builder generate branches.
    """
    if not src_root:
        return True  # assume it does if we can't check
    for root_dir, _, files in os.walk(src_root):
        for fname in files:
            if fname == f"{class_name.split('.')[-1]}.java":
                fpath = os.path.join(root_dir, fname)
                try:
                    with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                        file_content = f.read()
                    has_conditionals = bool(BRANCH_LOGIC_PATTERN.search(file_content))
                    is_interface = bool(re.search(r'\binterface\b', file_content))
                    is_enum = bool(re.search(r'\benum\b', file_content))
                    is_abstract_only = bool(re.search(r'\babstract\b', file_content))
                    # Lombok/DTO signals: always require branch coverage
                    has_lombok = bool(re.search(r'@(Data|Value|Builder|EqualsAndHashCode|Getter|Setter)', file_content))
                    has_validation = bool(re.search(r'@(NotNull|NotBlank|Size|Pattern|Min|Max|Valid)', file_content))
                    has_equals = 'equals(' in file_content or 'hashCode(' in file_content
                    if has_lombok or has_validation or has_equals:
                        return True  # always requires branch coverage
                    if is_interface and not has_conditionals:
                        return False
                    if (is_enum or is_abstract_only) and not has_conditionals:
                        return False
                except Exception:
                    pass
    return True  # default: assume has logic

def parse_jacoco(xml_path, filter_classes=None, src_root=None):
    if not os.path.isfile(xml_path):
        print(f"REPORT_NOT_FOUND: {xml_path}", file=sys.stderr)
        sys.exit(1)

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"REPORT_NOT_FOUND: could not parse XML — {e}", file=sys.stderr)
        sys.exit(1)

    summary = {"lines": 0, "branches": "N/A"}
    report_lines = report_missed_lines = 0
    report_branches = report_missed_branches = 0
    for counter in root.findall('./counter'):
        ctype = counter.get('type')
        covered = int(counter.get('covered', 0))
        missed = int(counter.get('missed', 0))
        if ctype == 'LINE':
            report_lines = covered
            report_missed_lines = missed
        elif ctype == 'BRANCH':
            report_branches = covered
            report_missed_branches = missed

    total_report_lines = report_lines + report_missed_lines
    if total_report_lines > 0:
        summary["lines"] = round(report_lines / total_report_lines * 100)
    total_report_branches = report_branches + report_missed_branches
    if total_report_branches > 0:
        summary["branches"] = f"{round(report_branches / total_report_branches * 100)}%"

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

            # Determine if branch coverage is applicable
            branch_applicable = has_branch_logic(src_root, name)

            if branch_applicable and total_branches > 0:
                branch_pct = round(branches_covered / total_branches * 100)
                branch_display = f"{branch_pct}%"
                branch_delta = max(0, BRANCH_GATE - branch_pct)
                branch_delta_display = f"+{branch_delta}%" if branch_delta > 0 else "—"
                gate_met = line_pct >= LINE_GATE and branch_pct >= BRANCH_GATE
            else:
                branch_pct = None
                branch_display = "N/A"
                branch_delta_display = "N/A"
                gate_met = line_pct >= LINE_GATE  # gate based on lines only

            line_delta = max(0, LINE_GATE - line_pct)
            line_delta_display = f"+{line_delta}%" if line_delta > 0 else "—"

            if gate_met:
                status = "GATE_MET"
            elif cls.get('name', '').endswith(('Repository', 'Dao', 'Mapper')) or branch_display == "N/A":
                # Interface or no-branch class: flag only if lines below gate
                status = "GATE_MET" if line_pct >= LINE_GATE else "BELOW_GATE"
            else:
                status = "BELOW_GATE"

            results.append({
                'class': name,
                'lines': line_pct,
                'branch_display': branch_display,
                'line_delta': line_delta_display,
                'branch_delta': branch_delta_display,
                'status': status,
            })

    return summary, results

def format_table(summary, results):
    intro = [
        f"PROJECT COVERAGE: lines={summary['lines']}% | branches={summary['branches']}",
        "",
    ]
    header = f"{'CLASS':<40} | {'LINES%':>6} | {'BRANCHES%':>9} | {'LINE_DELTA':>10} | {'BRANCH_DELTA':>12} | STATUS"
    sep = '-' * len(header)
    rows = intro + [header, sep]
    for r in results:
        rows.append(
            f"{r['class']:<40} | {r['lines']:>5}% | {r['branch_display']:>9} | "
            f"{r['line_delta']:>10} | {r['branch_delta']:>12} | {r['status']}"
        )
    return '\n'.join(rows)

def resolve_output_path(project_root, report_name):
    """Always saves tracker to <project_root>/docs/<report_name>.md."""
    docs_dir = os.path.join(project_root, 'docs')
    os.makedirs(docs_dir, exist_ok=True)
    if not report_name.endswith('.md'):
        report_name = report_name + '.md'
    return os.path.join(docs_dir, report_name)

def main(xml_path, project_root, filter_classes=None, src_root=None, report_name='coverage-tracker'):
    summary, results = parse_jacoco(xml_path, filter_classes, src_root)

    if filter_classes and not results:
        print(f"CLASS_NOT_FOUND: none of {filter_classes} found in report", file=sys.stderr)
        sys.exit(1)

    table = format_table(summary, results)
    print(table)

    output_path = resolve_output_path(project_root, report_name)
    with open(output_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(table + '\n')
    print(f"\nTracker saved to: {output_path}")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: generate-class-coverage-tracker.py <jacoco_xml> <project_root> [--class Name] [--classes A,B] [--src-root path] [--report-name filename.md]\nOutput: <project_root>/docs/<report-name>.md", file=sys.stderr)
        sys.exit(1)

    xml_path = sys.argv[1]
    project_root = sys.argv[2]
    filter_classes = None
    src_root = None
    report_name = 'coverage-tracker'

    i = 3
    while i < len(sys.argv):
        if sys.argv[i] == '--class' and i + 1 < len(sys.argv):
            filter_classes = {sys.argv[i + 1]}
            i += 2
        elif sys.argv[i] == '--classes' and i + 1 < len(sys.argv):
            filter_classes = set(sys.argv[i + 1].split(','))
            i += 2
        elif sys.argv[i] == '--src-root' and i + 1 < len(sys.argv):
            src_root = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == '--report-name' and i + 1 < len(sys.argv):
            report_name = sys.argv[i + 1]
            i += 2
        else:
            i += 1

    main(xml_path, project_root, filter_classes, src_root, report_name)
