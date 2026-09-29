# Release Process

Semantic Versioning. Source of truth: `skill-pack.xml` (`<version>`).

## 1. Update version

1. Set `<version>` in `skill-pack.xml`.
2. Add a section in `CHANGELOG.md`.

## 2. Commit

```
git add skill-pack.xml CHANGELOG.md RELEASE.md README.md skills
git commit -m "chore(release): vX.Y.Z"
```

## 3. Tag

Tag `vX.Y.Z` from the default branch and push the tag.

## 4. Publish

Create a GitHub Release from that tag. Copy notes from `CHANGELOG.md`.

## Bump rules

- `PATCH`: wording or reference fixes.
- `MINOR`: new guidance that stays compatible (same skill name and flow).
- `MAJOR`: skill rename, removed skills, or a different agent contract.
