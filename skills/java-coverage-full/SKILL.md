---
name: java-coverage-full
description: Generates JUnit tests for an entire Java project until reaching 92% line
  coverage and 90% branch coverage. Detects Java version (8, 11, 17+), validates pom.xml
  dependencies, consolidates duplicate test classes,
  plans generation in batch, and delivers every file as a BOM-free UTF-8 patch.
  Use when the goal is to raise coverage for the full project in one run.
  Don't use for single modules, specific files, or git diff scoped generation.
---

# Java Coverage â€” Full Project

## Entry Point â€” Autonomous Execution

This skill is triggered by phrases like:
- "use o fluxo completo no projeto <path>"
- "use a skill java-coverage-full para o projeto tal"
- "rode a skill completa para o projeto <name>"
- "run full coverage flow for <project>"
- "gere cobertura completa do projeto <path>"

When triggered, execute ALL steps in sequence from Step 1 to Step 8 WITHOUT stopping
to ask for confirmation between steps. This flow must run with no user interaction:

- If blockers happen, continue autonomously where possible.
- Report unresolved blockers only in final summary.

In all other cases: proceed autonomously, print the checkpoint output for each step,
and continue to the next step immediately.

Hard rule: this skill must execute the complete cycle (coverage analysis, test generation,
test execution, coverage re-analysis) and MUST NOT stop after only diagnostic/snapshot output.
Partial runs are not valid completion.

After completing Step 8, print the final tracker from
`docs/coverage-tracker-full.md` and a one-line summary:
```
SKILL COMPLETE: <N> GATE_MET / <N> BLOCKED â€” <reason> / <N> BOUNDARY_VIOLATION
```
Completion is valid only when there are zero `BELOW_GATE` classes in scope.

---

## Procedures

**Tracker Update Policy (Mandatory)**

1. Before generating any tests, always capture the current project state and write/update the tracker report.
2. A "wave" is: (a) coverage analysis, (b) test generation, (c) coverage re-analysis.
3. At the end of every full wave, the same tracker file must be updated in `docs/` so the user can see progress.
4. Never keep tracker values stale across waves.

**Step 1: Check Skill Readiness**

0. Resolve `<project_root>`:
   - If user provided an explicit path, use it.
   - If path is omitted, infer from open projects in workspace/IDE context.
   - If exactly one candidate project is open, use it automatically.
   - If multiple candidates are open, choose the best match using user text hints (project/module name).
   - If no safe candidate is found, default to current workspace root as `<project_root>`.
1. Run `scripts/check-skill-readiness.py <project_root>` to verify the project
   is ready for coverage generation.
2. If output is `NOT_READY: <reason>`, mark run as `BLOCKED â€” not ready` and stop.
3. Print before proceeding:
   ```
   SKILL READY: java=<8|11|17+> build=maven
   ```
4. Read `references/java-version-patterns.md` and keep it active for all steps.

**Step 2: Validate pom.xml Dependencies**

1. Run `scripts/check-pom-deps.py <pom_path> <java_version>`.
2. If output contains `MISSING: <dep>`:
   - Read `references/pom-dependency-blocks.md` for the correct XML block.
   - Apply addition as a patch (follow Step 7 encoding rules).
   - Re-run until output is `DEPS OK`.
3. Print:
   ```
   DEPS STATUS: OK â€” junit=<version> mockito=<version> jacoco=<version>
   ```

**Step 3: Snapshot Coverage â€” All Classes**

1. Run `scripts/generate-class-coverage-tracker.py <jacoco_xml_path> <project_root> --report-name coverage-tracker-full.md`.
   The tracker is always saved to `<project_root>/docs/coverage-tracker-full.md` automatically.
   The top of the report must include global project progress:
   `PROJECT COVERAGE: lines=<X>% | branches=<Y>%`.
2. Print the full tracker before proceeding:
   ```
   CLASS                    | LINES% | BRANCHES% | LINE_DELTA | BRANCH_DELTA | STATUS
   CustomerService          | 42%    | 38%       | +50%       | +52%         | BELOW_GATE
   LegacyPaymentProcessor   | 0%     | 0%        | +92%       | +90%         | BELOW_GATE
   InvoiceService           | 95%    | 91%       | â€”          | â€”            | GATE_MET
   ```
