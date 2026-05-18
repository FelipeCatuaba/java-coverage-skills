#!/usr/bin/env python3
"""
Runs `mvn test jacoco:report`.

Usage:
  python3 run-jacoco-report.py <project_root>
"""
import os
import subprocess
import sys


def main(project_root: str) -> int:
    if not os.path.isdir(project_root):
        print(f"BUILD_ERROR: project root not found: {project_root}", file=sys.stderr)
        return 1

    cmd = ["mvn", "test", "jacoco:report", "--no-transfer-progress", "-B"]
    try:
        result = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=600,
        )
    except FileNotFoundError:
        print("BUILD_ERROR: mvn command not found — ensure Maven is installed and on PATH", file=sys.stderr)
        return 1
    except subprocess.TimeoutExpired:
        print("BUILD_ERROR: mvn test jacoco:report timed out after 600s", file=sys.stderr)
        return 1

    if result.returncode != 0:
        print("BUILD_ERROR: mvn test jacoco:report failed", file=sys.stderr)
        tail = (result.stdout + "\n" + result.stderr)[-8000:]
        print(tail, file=sys.stderr)
        return result.returncode

    print("JACOCO_REPORT_OK")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: run-jacoco-report.py <project_root>", file=sys.stderr)
        raise SystemExit(1)
    raise SystemExit(main(sys.argv[1]))
