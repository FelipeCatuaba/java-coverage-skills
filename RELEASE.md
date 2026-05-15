# Release Process

This package uses Semantic Versioning (`MAJOR.MINOR.PATCH`).
Central source of truth: `skill-pack.xml` (`<version>`).

## 1. Update Version

1. Update `<version>` in `skill-pack.xml`.
2. Add a new section in `CHANGELOG.md`.

## 2. Commit

```bash
git add skill-pack.xml CHANGELOG.md RELEASE.md README.md
git commit -m "chore(release): vX.Y.Z"
```

## 3. Tag

```bash
git tag -a vX.Y.Z -m "java-coverage-skills vX.Y.Z"
git push origin main
git push origin vX.Y.Z
```

## 4. Publish on GitHub

1. Open GitHub Releases.
2. Create release from tag `vX.Y.Z`.
3. Copy notes from `CHANGELOG.md`.

## Version Bump Rules

- `PATCH`: docs/instruction fixes, non-breaking behavior adjustments.
- `MINOR`: new capabilities or backward-compatible behavior additions.
- `MAJOR`: breaking changes in flow, required inputs, or output contracts.
