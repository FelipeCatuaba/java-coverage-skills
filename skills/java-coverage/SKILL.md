---
name: java-coverage
description: >-
  Raises JaCoCo coverage on a Java Maven or Gradle project by writing JUnit
  tests that assert observable contracts — not coverage padding. Scopes: full
  project, one module, one class, or uncommitted git diff. Gate is 92% lines
  and 90% branches (3 waves max). Use when the user asks to generate coverage,
  raise JaCoCo, cover a class/module, or test only what changed. Do not use
  for non-Java projects or production-code refactors.
---

# Java Coverage

Playbook for an agent. No scripts. Use the project's own wrapper through the
environment shell. Never write OS-specific executables, path prefixes, or
Python helpers.

Read [generation-rules.md](references/generation-rules.md) before writing any
test. Read [test-patterns.md](references/test-patterns.md) to match the
project's JUnit style. Read [build-tooling.md](references/build-tooling.md)
only when JUnit or JaCoCo is missing.

## 1. Resolve project and scope

Infer `<project_root>` from the user path or the open workspace. Default to
the workspace root.

Infer `scope` from the request:

| Hint | Scope |
|---|---|
| A `.java` path or class name | `file` |
| A module name | `module` |
| Uncommitted / "what I changed" / diff | `diff` |
| Otherwise | `full` |

Print `TARGET: scope=<scope> root=<project_root>` and continue.

## 2. Detect build and readiness

Look at files, not commands:

- **Gradle** if `settings.gradle`, `settings.gradle.kts`, `build.gradle`, or
  `build.gradle.kts` exists.
- **Maven** if `pom.xml` exists.
- Both present: wrapper in the repo, then `settings.gradle*`, then `pom.xml`.

Modules: `<modules>` in the POM, or `include` in `settings.gradle*`.

Ready when the project already has:

- JUnit (`junit`, `junit-jupiter`, `junit-bom`, or `spring-boot-starter-test`)
- Mockito (`mockito-core`, `mockito-junit-jupiter`, or a starter that brings it)
- JaCoCo (Maven plugin, or Gradle `jacoco` plugin / `jacoco { }` block)

If something is missing: stop. Tell the user what is missing and point to
[build-tooling.md](references/build-tooling.md). Do not edit the build.

Print `READY: tool=<maven|gradle> scope=<scope>` and continue.

## 3. Measure coverage

Prefer the coverage command already documented in the project's README or CI.
Otherwise run the project's wrapper with these **task names** (not executables):

- Maven: `test` and `jacoco:report`. Narrow with `-pl` + `-am` for `module` / `file`.
- Gradle: `test` and `jacocoTestReport`. Narrow to the module task for `module` / `file`.

Then **search** for the XML. Do not hardcode a single path.

- Maven: `**/target/site/jacoco/jacoco.xml`, `**/target/site/jacoco-aggregate/jacoco.xml`
- Gradle: `**/build/reports/jacoco/**/*.xml`

If XML is still missing after a successful test run: stop. The report was not
enabled (see [build-tooling.md](references/build-tooling.md)). Do not edit the build.

Parse class counters (`LINE`, `BRANCH`). Gate:

- `LINES >= 92%`
- `BRANCHES >= 90%` when the class has branch logic
- Branch is N/A for interfaces / enums / abstract types with no conditionals
  (see [test-patterns.md](references/test-patterns.md))

Scope the class list:

- `full` — every class in the report
- `module` — classes under that module only
- `file` — the named class only
- `diff` — uncommitted production files under `**/src/main/java/**`
  (staged + unstaged + untracked). Gate those **changed lines** only.

Print a short table: class, lines, branches, status (`GATE_MET` / `BELOW_GATE`).
Skip `GATE_MET` classes. If the whole scope is already `GATE_MET`, finish.

## 4. Generate tests (max 3 waves)

A wave is: measure → write tests → run the smallest possible test task → re-measure.

When several classes are `BELOW_GATE`, work public services and caller-facing
types first. Do not spend a wave on `requireNonNull`, DTO constructors, or
private config defaults.

For each chosen class:

1. Find existing tests by walking `**/src/test/**` for `<ClassName>Test.java`
   (and obvious aliases). If several files exist, keep adding to the canonical
   `<ClassName>Test.java`.
2. Read the production class and the existing test. For each red branch,
   name the **contract** (given / when / then). If you cannot, skip it
   (`BLOCKED — no contract`).
3. Match the project's style (JUnit 4 vs 5, naming, base class, tags).
4. Write files directly under `src/test/`. Never touch `src/main/`.
5. One test class per production class. No `*Test2`, no coverage-only variants.
6. Re-read [generation-rules.md](references/generation-rules.md). Split or
   delete any method that packs scenarios, uses a weak assert, or exists only
   to paint a branch.

Fewer contract tests beat a packed method that lifts the percentage. Finishing
`STILL_BELOW` is better than keeping a sausage test.

After each wave, print the table again.

Stop a class early only for:

- `BLOCKED — boundary` — public API cannot reach the remaining branches
- `BLOCKED — no contract` — remaining branch has no caller-shaped outcome
- `BLOCKED — compile` or `BLOCKED — test failure` — still broken after two fixes
- `BLOCKED — no branches` — interface/enum, lines already at gate

After **3 waves**, stop even if some classes remain `BELOW_GATE`. That is a
valid finish (`STILL_BELOW`).

## 5. Done

Print one line:

```
DONE: <N> GATE_MET / <N> BLOCKED — <reason> / <N> STILL_BELOW
```

Progress lives in the chat only. Do not write `docs/coverage-tracker-*.md`.
