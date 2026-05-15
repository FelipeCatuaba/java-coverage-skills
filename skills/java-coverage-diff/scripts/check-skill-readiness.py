#!/usr/bin/env python3
"""
Verifies that a Java Maven project is ready for coverage generation.
Usage: python3 check-skill-readiness.py <project_root>
Stdout: SKILL READY: java=<8|11|17+> build=maven
Stderr: NOT_READY: <reason>
"""
import sys
import os
import xml.etree.ElementTree as ET

def detect_java_version(pom_path):
    try:
        tree = ET.parse(pom_path)
        root = tree.getroot()
        ns = root.tag.split('}')[0].strip('{') if '}' in root.tag else ''
        prefix = f'{{{ns}}}' if ns else ''

        for tag in ['maven.compiler.source', 'java.version', 'maven.compiler.release']:
            el = root.find(f'.//{prefix}properties/{prefix}{tag}')
            if el is not None and el.text:
                v = el.text.strip().replace('1.', '')
                version = int(v.split('.')[0])
                if version <= 8:
                    return '8'
                elif version == 11:
                    return '11'
                else:
                    return '17+'

        for plugin_tag in [f'.//{prefix}plugin']:
            for plugin in root.findall(plugin_tag):
                artifact = plugin.find(f'{prefix}artifactId')
                if artifact is not None and 'compiler' in (artifact.text or ''):
                    for config_child in plugin.iter(f'{prefix}source'):
                        v = config_child.text.strip().replace('1.', '')
                        version = int(v.split('.')[0])
                        if version <= 8:
                            return '8'
                        elif version == 11:
                            return '11'
                        else:
                            return '17+'
    except Exception:
        pass
    return None

def main(project_root):
    if not os.path.isdir(project_root):
        print(f"NOT_READY: project root not found: {project_root}", file=sys.stderr)
        sys.exit(1)

    pom_path = os.path.join(project_root, 'pom.xml')
    if not os.path.isfile(pom_path):
        print("NOT_READY: pom.xml not found — not a Maven project", file=sys.stderr)
        sys.exit(1)

    java_version = detect_java_version(pom_path)
    if not java_version:
        print("NOT_READY: could not detect Java version from pom.xml", file=sys.stderr)
        sys.exit(1)

    print(f"SKILL READY: java={java_version} build=maven")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("NOT_READY: missing argument.\nUsage: check-skill-readiness.py <project_root>", file=sys.stderr)
        sys.exit(1)
    main(sys.argv[1])
