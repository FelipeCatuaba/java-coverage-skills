# Test Generation Rules

Apply to every test this skill creates or edits.

Coverage is the **selector**, not the **standard**. A missed branch earns a
test only when you can name the observable contract it implements. If you
cannot, do not write the test — mark `BLOCKED — no contract`.

## 1. Never touch `src/main/`

Forbidden:

- Creating or editing anything under `src/main/`
- Refactoring production code to make it easier to test
- Adding `@VisibleForTesting`, changing access modifiers, or adding annotations
  on production classes

Hard-to-test private logic is reached only through the public API. If that is
not enough, mark the class `BLOCKED — boundary`.

Before writing a file, check the path. If it contains `src/main/`: abort,
report `BOUNDARY VIOLATION: <path>`, skip the class.

## 2. Never hide coverage

Do not add `sonar.exclusions`, `@SuppressWarnings("squid:...")` on production
types, or new JaCoCo `<exclude>` / Gradle `excludes` to inflate the number.

Existing exclusions stay as they are.

## 3. Contract first

Before writing a method, complete this sentence in your head:

> Given `<realistic input a caller can send>`, when `<public method>`,
> then `<exact value, state, exception message, or mock interaction>`.

If the sentence needs “to hit branch X” or “so JaCoCo paints green”, stop.
That gap is `BLOCKED — no contract`.

Prefer gaps that a production caller already exercises (public API input,
shipped fixture, documented error). Skip, in this order:

1. `Objects.requireNonNull` / record or constructor null-guards with no caller path
2. Private helpers that only coerce `null`/missing config keys to a default
3. Synthetic test resources invented only to omit keys the shipped file already has
4. Dead code after a throw, or a standard-library path that always succeeds
   (for example `MessageDigest.getInstance("SHA-256")`)

Leaving those untested and finishing `STILL_BELOW` is correct.

## 4. No empty, trivial, or packed tests

Forbidden:

```java
// FORBIDDEN — constructor only
void shouldCreateInstance() {
    assertNotNull(new CustomerService(repo));
}

// FORBIDDEN — empty
void shouldProcessOrder() { }

// FORBIDDEN — tautology
void shouldReturnSomething() {
    assertTrue(service.doSomething() != null);
}

// FORBIDDEN — swallow
void shouldHandleError() {
    try { service.riskyMethod(); } catch (Exception ignored) { }
}

// FORBIDDEN — packed scenarios (two acts, two rules)
void givenInvalidWhenCreateThenTruncatesAndUsesDefaultType() {
    assertEquals(500, service.create(..., "x".repeat(600)).reason().length());
    assertEquals("STANDARD", service.create(..., "").type());
}

// FORBIDDEN — coverage tourism
assertThrows(NullPointerException.class, () -> useCase.execute(null));
assertThrows(NullPointerException.class, () -> new Input(null));
```

A valid test has **one** arrange, **one** act, and assertions on **that** act.

`@ParameterizedTest` is allowed only when every case checks the **same** rule
with the **same** assertion shape (e.g. several invalid dates → empty
optional). Different rules stay in different methods.

## 5. Specific assertions

Forbidden substitutes for a contract:

- `assertNotNull`, `assertTrue(x != null)`
- `assertFalse(map.isEmpty())` / `assertTrue(list.size() > 0)`
- `assertTrue(value.length() >= n)`
- `assertTrue(text.contains(exception.getClass().getSimpleName()))`
- `assertThrows(SomeException.class, …)` with no message (or project equivalent)

Required:

- Exact return or field the rule names (`assertEquals("2026-07-23", date)`)
- Exception **type and message** (`assertEquals("id cannot be blank", ex.getMessage())`)
- The map/list **key or element** the rule cares about, not “not empty”
- Mock: `verify` the interaction the rule requires (`never().save(…)`, `save` with a named status)

## 6. Production-like inputs

Call public methods the way the application does. Reuse fixtures and sample
data the project already ships.

Forbidden:

- A YAML/JSON/XML under `src/test/resources` whose only job is to omit keys
  so private parsers take the `null` branch
- Hand-built objects that skip the mapper/validator the use case would run,
  unless that class **is** the unit under test
- `null` arguments that no caller can pass, just to cover `requireNonNull`

Mock collaborators to isolate the unit. Do not mock away the logic under test.

No reflection, `Whitebox`, or `ReflectionTestUtils`.

## 7. Coverage decides file existence, not quality

If the class is `BELOW_GATE`, add tests to `<ClassName>Test.java` even when
the file already exists. Read it first. Add only **missing contracts**.

Do not add a method whose only justification is “this line is red”.

When several classes are `BELOW_GATE`, spend the wave on public services and
the types this repo already tests as behavior — not on DTO constructors or
private config defaults.

## 8. One test class

Canonical name: `<ClassName>Test.java`. Add methods there. Never create
`Test2`, `CoverageTest`, or `Tests` variants.

If several aliases already exist, keep writing into `<ClassName>Test.java`.
Do not spend a wave consolidating unless the user asks.

## 9. Checklist before saving a test file

- [ ] You can name the contract without mentioning JaCoCo or a branch index
- [ ] One scenario per method (or a parameterized **same-rule** table)
- [ ] Arrange uses caller-shaped, realistic data
- [ ] Assertion is exact (value, field, exception message, or named mock call)
- [ ] If this production rule changed, the test would fail for that reason
- [ ] Path is under `src/test/`
- [ ] No new Sonar/JaCoCo exclusions
- [ ] No reflection
- [ ] No fixture invented only to miss production keys

If any box fails: rewrite, split, or delete the method. Do not keep it to
protect the coverage number.
