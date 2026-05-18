---
name: java-coverage-module
description: Generates JUnit tests for a single module of a Maven multi-module Java project
  until reaching 92% line coverage and 90% branch coverage. Applies the same full-project
  logic (pom validation, batch generation, patch encoding)
  scoped exclusively to the target module. Use when the project is multi-module and only one
  module needs coverage improvement. Don't use for full project runs, single files, or
  git diff scoped generation.
---

# Java Coverage â€” Single Module

## Entry Point â€” Autonomous Execution

This skill is triggered by phrases like:
- "use o fluxo de mÃ³dulos no mÃ³dulo <name>"
- "rode a skill de mÃ³dulo para o mÃ³dulo <name>"
- "run module coverage flow for <module>"
- "gere cobertura do mÃ³dulo <name>"

When triggered, execute ALL steps in sequence from Step 1 to Step 9 WITHOUT stopping
to ask for confirmation between steps. This flow must run with no user interaction:

- No user input is required during execution.
- If blockers happen, the skill must continue autonomously where possible and
  only report final blockers in the completion summary.

In all other cases: proceed autonomously, print the checkpoint output for each step,
and continue to the next step immediately.

Hard rule: this skill must execute the complete cycle (coverage analysis, test generation,
test execution, coverage re-analysis) and MUST NOT stop after only diagnostic/snapshot output.
Partial runs are not valid completion.

After completing Step 9, print the final tracker from
`<project_root>/docs/coverage-tracker-<module_name>.md` and a one-line summary:
```
SKILL COMPLETE (module: <name>): <N> GATE_MET / <N> BLOCKED â€” <reason>
```
Completion is valid only when there are zero `BELOW_GATE` classes in the selected module.

---

## Procedures

**Tracker Update Policy (Mandatory)**

1. Before generating any tests, always capture the current module state and write/update the tracker report.
2. A "wave" is: (a) coverage analysis, (b) test generation, (c) coverage re-analysis.
3. At the end of every full wave, the same tracker file must be updated in `<project_root>/docs/`.
4. Never keep tracker values stale across waves.

**Step 1: Resolve Module**

1. Run `scripts/resolve-module.py <project_root>` to list all Maven modules.
2. Print the module list:
   ```
   MODULES FOUND:
   [0] payment-service    (src/main/java â€” 12 classes)
   [1] order-service      (src/main/java â€” 8 classes)
   [2] shared-lib         (src/main/java â€” 5 classes)
   ```
3. If the user already specified a module name: match it against the list.
   If no module was specified: auto-select the best candidate module by:
   - path/name hint from user message;
   - highest class count if no hint is available.
4. If module name is ambiguous (multiple partial matches), auto-select using:
   - exact match > prefix match > contains match;
   - if still tied, choose the largest module by class count.
5. Print the resolved target before proceeding:
   ```
   TARGET MODULE: <module_name> â€” root: <module_path>
   ```
6. Use `<module_path>` as the scoped root for all subsequent steps.
   Never read or modify files outside this path.

**Step 2: Check Skill Readiness (Module Scope)**

1. Run `scripts/check-skill-readiness.py <module_path>` to verify the module
   is ready for coverage generation.
2. If output is `NOT_READY: <reason>`, report the reason and stop.
3. Print:
   ```
   SKILL READY: java=<8|11|17+> build=maven module=<module_name>
   ```
4. Read `references/java-version-patterns.md` and keep it active for all steps.

**Step 3: Validate pom.xml Dependencies (Module pom)**

1. Run `scripts/check-pom-deps.py <module_path>/pom.xml <java_version>`.
2. If `MISSING: <dep>`: read `references/pom-dependency-blocks.md`, apply as patch,
   re-run until `DEPS OK`.
3. Print:
   ```
   DEPS STATUS: OK â€” junit=<version> mockito=<version> jacoco=<version>
   ```

**Step 4: Snapshot Coverage â€” Module Classes Only**

