---
name: java-coverage-diff
description: Generates JUnit tests only for uncommitted Java changes (staged/unstaged/untracked),
  and validates gate only on the diff lines that were newly developed. Detects
  Java version, validates pom.xml dependencies, and delivers tests as BOM-free UTF-8
  patches. Use when a developer wants to cover only what is not committed yet.
  Don't use for full project runs, module-wide generation, single file targeting, or
  class consolidation.
---

# Java Coverage â€” Git Diff

## Entry Point â€” Autonomous Execution

This skill is triggered by phrases like:
- "rode a skill de diff"
- "gere cobertura do que eu desenvolvi"
- "run diff coverage flow"
- "cover only my changes"

When triggered, execute ALL steps in sequence from Step 1 to Step 7 WITHOUT stopping
to ask for confirmation between steps. This flow must run with no user interaction:

- If blockers happen, continue autonomously where possible.
- Report unresolved blockers only in final summary.

In all other cases: proceed autonomously and print the checkpoint output for each step.

Hard rule: this skill must execute the complete cycle (diff-line coverage analysis,
test generation, test execution, diff-line coverage re-analysis) and MUST NOT stop
after only diagnostic output. Partial runs are not valid completion.

After completing Step 7, print the final in-memory progress view and a one-line summary:
```
SKILL COMPLETE (diff): <N> GATE_MET / <N> BLOCKED â€” <reason>
```
Completion is valid only when there are zero `BELOW_GATE` classes in diff scope.

---

## Procedures

**Progress Policy (In-Memory for Diff Scope)**

1. For diff scope, do not persist coverage tracker files in `docs/`.
2. Keep progress in memory during the run and print each wave result to stdout.
3. A "wave" is: (a) diff-line coverage analysis, (b) test generation, (c) diff-line coverage re-analysis.

**Step 1: Resolve Changed Classes**

1. Run `scripts/resolve-git-diff.py <project_root>` to list all uncommitted
   `.java` production files (staged + unstaged + untracked).
2. Print the resolved list before proceeding:
   ```
   CHANGED CLASSES (uncommitted diff):
   src/main/java/com/example/OrderService.java
   src/main/java/com/example/PaymentValidator.java
   ```
3. If no .java files found in diff: mark run as `BLOCKED â€” no diff scope` and stop.
   Do not process test files â€” filter out any path under src/test/.
4. Run `scripts/check-skill-readiness.py <project_root>`.
5. Print:
   ```
   SKILL READY: java=<8|11|17+> build=maven
   ```
6. Read `references/java-version-patterns.md` and keep active for all steps.

**Step 2: Validate pom.xml Dependencies**

1. Run `scripts/check-pom-deps.py <pom_path> <java_version>`.
2. If `MISSING: <dep>`: read `references/pom-dependency-blocks.md`, apply as patch,
   re-run until `DEPS OK`.
3. Print: `DEPS STATUS: OK â€” junit=<version> mockito=<version> jacoco=<version>`

**Step 3: Snapshot Coverage â€” Diff Lines Only**

1. Run `scripts/check-diff-line-gate.py <project_root> <jacoco_xml_path>`.
2. Print the in-memory progress view for changed classes considering only diff lines.
   ```
   CLASS             | DIFF_LINES | LINES% | BRANCHES% | STATUS
   OrderService      |         12 | 83%    | 75%       | BELOW_GATE
   PaymentValidator  |          5 | 100%   | N/A       | GATE_MET
   ```
3. Gate is evaluated only on changed diff lines:
   - `LINES >= 92%`
   - `BRANCHES >= 90%` only when diff lines have branch opportunities
   - if no branches exist in changed lines, evaluate gate by lines only
4. Never classify a class as BELOW_GATE because of untouched lines outside the diff.
5. Do not proceed until tracker is printed.

**Step 4: Plan Generation Batch**

1. For each BELOW_GATE class, assign strategy based on diff-line coverage delta:

   Line Delta <= 15%  -> TARGETED  : uncovered branches only, read existing file first
   Line Delta 16-40%  -> STANDARD  : all public methods + main conditional branches
   Line Delta > 40%   -> FULL      : all public methods, branches, edge cases, mocks

2. Print complete plan before generating:
   ```
   GENERATION PLAN (diff scope):
   OrderService      -> STANDARD (diff lines below gate)
   ```
3. Do not generate any test until the plan is printed.

**Step 5: Generate Tests**

1. Generate tests per strategy and references/java-version-patterns.md.
2. Read `references/generation-rules.md` before writing any test method.
   This file is MANDATORY â€” it defines forbidden patterns and quality requirements.
3. Rules:
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
   - Do not modify any class not listed in the diff.
3. Deliver each file as a patch following Step 6.
4. Update tracker: GENERATED â€” est_lines=<X>% est_branches=<X>%.