3. Classes where LINES >= 92% AND BRANCHES >= 90% are GATE_MET â€” exclude from all steps.
4. Do not proceed until the full tracker is printed.

**Step 4: Audit and Consolidate Test Classes**

1. Run `scripts/find-test-classes.py <project_root> <class_name>` for each
   class with status BELOW_GATE.
2. If more than one test file exists for the same class:
   - Consolidate all methods into <ClassName>Test.java.
   - Remove non-canonical files via patch.
   - Update tracker: CONSOLIDATED.
3. If one file exists with a non-canonical name (e.g. CustomerService_ESTest):
   - Rename to <ClassName>Test.java via patch.
   - Update tracker: RENAMED.
4. If more than 3 non-canonical files exist: auto-consolidate in batches and proceed.
5. Print: AUDIT DONE â€” consolidated: <N> / renamed: <N>

**Step 5: Plan Generation Batch**

1. For each class with status BELOW_GATE, CONSOLIDATED, or RENAMED,
   assign strategy based on line delta:

   Line Delta <= 15%  -> TARGETED  : uncovered branches only, read existing file first
   Line Delta 16-40%  -> STANDARD  : all public methods + main conditional branches
   Line Delta > 40%   -> FULL      : all public methods, branches, edge cases, mocks

2. Update tracker: PLANNED â€” strategy=<TARGETED|STANDARD|FULL>.
3. Print complete plan before generating any test:
   ```
   GENERATION PLAN:
   CustomerService        -> FULL     (lines +50%, branches +52%)
   OrderRepository        -> TARGETED (lines +1%,  branches +1%)
   LegacyPaymentProcessor -> FULL     (lines +92%, branches +90%)
   ```
4. Do not generate any test until the full plan is printed.

**Step 6: Generate Tests**

1. For each class in the plan, generate tests per strategy and patterns
   in references/java-version-patterns.md.
2. Read `references/generation-rules.md` before writing any test method.
   This file is MANDATORY â€” it defines forbidden patterns and quality requirements.
3. Rules for every generated file:
   - SCOPE: only write to `src/test/` â€” never touch any file under `src/main/`.
     If a patch path contains `src/main/`, abort it and report BOUNDARY VIOLATION.
   - SONAR: never add classes to `sonar.exclusions` or JaCoCo `<exclude>` rules.
   - QUALITY: no empty tests, no trivial assertNotNull-only tests, no catch-and-ignore.
   - PUBLIC API: test via public methods simulating real application flow â€” no reflection,
     no Whitebox, no ReflectionTestUtils.
   - One test class per production class â€” never create <Name>Test2 or variants.
   - Coverage decides generation, not file existence: if a test file already
     exists but the class is BELOW_GATE, read the existing file first, identify
     which branches and methods are NOT yet covered, and add tests for those gaps.
     Never assume coverage is sufficient because a test file exists.
   - Add methods to the existing file; never create a new file.
   - File name must be exactly <ClassName>Test.java.
3. Deliver each file as a patch following Step 7.
4. Update tracker: GENERATED â€” est_lines=<X>% est_branches=<X>%.

**Step 7: Patch Encoding Rules**

Every file created or modified must be a patch. Never write raw file content.

1. Use unified diff format:
   --- a/src/test/java/com/example/CustomerServiceTest.java
   +++ b/src/test/java/com/example/CustomerServiceTest.java
2. Run scripts/validate-patch.py <patch_file> before presenting.
3. If BOM_DETECTED or CRLF_DETECTED: fix and re-validate.
   After two failed attempts: mark class as `BLOCKED â€” patch encoding` and continue.
4. Mandatory for every patch:
   - No BOM (0xEF 0xBB 0xBF forbidden at file start).
   - LF only (\n â€” no \r\n).
   - UTF-8 without BOM.

**Step 7.5: Compile and Verify Tests**

1. Run `scripts/run-tests-and-verify.py <project_root>` after all patches from
   Step 6 are applied.
