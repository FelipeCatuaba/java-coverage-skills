#!/usr/bin/env python3
"""
Runs JaCoCo report for a Maven project with a fast path.

Strategy:
1) Fast path: generate report without re-running tests (`-DskipTests`).
2) Fallback: if report artifacts are missing, run `test jacoco:report`.

Usage:
  python run-jacoco-report.py <project_root>
"""
import os
import shutil
import subprocess
import sys
from typing import List, Optional, Tuple


def resolve_maven_cmd(project_root: str) -> Optional[List[str]]:
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


def run_cmd(cmd: List[str], project_root: str, timeout_sec: int) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=project_root,
        capture_output=True,
        text=True,
        timeout=timeout_sec,
    )


def has_jacoco_artifacts(project_root: str) -> bool:
    exec_file = os.path.join(project_root, "target", "jacoco.exec")
    xml_file = os.path.join(project_root, "target", "site", "jacoco", "jacoco.xml")
    return os.path.isfile(exec_file) and os.path.isfile(xml_file)


def tail_output(result: subprocess.CompletedProcess, max_chars: int = 8000) -> str:
    return (result.stdout + "\n" + result.stderr)[-max_chars:]


def try_fast_report(mvn_cmd: List[str], project_root: str) -> Tuple[bool, Optional[subprocess.CompletedProcess]]:
    cmd = mvn_cmd + ["-DskipTests", "jacoco:report", "--no-transfer-progress", "-B"]
    try:
        result = run_cmd(cmd, project_root, timeout_sec=420)
    except subprocess.TimeoutExpired:
        print("WARN: fast JaCoCo report timed out; switching to fallback full run.")
        return False, None

    if result.returncode == 0 and has_jacoco_artifacts(project_root):
        print("JACOCO_REPORT_OK (fast path: skipTests)")
        return True, result

    return False, result


def run_fallback_full(mvn_cmd: List[str], project_root: str) -> int:
    cmd = mvn_cmd + ["test", "jacoco:report", "--no-transfer-progress", "-B"]
    try:
        result = run_cmd(cmd, project_root, timeout_sec=1200)
    except subprocess.TimeoutExpired:
        print("BUILD_ERROR: mvn test jacoco:report timed out after 1200s", file=sys.stderr)
        return 1

    if result.returncode != 0:
        print("BUILD_ERROR: mvn test jacoco:report failed", file=sys.stderr)
        print(tail_output(result), file=sys.stderr)
        return result.returncode

    if not has_jacoco_artifacts(project_root):
        print("BUILD_ERROR: JaCoCo artifacts were not generated after fallback run", file=sys.stderr)
        return 1

    print("JACOCO_REPORT_OK (fallback: test + report)")
    return 0


def main(project_root: str) -> int:
    if not os.path.isdir(project_root):
        print(f"BUILD_ERROR: project root not found: {project_root}", file=sys.stderr)
        return 1

    mvn_cmd = resolve_maven_cmd(project_root)
    if not mvn_cmd:
        print(
            "BUILD_ERROR: Maven not found (mvn) and wrapper not found (mvnw/mvnw.cmd)",
            file=sys.stderr,
        )
        return 1

    ok, result = try_fast_report(mvn_cmd, project_root)
    if ok:
        return 0

    if result is not None and result.returncode != 0:
        print("INFO: fast path failed, using fallback full run.")

    return run_fallback_full(mvn_cmd, project_root)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: run-jacoco-report.py <project_root>", file=sys.stderr)
        raise SystemExit(1)
    raise SystemExit(main(sys.argv[1]))