1. Run `scripts/generate-class-coverage-tracker.py <module_jacoco_xml> <project_root> --report-name coverage-tracker-<module_name>.md`.
   The tracker is always saved to `<project_root>/docs/coverage-tracker-<module_name>.md` automatically.
   The top of the report must include module progress:
   `PROJECT COVERAGE: lines=<X>% | branches=<Y>%` (calculated from the module report).
   The JaCoCo report must be the module-level report, not the aggregated root report.
   Never use any aggregated report under the repository root for this skill.
2. Print the full tracker for this module only:
   ```
   CLASS                    | LINES% | BRANCHES% | LINE_DELTA | BRANCH_DELTA | STATUS
   PaymentProcessor         | 55%    | 48%       | +37%       | +42%         | BELOW_GATE
   PaymentValidator         | 92%    | 90%       | â€”          | â€”            | GATE_MET
   ```
3. Classes where LINES >= 92% AND BRANCHES >= 90% are GATE_MET â€” exclude from all steps.
4. Do not proceed until the full tracker is printed.

**Step 5: Audit and Consolidate Test Classes**

1. Run `scripts/find-test-classes.py <module_path> <class_name>` for each BELOW_GATE class.
2. If more than one test file exists for the same class:
   - Consolidate all methods into <ClassName>Test.java.
   - Remove non-canonical files via patch.
   - Update tracker: CONSOLIDATED.
3. If one file with non-canonical name exists: rename via patch. Update tracker: RENAMED.
4. If more than 3 non-canonical files: auto-consolidate in batches into the canonical file and continue.
5. Print: AUDIT DONE â€” consolidated: <N> / renamed: <N>

**Step 6: Plan Generation Batch**

1. For each class with status BELOW_GATE, CONSOLIDATED, or RENAMED,
   assign strategy based on line delta:

   Line Delta <= 15%  -> TARGETED  : uncovered branches only, read existing file first
   Line Delta 16-40%  -> STANDARD  : all public methods + main conditional branches
   Line Delta > 40%   -> FULL      : all public methods, branches, edge cases, mocks

2. Update tracker: PLANNED â€” strategy=<TARGETED|STANDARD|FULL>.
3. Print complete plan:
   ```
   GENERATION PLAN (module: <module_name>):
   PaymentProcessor  -> FULL     (lines +37%, branches +42%)
   RefundService     -> STANDARD (lines +20%, branches +25%)
   ```
4. Do not generate any test until the full plan is printed.

**Step 7: Generate Tests**

1. Generate tests per strategy and patterns in references/java-version-patterns.md.
2. Read `references/generation-rules.md` before writing any test method.
   This file is MANDATORY â€” it defines forbidden patterns and quality requirements.
3. Rules:
   - SCOPE: only write to `src/test/` inside <module_path> â€” never touch `src/main/`.
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
   - All output files must be inside <module_path>.
3. Deliver each file as a patch following Step 8.
4. Update tracker: GENERATED â€” est_lines=<X>% est_branches=<X>%.

**Step 8: Patch Encoding Rules**

Every file created or modified must be a patch. Never write raw file content.

1. Use unified diff format:
   --- a/<module_path>/src/test/java/com/example/PaymentProcessorTest.java
   +++ b/<module_path>/src/test/java/com/example/PaymentProcessorTest.java
2. Run scripts/validate-patch.py <patch_file> before presenting.
3. If BOM_DETECTED or CRLF_DETECTED: fix and re-validate.
   After two failed attempts: mark class as `BLOCKED â€” patch encoding` and continue with remaining classes.
4. Mandatory for every patch:
   - No BOM (0xEF 0xBB 0xBF forbidden).
   - LF only (\n â€” no \r\n).
   - UTF-8 without BOM.

**Step 8.5: Compile and Verify Tests**

1. Run `scripts/run-tests-and-verify.py <project_root> --module <module_name>` after all patches from
   Step 8 are applied. Test execution and verification must stay scoped to `<module_name>`.