2. Evaluate the output:
   - `EXIT STATUS: TESTS_OK`: all tests compile and pass â€” proceed to Step 8.
   - `COMPILE_ERROR`: one or more test classes failed to compile.
     Fix the affected patch(es) and re-apply before re-running this step.
   - `EXIT STATUS: TESTS_FAILED`: tests compiled but assertions are failing.
     Read the failure details printed per class and fix the test logic before
     re-running this step.
   - `NO_TESTS_FOUND`: no test classes exist yet for this scope â€” this is
     expected on the first run before any patches are applied. Proceed to Step 8.
3. Do NOT run `scripts/check-coverage-gate.py` (Step 8) until this step
   exits with `TESTS_OK` or `NO_TESTS_FOUND`.
4. Maximum two fix-and-retry rounds per failing class. If a class still fails
   after two rounds: mark it `NEEDS_REVIEW â€” test failure` in the tracker,
   skip it in Step 8, and continue autonomously with remaining classes.

**Step 8: Validate Coverage â€” Gate is Mandatory**

Gate: LINES >= 92% AND BRANCHES >= 90% per class. The skill does NOT finish
until every class in scope reaches the gate or is explicitly blocked by a
BOUNDARY_VIOLATION or a persistent COMPILE_ERROR / test failure.

1. Run `scripts/check-coverage-gate.py <project_root> <jacoco_xml_path>`.
2. Update tracker with real values and print:
   ```
   CLASS                  | LINES% | BRANCHES% | STATUS
   CustomerService        | 94%    | 91%       | GATE_MET
   LegacyPaymentProcessor | 88%    | 85%       | BELOW_GATE
   ```
3. For each class still BELOW_GATE, run additional generation rounds:
   - Determine remaining delta and assign strategy (TARGETED / STANDARD / FULL).
   - Generate complement tests, apply patch, re-run Step 7.5, then re-validate.
   - After each re-validation, re-run `scripts/generate-class-coverage-tracker.py <jacoco_xml_path> <project_root> --report-name coverage-tracker-full.md` to overwrite the tracker with the latest wave state.
     Confirm that the `PROJECT COVERAGE` line at the top reflects the new wave progress.
   - Repeat until the class reaches GATE_MET.
4. A class may only be marked `BLOCKED` (and excluded from further rounds) if
   one of these hard blockers applies â€” document the reason explicitly:
   - `BLOCKED â€” boundary`: production class cannot be touched and public API
     does not expose enough behaviour to reach the gate.
   - `BLOCKED â€” compile`: test class fails to compile after three fix attempts.
   - `BLOCKED â€” test failure`: tests keep failing after three fix attempts.
   - `BLOCKED â€” no branches`: class has N/A branch coverage (interface/enum)
     and lines are >= 92%.
   Any other reason is NOT a valid blocker. Keep generating.
5. Run `scripts/cleanup-generated-logs.py <project_root>`.
6. Print the final tracker in full, then print the mandatory summary line:
   ```
   SKILL COMPLETE: <N> GATE_MET / <N> BLOCKED â€” <reason> / <N> BOUNDARY_VIOLATION
   ```
   The skill is only considered finished when every class is either GATE_MET or BLOCKED
   with an explicit documented reason. BELOW_GATE is not an acceptable final state.
7. If any class remains BELOW_GATE, start a new full wave immediately and continue until
   the completion condition above is satisfied.

## Error Handling

* check-skill-readiness.py returns NOT_READY: mark run as `BLOCKED â€” not ready` and stop.
* generate-class-coverage-tracker.py fails REPORT_NOT_FOUND: run
  `scripts/run-jacoco-report.py <project_root>` and retry automatically.
* check-pom-deps.py returns UNSUPPORTED_STRUCTURE: read error section of
  references/pom-dependency-blocks.md and report blocker to user.
* validate-patch.py returns encoding error after two attempts: mark class as
  `BLOCKED â€” patch encoding` and continue with remaining classes.
* run-tests-and-verify.py returns COMPILE_ERROR: fix the patch for the affected
  class and re-run before proceeding. Do not validate coverage with broken tests.
* run-tests-and-verify.py returns TESTS_FAILED after three fix attempts: mark
  the class as BLOCKED â€” test failure in the tracker, document the reason,
  and report to user. This is the only condition that allows skipping a class.
* If any patch path contains `src/main/`: BOUNDARY VIOLATION â€” abort that patch
  immediately, report the path to the user, and skip the class. Never modify
  production source files under any circumstance.


