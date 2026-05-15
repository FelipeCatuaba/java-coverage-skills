# java-coverage-skills

Skill pack for Java test coverage automation with four execution scopes:

- `java-coverage-full`
- `java-coverage-module`
- `java-coverage-file`
- `java-coverage-diff`

## Versioning

This repository uses a centralized version source in:

- `skill-pack.xml`

The XML file is the source of truth for package version and included skills.

## Quick Release Flow

1. Edit `skill-pack.xml` and update `<version>`.
2. Update `CHANGELOG.md`.
3. Commit and tag:

```bash
git add .
git commit -m "chore(release): vX.Y.Z"
git tag -a vX.Y.Z -m "java-coverage-skills vX.Y.Z"
git push origin main
git push origin vX.Y.Z
```
