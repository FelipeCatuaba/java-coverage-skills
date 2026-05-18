---
name: java-coverage-file
description: Generates JUnit tests for a single specified Java class until reaching 92%
  line coverage and 90% branch coverage. Detects Java version, validates pom.xml
  dependencies, and delivers the test file
  as a BOM-free UTF-8 patch. Use when a specific .java file path is provided and the goal
  is to improve coverage for that class only. Don't use for full project runs, module-wide
  generation, or git diff scoped generation.
---

# Java Coverage â€” Single File

## Entry Point â€” Autonomous Execution

This skill is triggered by phrases like:
- "rode a skill para o arquivo <ClassName>.java"
- "gere cobertura para a classe <ClassName>"
- "run file coverage for <ClassName>"

When triggered, execute ALL steps in sequence from Step 1 to Step 7 WITHOUT stopping
to ask for confirmation between steps. This flow must run with no user interaction:

- If blockers happen, continue autonomously where possible.
- Report unresolved blockers only in final summary.

In all other cases: proceed autonomously and print the checkpoint output for each step.

Hard rule: this skill must execute the complete cycle (coverage analysis, test generation,
test execution, coverage re-analysis) and MUST NOT stop after only diagnostic output.
Partial runs are not valid completion.

After completing Step 7, print a one-line summary:
```
SKILL COMPLETE (<ClassName>): GATE_MET | BLOCKED â€” <reason> | BOUNDARY_VIOLATION
```
Completion is valid only when target class is `GATE_MET` or `BLOCKED` with valid reason.

---

## Procedures

**Progress Policy (In-Memory for File Scope)**

1. For file scope, do not persist coverage tracker files in `docs/`.
2. Keep progress in memory during the run and print each wave result to stdout.
3. A "wave" is: (a) coverage analysis, (b) test generation, (c) coverage re-analysis.

**Step 1: Resolve Target Class**

1. Resolve target file path:
   - If user provided path, use it.
   - If path omitted, auto-detect best candidate from current context/workspace.
   - If no safe candidate found, mark run as `BLOCKED â€” target not resolved` and stop.
2. Run `scripts/check-skill-readiness.py <project_root>` to detect Java version and profile.
3. Print before proceeding:
   ```
   TARGET: OrderService.java
   SKILL READY: java=<8|11|17+> build=maven
   ```
4. Read `references/java-version-patterns.md` and keep active for all steps.

**Step 2: Validate pom.xml Dependencies**

1. Run `scripts/check-pom-deps.py <pom_path> <java_version>`.
2. If `MISSING: <dep>`: read `references/pom-dependency-blocks.md`, apply as patch,
   re-run until `DEPS OK`.
3. Print: `DEPS STATUS: OK â€” junit=<version> mockito=<version> jacoco=<version>`

**Step 3: Snapshot Coverage â€” Target Class Only**

