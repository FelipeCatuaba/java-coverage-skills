# Changelog

## 2.1.0

Harden the test bar. Coverage selects which class to touch; a missed branch
earns a test only when it has an observable contract.

- One scenario per method (parameterized only for the same rule).
- Assert exact values, exception messages, or named mock calls — not
  `isEmpty()`, `length() >= n`, or `assertThrows` without a message.
- No `requireNonNull` tourism, no fixtures invented to miss production keys.
- New stop reason: `BLOCKED — no contract`. `STILL_BELOW` beats a sausage test.

## 2.0.0

Breaking: one skill (`java-coverage`) replaces `java-coverage-full`,
`java-coverage-module`, `java-coverage-file`, and `java-coverage-diff`.

- Playbook only — all Python scripts removed.
- Maven and Gradle. Detect build from repo files; run the project wrapper.
- No OS-specific commands.
- Do not auto-edit the build. Stop and show snippets if JaCoCo/JUnit is missing.
- Write tests directly under `src/test/`. No unified-diff ritual, no tracker in `docs/`.
- At most 3 waves. Remaining gaps finish as `STILL_BELOW`.

## 1.0.2

Last Maven-only pack with four copied skills and scripts.
