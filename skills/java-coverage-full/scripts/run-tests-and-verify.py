#!/usr/bin/env python3
"""
Compiles and runs tests for a Maven project or module, then parses Surefire results.
"""
import glob
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET


def resolve_maven_prefix(project_root):
    mvn = shutil.which("mvn")
    if mvn:
        return [mvn]

    wrapper_cmd = "mvnw.cmd" if os.name == "nt" else "mvnw"
    wrapper_path = os.path.join(project_root, wrapper_cmd)
    if os.path.isfile(wrapper_path):
        return [wrapper_path]

    wrapper_path_alt = os.path.join(project_root, "mvnw")
    if os.path.isfile(wrapper_path_alt):
        return [wrapper_path_alt]

    return None


def build_mvn_command(project_root, module=None, test_class=None):
    prefix = resolve_maven_prefix(project_root)
    if not prefix:
        return None
    cmd = prefix + ["test", "--no-transfer-progress", "-B"]
    if module:
        cmd += ["-pl", module, "-am"]
    if test_class:
        cmd += [f"-Dtest={test_class}", "-DfailIfNoTests=false"]
    return cmd


def run_maven(project_root, module=None, test_class=None):
    cmd = build_mvn_command(project_root, module, test_class)
    if not cmd:
        print("BUILD_ERROR: Maven not found (mvn) and wrapper not found (mvnw/mvnw.cmd)", file=sys.stderr)
        sys.exit(1)

    try:
        return subprocess.run(cmd, cwd=project_root, capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:
        print("BUILD_ERROR: mvn test timed out after 600s", file=sys.stderr)
        sys.exit(1)


def detect_compile_error(stdout, stderr):
    combined = stdout + stderr
    if "COMPILATION ERROR" in combined or "BUILD FAILURE" in combined:
        lines = combined.splitlines()
        errors = []
        capture = False
        for line in lines:
            if "COMPILATION ERROR" in line:
                capture = True
            if capture:
                errors.append(line)
            if capture and len(errors) > 20:
                break
        return "\n".join(errors[:20]) if errors else "Compilation failed - check Maven output"
    return None


def parse_surefire_reports(project_root, module=None):
    if module:
        pattern = os.path.join(project_root, module, "target", "surefire-reports", "TEST-*.xml")
    else:
        pattern = os.path.join(project_root, "**", "target", "surefire-reports", "TEST-*.xml")

    report_files = glob.glob(pattern, recursive=True)
    results = []

    for fpath in report_files:
        try:
            tree = ET.parse(fpath)
            root = tree.getroot()
            name = root.get("name", os.path.basename(fpath))
            simple_name = name.split(".")[-1]
            tests = int(root.get("tests", 0))
            failures = int(root.get("failures", 0))
            errors = int(root.get("errors", 0))
            skipped = int(root.get("skipped", 0))
            passed = tests - failures - errors - skipped

            failure_messages = []
            for tc in root.findall(".//testcase"):
                for child in tc:
                    if child.tag in ("failure", "error"):
                        method = tc.get("name", "?")
                        msg = (child.get("message") or child.text or "").strip()
                        msg = msg.splitlines()[0][:120] if msg else "no message"
                        failure_messages.append(f"  x {method}: {msg}")

            status = "PASS" if (failures + errors) == 0 else "FAIL"
            results.append({
                "class": simple_name,
                "tests": tests,
                "passed": passed,
                "failures": failures,
                "errors": errors,
                "skipped": skipped,
                "status": status,
                "messages": failure_messages,
            })
        except Exception:
            pass

    return sorted(results, key=lambda r: (r["status"] == "PASS", r["class"]))


def format_summary(results):
    total_tests = sum(r["tests"] for r in results)
    total_pass = sum(r["passed"] for r in results)
    total_fail = sum(r["failures"] + r["errors"] for r in results)
    total_skip = sum(r["skipped"] for r in results)

    lines = []
    header = f"{'TEST CLASS':<45} {'TESTS':>5} {'PASS':>5} {'FAIL':>5} {'SKIP':>5}  STATUS"
    sep = "-" * len(header)
    lines += [header, sep]

    for r in results:
        lines.append(
            f"{r['class']:<45} {r['tests']:>5} {r['passed']:>5} "
            f"{r['failures'] + r['errors']:>5} {r['skipped']:>5}  {r['status']}"
        )
        if r["messages"]:
            lines += r["messages"][:5]
            if len(r["messages"]) > 5:
                lines.append(f"  ... and {len(r['messages']) - 5} more failures")

    lines += [sep, f"TOTAL: {total_tests} tests - {total_pass} passed, {total_fail} failed, {total_skip} skipped"]
    return "\n".join(lines), total_fail


def main(project_root, module=None, test_class=None):
    if not os.path.isdir(project_root):
        print(f"BUILD_ERROR: project root not found: {project_root}", file=sys.stderr)
        sys.exit(1)

    scope = f"module={module}" if module else f"class={test_class}" if test_class else "full project"
    print(f"Running tests - scope: {scope}")
    print("...")

    result = run_maven(project_root, module, test_class)

    compile_error = detect_compile_error(result.stdout, result.stderr)
    if compile_error:
        print(f"COMPILE_ERROR:\n{compile_error}", file=sys.stderr)
        print("\nACTION REQUIRED: Fix compilation errors before proceeding to coverage validation.")
        print("Do NOT run check-coverage-gate.py until all classes compile successfully.")
        sys.exit(1)

    results = parse_surefire_reports(project_root, module)

    if not results:
        if "BUILD SUCCESS" in result.stdout:
            print("NO_TESTS_FOUND: Maven built successfully but no test reports were generated.")
            print("This is expected if no test classes exist yet for this scope.")
            print("EXIT STATUS: TESTS_OK")
            return
        print("BUILD_ERROR: Maven failed and no Surefire reports found.", file=sys.stderr)
        print(result.stdout[-2000:], file=sys.stderr)
        sys.exit(1)

    summary, total_fail = format_summary(results)
    print(summary)

    if total_fail > 0:
        print(f"\nEXIT STATUS: TESTS_FAILED - {total_fail} test(s) failing")
        print("\nACTION REQUIRED: Fix failing tests before proceeding to coverage validation.")
        print("Do NOT run check-coverage-gate.py until EXIT STATUS is TESTS_OK.")
        sys.exit(1)

    print("\nEXIT STATUS: TESTS_OK - all tests passing")
    print("Coverage gate validation can proceed.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: run-tests-and-verify.py <project_root> [--module name] [--test ClassName]", file=sys.stderr)
        sys.exit(1)

    project_root = sys.argv[1]
    module = None
    test_class = None

    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--module" and i + 1 < len(sys.argv):
            module = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--test" and i + 1 < len(sys.argv):
            test_class = sys.argv[i + 1]
            i += 2
        else:
            i += 1

    main(project_root, module, test_class)