2. Evaluate the output:
   - `EXIT STATUS: TESTS_OK`: all tests compile and pass â€” proceed to Step 9.
   - `COMPILE_ERROR`: one or more test classes failed to compile.
     Fix the affected patch(es) and re-apply before re-running this step.
   - `EXIT STATUS: TESTS_FAILED`: tests compiled but assertions are failing.
     Read the failure details printed per class and fix the test logic before
     re-running this step.
   - `NO_TESTS_FOUND`: no test classes exist yet for this scope â€” this is
     expected on the first run before any patches are applied. Proceed to Step 9.
3. Do NOT run `scripts/check-coverage-gate.py` (Step 9) until this step
   exits with `TESTS_OK` or `NO_TESTS_FOUND`.
4. Maximum two fix-and-retry rounds per failing class. If a class still fails
   after two rounds: mark it `NEEDS_REVIEW â€” test failure` in the tracker,
   skip it in Step 9, and continue autonomously with remaining classes.

**Step 9: Validate Coverage â€” Gate is Mandatory**

Gate: LINES >= 92% AND BRANCHES >= 90% per class. The skill does NOT finish
until every class in scope reaches the gate or is explicitly blocked.

1. Run `scripts/check-coverage-gate.py <module_path> <module_jacoco_xml>`.
   Gate calculation must consider only classes from `<module_path>` and only
   metrics from `<module_jacoco_xml>` for the selected module.
2. Update tracker with real values and print:
   ```
   CLASS              | LINES% | BRANCHES% | STATUS
   PaymentProcessor   | 94%    | 91%       | GATE_MET
   RefundService      | 87%    | 84%       | BELOW_GATE
   ```
3. For each class still BELOW_GATE, run additional generation rounds:
   - Determine remaining delta and assign strategy (TARGETED / STANDARD / FULL).
   - Generate complement tests, apply patch, re-run Step 8.5, then re-validate.
   - After each re-validation, re-run `scripts/generate-class-coverage-tracker.py <module_jacoco_xml> <project_root> --report-name coverage-tracker-<module_name>.md` to overwrite the tracker with the latest wave state.
     Confirm that the `PROJECT COVERAGE` line at the top reflects the new wave progress.
   - Repeat until the class reaches GATE_MET.
4. A class may only be marked `BLOCKED` if one of these hard blockers applies:
   - `BLOCKED â€” boundary`: public API does not expose enough behaviour.
   - `BLOCKED â€” compile`: test class fails to compile after three fix attempts.
   - `BLOCKED â€” test failure`: tests keep failing after three fix attempts.
   - `BLOCKED â€” no branches`: interface/enum with lines >= 92%.
   Any other reason is NOT a valid blocker. Keep generating.
5. Run `scripts/cleanup-generated-logs.py <module_path>`.
6. Print the final tracker from `<project_root>/docs/coverage-tracker-<module_name>.md`, then:
   ```
   SKILL COMPLETE (module: <name>): <N> GATE_MET / <N> BLOCKED â€” <reason>
   ```
   BELOW_GATE is not an acceptable final state.
7. If any class remains BELOW_GATE in the module, start a new full wave immediately and
   continue until the completion condition above is satisfied.

## Error Handling

* resolve-module.py returns NO_MODULES_FOUND: treat `<project_root>` itself as
  single module scope and continue with java-coverage-module flow.
* check-skill-readiness.py returns NOT_READY: mark run as `BLOCKED - not ready`
  and stop.
* generate-class-coverage-tracker.py fails REPORT_NOT_FOUND: run
  `scripts/run-jacoco-report.py <module_path>` and retry automatically.
* Any patch targeting a file outside <module_path>: abort and report path violation.
* validate-patch.py encoding error after two attempts: mark class as
  `BLOCKED â€” patch encoding` and continue with remaining classes.
* run-tests-and-verify.py returns COMPILE_ERROR: fix the patch for the affected
  class and re-run before proceeding. Do not validate coverage with broken tests.
* run-tests-and-verify.py returns TESTS_FAILED after three fix attempts: mark
  the class as BLOCKED â€” test failure in the tracker, document the reason,
  and report to user. This is the only condition that allows skipping a class.
* If any patch path contains `src/main/`: BOUNDARY VIOLATION â€” abort that patch
  immediately, report the path to the user, and skip the class. Never modify
  production source files under any circumstance.


