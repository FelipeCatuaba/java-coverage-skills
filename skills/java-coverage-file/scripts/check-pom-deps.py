#!/usr/bin/env python3
"""
Checks if required test dependencies are present in pom.xml.
Usage: python3 check-pom-deps.py <pom_path> <java_version>
Stdout: DEPS OK — junit=<v> mockito=<v> jacoco=<v>
        MISSING: <dep> (one line per missing dep)
Stderr: error messages
"""
import sys
import os
import xml.etree.ElementTree as ET

REQUIRED_DEPS = {
    '8':   {'junit': 'junit', 'mockito': 'mockito-core', 'jacoco': 'jacoco-maven-plugin'},
    '11':  {'junit': 'junit-jupiter', 'mockito': 'mockito-core', 'jacoco': 'jacoco-maven-plugin'},
    '17+': {'junit': 'junit-jupiter', 'mockito': 'mockito-core', 'jacoco': 'jacoco-maven-plugin'},
}

def get_ns(root):
    return f'{{{root.tag.split("}")[0][1:]}}}' if '}' in root.tag else ''

def find_version(root, ns, artifact_id):
    for dep in root.findall(f'.//{ns}dependency'):
        artifact = dep.find(f'{ns}artifactId')
        version = dep.find(f'{ns}version')
        if artifact is not None and artifact_id in (artifact.text or ''):
            return (version.text if version is not None else 'managed') or 'managed'
    for plugin in root.findall(f'.//{ns}plugin'):
        artifact = plugin.find(f'{ns}artifactId')
        version = plugin.find(f'{ns}version')
        if artifact is not None and artifact_id in (artifact.text or ''):
            return (version.text if version is not None else 'managed') or 'managed'
    return None

def main(pom_path, java_version):
    if not os.path.isfile(pom_path):
        print(f"UNSUPPORTED_STRUCTURE: pom.xml not found at {pom_path}", file=sys.stderr)
        sys.exit(1)

    version_key = java_version if java_version in REQUIRED_DEPS else '17+'

    try:
        tree = ET.parse(pom_path)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"UNSUPPORTED_STRUCTURE: could not parse pom.xml — {e}", file=sys.stderr)
        sys.exit(1)

    ns = get_ns(root)
    required = REQUIRED_DEPS[version_key]
    found = {}
    missing = []

    for label, artifact_id in required.items():
        version = find_version(root, ns, artifact_id)
        if version:
            found[label] = version
        else:
            missing.append(artifact_id)

    for dep in missing:
        print(f"MISSING: {dep}")

    if not missing:
        junit_v = found.get('junit', 'unknown')
        mockito_v = found.get('mockito', 'unknown')
        jacoco_v = found.get('jacoco', 'unknown')
        print(f"DEPS OK — junit={junit_v} mockito={mockito_v} jacoco={jacoco_v}")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: check-pom-deps.py <pom_path> <java_version>", file=sys.stderr)
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
