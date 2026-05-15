# Changelog

All notable changes to `java-coverage-skills` should be documented in this file.

This project follows Semantic Versioning (`MAJOR.MINOR.PATCH`).

## [1.0.0] - 2026-05-15

### Added
- Initial package versioning structure:
  - Root `CHANGELOG.md`.
  - Root `RELEASE.md` with release process for GitHub.
- Centralized package metadata file: `skill-pack.xml`.

### Changed
- Coverage tracker output standardized as Markdown under project root `docs/`.
- Diff flow constrained to uncommitted changes and diff-line gate evaluation.
- Module flow constrained to module-only metrics and module-scoped gate evaluation.
- Tracker update policy documented: initial snapshot + update every complete wave.
