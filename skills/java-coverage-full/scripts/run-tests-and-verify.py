#!/usr/bin/env python3
"""
Compiles and runs tests for a Maven project or module, then parses Surefire results.
Must be run AFTER patches are applied and BEFORE coverage gate validation.

Usage:
  Full project : python3 run-tests-and-verify.py <project_root>
  Single module: python3 run-tests-and-verify.py <project_root> --module <module_name>
  Single class : python3 run-tests-and-verify.py <project_root> --test <ClassName>Test

Stdout:
  TEST RUN SUMMARY with pass/fail/error counts per class
  EXIT STATUS: TESTS_OK or TESTS_FAILED

Stderr:
  COMPILE_ERROR: <details> if compilation fails before tests run
  BUILD_ERROR: <details> if Maven itself fails
"""
import sys
import os
import subprocess
import xml.etree.ElementTree as ET
import glob

def build_mvn_command(project_root, module=None, test_class=None):
    cmd = ['mvn', 'test', '--no-transfer-progress', '-B']
    if module:
        cmd += ['-pl', module, '-am']
    if test_class:
        cmd += [f'-Dtest={test_class}', '-DfailIfNoTests=false']
    return cmd

def run_maven(project_root, module=None, test_class=None):
    cmd = build_mvn_command(project_root, module, test_class)
    try:
        result = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=300
        )
        return result
    except FileNotFoundError:
        print("BUILD_ERROR: mvn command not found — ensure Maven is installed and on PATH",
              file=sys.stderr)
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("BUILD_ERROR: mvn test timed out after 300s", file=sys.stderr)
        sys.exit(1)

def detect_compile_error(stdout, stderr):
    combined = stdout + stderr
    if 'COMPILATION ERROR' in combined or 'BUILD FAILURE' in combined:
        lines = combined.splitlines()
        errors = []
        capture = False
        for line in lines:
            if 'COMPILATION ERROR' in line:
                capture = True
            if capture:
                errors.append(line)
            if capture and len(errors) > 20:
                break
        return '\n'.join(errors[:20]) if errors else "Compilation failed — check Maven output"
    return None

def parse_surefire_reports(project_root, module=None):
    """Parse XML Surefire reports to get per-class pass/fail/error counts."""
    if module:
        pattern = os.path.join(project_root, module,
                               'target', 'surefire-reports', 'TEST-*.xml')
    else:
        pattern = os.path.join(project_root, '**',
                               'target', 'surefire-reports', 'TEST-*.xml')

    report_files = glob.glob(pattern, recursive=True)

    results = []
    for fpath in report_files:
        try:
            tree = ET.parse(fpath)
            root = tree.getroot()
            name = root.get('name', os.path.basename(fpath))
            simple_name = name.split('.')[-1]
            tests = int(root.get('tests', 0))
            failures = int(root.get('failures', 0))
            errors = int(root.get('errors', 0))
            skipped = int(root.get('skipped', 0))
            passed = tests - failures - errors - skipped

            failure_messages = []
            for tc in root.findall('.//testcase'):
                for child in tc:
                    if child.tag in ('failure', 'error'):
                        method = tc.get('name', '?')
                        msg = (child.get('message') or child.text or '').strip()
                        msg = msg.splitlines()[0][:120] if msg else 'no message'
                        failure_messages.append(f"  ✗ {method}: {msg}")

            status = 'PASS' if (failures + errors) == 0 else 'FAIL'
            results.append({
                'class': simple_name,
                'tests': tests,
                'passed': passed,
                'failures': failures,
                'errors': errors,
                'skipped': skipped,
                'status': status,
                'messages': failure_messages,
            })
        except Exception:
            pass

    return sorted(results, key=lambda r: (r['status'] == 'PASS', r['class']))

def format_summary(results):
    total_tests = sum(r['tests'] for r in results)
    total_pass = sum(r['passed'] for r in results)
    total_fail = sum(r['failures'] + r['errors'] for r in results)
    total_skip = sum(r['skipped'] for r in results)

    lines = []
    header = f"{'TEST CLASS':<45} {'TESTS':>5} {'PASS':>5} {'FAIL':>5} {'SKIP':>5}  STATUS"
    sep = '-' * len(header)
    lines += [header, sep]

    for r in results:
        lines.append(
            f"{r['class']:<45} {r['tests']:>5} {r['passed']:>5} "
            f"{r['failures'] + r['errors']:>5} {r['skipped']:>5}  {r['status']}"
        )
        if r['messages']:
            lines += r['messages'][:5]  # max 5 failure details per class
            if len(r['messages']) > 5:
                lines.append(f"  ... and {len(r['messages']) - 5} more failures")

    lines += [
        sep,
        f"TOTAL: {total_tests} tests — {total_pass} passed, "
        f"{total_fail} failed, {total_skip} skipped",
    ]
    return '\n'.join(lines), total_fail

def main(project_root, module=None, test_class=None):
    if not os.path.isdir(project_root):
        print(f"BUILD_ERROR: project root not found: {project_root}", file=sys.stderr)
        sys.exit(1)

    scope = f"module={module}" if module else f"class={test_class}" if test_class else "full project"
    print(f"Running tests — scope: {scope}")
    print("...")

    result = run_maven(project_root, module, test_class)

    # Check compile error first
    compile_error = detect_compile_error(result.stdout, result.stderr)
    if compile_error:
        print(f"COMPILE_ERROR:\n{compile_error}", file=sys.stderr)
        print("\nACTION REQUIRED: Fix compilation errors before proceeding to coverage validation.")
        print("Do NOT run check-coverage-gate.py until all classes compile successfully.")
        sys.exit(1)

    # Parse Surefire reports
    results = parse_surefire_reports(project_root, module)

    if not results:
        # Maven ran but no Surefire XMLs found — could be no tests exist yet
        if 'BUILD SUCCESS' in result.stdout:
            print("NO_TESTS_FOUND: Maven built successfully but no test reports were generated.")
            print("This is expected if no test classes exist yet for this scope.")
            print("EXIT STATUS: TESTS_OK")
            return
        else:
            print("BUILD_ERROR: Maven failed and no Surefire reports found.", file=sys.stderr)
            print(result.stdout[-2000:], file=sys.stderr)
            sys.exit(1)

    summary, total_fail = format_summary(results)
    print(summary)

    if total_fail > 0:
        print(f"\nEXIT STATUS: TESTS_FAILED — {total_fail} test(s) failing")
        print("\nACTION REQUIRED: Fix failing tests before proceeding to coverage validation.")
        print("Do NOT run check-coverage-gate.py until EXIT STATUS is TESTS_OK.")
        sys.exit(1)
    else:
        print("\nEXIT STATUS: TESTS_OK — all tests passing")
        print("Coverage gate validation can proceed.")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(
            "Usage: run-tests-and-verify.py <project_root> [--module name] [--test ClassName]\n"
            "Example (full):   python3 run-tests-and-verify.py /projects/customer\n"
            "Example (module): python3 run-tests-and-verify.py /projects/customer --module payment-service\n"
            "Example (class):  python3 run-tests-and-verify.py /projects/customer --test OrderServiceTest",
            file=sys.stderr
        )
        sys.exit(1)

    project_root = sys.argv[1]
    module = None
    test_class = None

    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == '--module' and i + 1 < len(sys.argv):
            module = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == '--test' and i + 1 < len(sys.argv):
            test_class = sys.argv[i + 1]
            i += 2
        else:
            i += 1

    main(project_root, module, test_class)