**Step 6: Patch Encoding Rules**

Every file created or modified must be a patch. Never write raw file content.

1. Use unified diff format:
   --- a/src/test/java/com/example/OrderServiceTest.java
   +++ b/src/test/java/com/example/OrderServiceTest.java
2. Run scripts/validate-patch.py <patch_file> before presenting.
3. If BOM_DETECTED or CRLF_DETECTED: fix and re-validate.
   After two failed attempts: mark class as `BLOCKED â€” patch encoding` and continue.
4. Mandatory for every patch:
   - No BOM (0xEF 0xBB 0xBF forbidden).
   - LF only (\n â€” no \r\n).
   - UTF-8 without BOM.

**Step 6.5: Compile and Verify Tests**

1. Run `scripts/run-tests-and-verify.py <project_root>` after all patches from
   Step 6 are applied.
2. Evaluate the output:
   - `EXIT STATUS: TESTS_OK`: all tests compile and pass â€” proceed to Step 7.
   - `COMPILE_ERROR`: one or more test classes failed to compile.
     Fix the affected patch(es) and re-apply before re-running this step.
   - `EXIT STATUS: TESTS_FAILED`: tests compiled but assertions are failing.
     Read the failure details printed per class and fix the test logic before
     re-running this step.
   - `NO_TESTS_FOUND`: no test classes exist yet for this scope â€” this is
     expected on the first run before any patches are applied. Proceed to Step 7.
3. Do NOT run `scripts/check-diff-line-gate.py` (Step 7) until this step
   exits with `TESTS_OK` or `NO_TESTS_FOUND`.
4. Maximum two fix-and-retry rounds per failing class. If a class still fails
   after two rounds: mark it `NEEDS_REVIEW â€” test failure` in the tracker,
   skip it in Step 7, and continue autonomously.

**Step 7: Validate Coverage â€” Gate is Mandatory**

Gate applies only to changed diff lines:
- LINES >= 92%
- BRANCHES >= 90% only for diff lines that contain branches
The skill does NOT
finish until every changed class reaches the gate or is explicitly blocked.

1. Run `scripts/check-diff-line-gate.py <project_root> <jacoco_xml_path>`.
2. Update tracker and print:
   ```
   CLASS             | DIFF_LINES | LINES% | BRANCHES% | STATUS
   OrderService      |         11 | 100%   | 100%      | GATE_MET
   PaymentValidator  |          4 | 75%    | N/A       | BELOW_GATE
   ```
3. For each class still BELOW_GATE: determine remaining delta, assign strategy,
   generate complement tests, apply patch, re-run Step 6.5, then re-validate.
   After each re-validation, re-run `scripts/check-diff-line-gate.py <project_root> <jacoco_xml_path>` to refresh in-memory progress for the latest wave state.
   Repeat until GATE_MET.
4. A class may only be marked `BLOCKED` if one of these hard blockers applies:
   - `BLOCKED â€” boundary`: public API insufficient, cannot touch src/main/.
   - `BLOCKED â€” compile`: fails to compile after three fix attempts.
   - `BLOCKED â€” test failure`: tests keep failing after three fix attempts.
   - `BLOCKED â€” no branches`: interface/enum with lines >= 92%.
5. Print final tracker and summary:
   ```
   SKILL COMPLETE (diff): <N> GATE_MET / <N> BLOCKED â€” <reason>
   ```
   BELOW_GATE is not an acceptable final state.
6. If any changed class remains BELOW_GATE, start a new full wave immediately and
   continue until the completion condition above is satisfied.

## Error Handling

* resolve-git-diff.py returns NO_JAVA_FILES: mark run as `BLOCKED â€” no diff scope`.
* resolve-git-diff.py returns NOT_A_GIT_REPO: mark run as `BLOCKED â€” not a git repo`.
* check-diff-line-gate.py returns REPORT_NOT_FOUND: run
  `scripts/run-jacoco-report.py <project_root>` and retry automatically.
* Any generated patch targeting a file not in the diff list: abort that patch and
  report the path violation before continuing with the next class.
* validate-patch.py encoding error after two attempts: mark class as
  `BLOCKED â€” patch encoding` and continue.
* run-tests-and-verify.py returns COMPILE_ERROR: fix the patch for the affected
  class and re-run before proceeding. Do not validate coverage with broken tests.
* run-tests-and-verify.py returns TESTS_FAILED after three fix attempts: mark
  the class as BLOCKED â€” test failure in the tracker, document the reason,
  and report to user. This is the only condition that allows skipping a class.
* If any patch path contains `src/main/`: BOUNDARY VIOLATION â€” abort that patch
  immediately, report the path to the user, and skip the class. Never modify
  production source files under any circumstance.