1. Run `scripts/generate-class-coverage-tracker.py <jacoco_xml_path> <project_root> --class <ClassName>`.
   For file scope, this output is used only in-memory/console for the current run.
   Original line continued:
   --class <ClassName>` to extract coverage for this class only.
2. Print:
   ```
   CLASS         | LINES% | BRANCHES% | LINE_DELTA | BRANCH_DELTA | STATUS
   OrderService  | 55%    | 48%       | +37%       | +42%         | BELOW_GATE
   ```
3. If STATUS is GATE_MET (LINES >= 92% AND BRANCHES >= 90%): inform the user and stop.
   No generation needed.

**Step 4: Audit Existing Test Class**

1. Run `scripts/find-test-classes.py <project_root> OrderService`.
2. If more than one test file found:
   - Consolidate all methods into OrderServiceTest.java via patch.
   - Remove non-canonical files via patch.
   - If more than 3 files found: auto-consolidate in batches and continue.
3. If one non-canonical file (e.g. OrderService_ESTest): rename via patch.
4. Print: AUDIT DONE â€” canonical file: <path>/OrderServiceTest.java

**Step 5: Plan and Generate Tests**

1. Assign strategy based on line delta:
   Line Delta <= 15%  -> TARGETED  : uncovered branches only, read existing file first
   Line Delta 16-40%  -> STANDARD  : all public methods + main conditional branches
   Line Delta > 40%   -> FULL      : all public methods, branches, edge cases, mocks

2. Print plan before generating:
   ```
   GENERATION PLAN: OrderService -> FULL (lines +37%, branches +42%)
   ```
3. Generate tests per strategy and references/java-version-patterns.md.
4. Read `references/generation-rules.md` before writing any test method.
   This file is MANDATORY â€” it defines forbidden patterns and quality requirements.
5. Rules:
   - SCOPE: only write to `src/test/` â€” never touch any file under `src/main/`.
     If a patch path contains `src/main/`, abort it and report BOUNDARY VIOLATION.
   - SONAR: never add classes to `sonar.exclusions` or JaCoCo `<exclude>` rules.
   - QUALITY: no empty tests, no trivial assertNotNull-only tests, no catch-and-ignore.
   - PUBLIC API: test via public methods simulating real application flow â€” no reflection,
     no Whitebox, no ReflectionTestUtils.
   - One test class only â€” never create OrderServiceTest2 or variants.
   - Coverage decides generation, not file existence: if a test file already
     exists but the class is BELOW_GATE, read the existing file first, identify
     which branches and methods are NOT yet covered, and add tests for those gaps.
     Never assume coverage is sufficient because a test file exists.
   - Add methods to the existing file; never create a new file.
   - File name must be exactly <ClassName>Test.java.
5. Deliver as patch following Step 6.

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
3. Do NOT run `scripts/check-coverage-gate.py` (Step 7) until this step
   exits with `TESTS_OK` or `NO_TESTS_FOUND`.
4. Maximum two fix-and-retry rounds per failing class. If a class still fails
   after two rounds: mark it `NEEDS_REVIEW â€” test failure` in the tracker,
   skip it in Step 7, and continue autonomously.

**Step 7: Validate Coverage â€” Gate is Mandatory**

Gate: LINES >= 92% AND BRANCHES >= 90%. The skill does NOT finish until the
class reaches the gate or is explicitly blocked.

1. Run `scripts/check-coverage-gate.py <project_root> <jacoco_xml_path> --class <ClassName>`.
2. Print result:
   ```
   CLASS         | LINES% | BRANCHES% | STATUS
   OrderService  | 94%    | 91%       | GATE_MET
   ```
3. If BELOW_GATE: determine remaining delta, assign strategy, generate complement
   tests, apply patch, re-run Step 6.5, then re-validate. Repeat until GATE_MET.
   After each re-validation, re-run `scripts/generate-class-coverage-tracker.py <jacoco_xml_path> <project_root> --class <ClassName>` to refresh in-memory progress for the latest wave state.
4. A class may only be marked `BLOCKED` if one of these hard blockers applies:
   - `BLOCKED â€” boundary`: public API insufficient, cannot touch src/main/.
   - `BLOCKED â€” compile`: fails to compile after three fix attempts.
   - `BLOCKED â€” test failure`: tests keep failing after three fix attempts.
   - `BLOCKED â€” no branches`: interface/enum with lines >= 92%.
5. Print final summary:
   ```
   SKILL COMPLETE (<ClassName>): GATE_MET | BLOCKED â€” <reason>
   ```
   BELOW_GATE is not an acceptable final state.
6. If target class remains BELOW_GATE, start a new full wave immediately and continue
   until the completion condition above is satisfied.

## Error Handling

* No file path provided by user: auto-detect from context/workspace; if unresolved,
  mark run as `BLOCKED â€” target not resolved`.
* generate-class-coverage-tracker.py returns CLASS_NOT_FOUND: JaCoCo report may be
  outdated. Run `scripts/run-jacoco-report.py <project_root>` and retry automatically.
* Target class already at GATE_MET: finish autonomously with completion summary. No generation needed.
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


