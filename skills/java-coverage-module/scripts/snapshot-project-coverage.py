#!/usr/bin/env python3
"""
Finds JaCoCo reports automatically and generates a full project coverage snapshot.
No need to specify the XML path — the script searches the project tree.

Usage: python3 snapshot-project-coverage.py <project_root>
Output: <project_root>/docs/coverage-snapshot.md (created automatically)
Stdout: coverage tracker table sorted by line delta descending
Stderr: REPORT_NOT_FOUND with instructions if no report exists
"""
import sys
import os
import re
import xml.etree.ElementTree as ET

LINE_GATE = 92
BRANCH_GATE = 90

BRANCH_LOGIC_PATTERN = re.compile(
    r'\bif\b|\bswitch\b|\bfor\b|\bwhile\b|\bdo\b|\?\s*[^:]|\&\&|\|\|'
)

# Candidate paths where JaCoCo reports are commonly generated
JACOCO_CANDIDATES = [
    'target/site/jacoco-aggregate/jacoco.xml',  # multi-module aggregate (Maven)
    'target/site/jacoco/jacoco.xml',             # single module
    'build/reports/jacoco/test/jacocoTestReport.xml',  # Gradle
]

def find_jacoco_report(project_root):
    """Search for JaCoCo XML in known locations, prefer aggregate report."""
    for candidate in JACOCO_CANDIDATES:
        path = os.path.join(project_root, candidate)
        if os.path.isfile(path):
            return path

    # Fallback: walk the tree looking for jacoco.xml files
    found = []
    for root_dir, dirs, files in os.walk(project_root):
        # Skip node_modules, .git, etc.
        dirs[:] = [d for d in dirs if d not in {'.git', 'node_modules', '.idea'}]
        for fname in files:
            if fname == 'jacoco.xml':
                found.append(os.path.join(root_dir, fname))

    if not found:
        return None

    # Prefer aggregate reports over module-level ones
    for path in found:
        if 'jacoco-aggregate' in path:
            return path

    # Return the one closest to project root (shortest path)
    return sorted(found, key=lambda p: len(p.split(os.sep)))[0]

def has_branch_logic(src_root, class_name):
    if not src_root:
        return True
    simple_name = class_name.split('.')[-1]
    for root_dir, _, files in os.walk(src_root):
        if f"{simple_name}.java" in files:
            fpath = os.path.join(root_dir, f"{simple_name}.java")
            try:
                with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                    file_content = f.read()
                has_conditionals = bool(BRANCH_LOGIC_PATTERN.search(file_content))
                is_interface = bool(re.search(r'\binterface\b', file_content))
                is_enum = bool(re.search(r'\benum\b', file_content))
                is_abstract = bool(re.search(r'\babstract\b', file_content))
                has_lombok = bool(re.search(
                    r'@(Data|Value|Builder|EqualsAndHashCode|Getter|Setter)', file_content))
                has_validation = bool(re.search(
                    r'@(NotNull|NotBlank|Size|Pattern|Min|Max|Valid)', file_content))
                has_equals = 'equals(' in file_content or 'hashCode(' in file_content
                if has_lombok or has_validation or has_equals:
                    return True
                if is_interface and not has_conditionals:
                    return False
                if (is_enum or is_abstract) and not has_conditionals:
                    return False
            except Exception:
                pass
    return True

def parse_jacoco(xml_path, src_root=None):
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"REPORT_NOT_FOUND: could not parse XML — {e}", file=sys.stderr)
        sys.exit(1)

    results = []
    for package in root.findall('.//package'):
        pkg_name = package.get('name', '').replace('/', '.')
        for cls in package.findall('class'):
            raw_name = cls.get('name', '').replace('/', '.')
            simple_name = raw_name.split('.')[-1]

            # Skip inner classes (contain $)
            if '$' in simple_name:
                continue

            lines_covered = lines_missed = 0
            branches_covered = branches_missed = 0
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

            if total_lines == 0:
                continue  # skip empty/generated classes

            line_pct = round(lines_covered / total_lines * 100)
            branch_applicable = has_branch_logic(src_root, simple_name)

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
                gate_met = line_pct >= LINE_GATE

            line_delta = max(0, LINE_GATE - line_pct)
            line_delta_display = f"+{line_delta}%" if line_delta > 0 else "—"
            status = "GATE_MET" if gate_met else "BELOW_GATE"

            # Derive module from package path relative to project root
            module = pkg_name.split('.')[2] if len(pkg_name.split('.')) > 2 else '(root)'

            results.append({
                'module': module,
                'class': simple_name,
                'lines': line_pct,
                'branch_display': branch_display,
                'branch_pct': branch_pct if branch_pct is not None else 999,
                'line_delta': line_delta,
                'line_delta_display': line_delta_display,
                'branch_delta_display': branch_delta_display,
                'status': status,
            })

    # Sort: BELOW_GATE first, then by line_delta descending
    results.sort(key=lambda r: (r['status'] == 'GATE_MET', -r['line_delta']))
    return results

def format_table(results, report_path):
    lines = [
        f"COVERAGE SNAPSHOT — report: {report_path}",
        f"Gate: lines >= {LINE_GATE}% | branches >= {BRANCH_GATE}%",
        "",
    ]

    below = [r for r in results if r['status'] == 'BELOW_GATE']
    met = [r for r in results if r['status'] == 'GATE_MET']

    header = (f"{'MODULE':<20} {'CLASS':<35} {'LINES%':>6} {'BRANCHES%':>10} "
              f"{'LINE_DELTA':>10} {'BR_DELTA':>9} STATUS")
    sep = '-' * len(header)

    lines += [f"BELOW GATE ({len(below)} classes):", header, sep]
    for r in below:
        lines.append(
            f"{r['module']:<20} {r['class']:<35} {r['lines']:>5}% "
            f"{r['branch_display']:>10} {r['line_delta_display']:>10} "
            f"{r['branch_delta_display']:>9} {r['status']}"
        )

    lines += ["", f"GATE MET ({len(met)} classes):", header, sep]
    for r in met:
        lines.append(
            f"{r['module']:<20} {r['class']:<35} {r['lines']:>5}% "
            f"{r['branch_display']:>10} {'—':>10} {'—':>9} {r['status']}"
        )

    total = len(results)
    pct_done = round(len(met) / total * 100) if total else 0
    lines += [
        "",
        f"SUMMARY: {len(met)}/{total} classes at gate ({pct_done}%) | "
        f"{len(below)} classes need work",
    ]
    return '\n'.join(lines)

def main(project_root):
    if not os.path.isdir(project_root):
        print(f"REPORT_NOT_FOUND: project root not found: {project_root}", file=sys.stderr)
        sys.exit(1)

    report_path = find_jacoco_report(project_root)
    if not report_path:
        print(
            "REPORT_NOT_FOUND: no jacoco.xml found under project root.\n"
            "Run scripts/run-jacoco-report.py <project_root> and retry.",
            file=sys.stderr
        )
        sys.exit(1)

    src_root = os.path.join(project_root, 'src', 'main', 'java')
    if not os.path.isdir(src_root):
        # Multi-module: src lives inside each module, pass project root and let
        # has_branch_logic walk the full tree
        src_root = project_root

    results = parse_jacoco(report_path, src_root)

    if not results:
        print(
            "REPORT_NOT_FOUND: jacoco.xml was found but contains no class data.\n"
            "Ensure tests ran before generating the report: scripts/run-jacoco-report.py <project_root>",
            file=sys.stderr
        )
        sys.exit(1)

    table = format_table(results, report_path)
    print(table)

    docs_dir = os.path.join(project_root, 'docs')
    os.makedirs(docs_dir, exist_ok=True)
    output_path = os.path.join(docs_dir, 'coverage-snapshot.md')
    with open(output_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(table + '\n')
    print(f"\nSnapshot saved to: {output_path}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(
            "Usage: snapshot-project-coverage.py <project_root>\n"
            "Output: <project_root>/docs/coverage-snapshot.md\n"
            "Example: python3 snapshot-project-coverage.py /projects/customer",
            file=sys.stderr
        )
        sys.exit(1)

    root = sys.argv[1]
    main(root)
