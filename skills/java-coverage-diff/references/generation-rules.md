# Test Generation Rules

These rules apply to EVERY test generated or modified by this skill.
Read this file at the start of every generation step and enforce all rules without exception.

---

## 1. Scope Boundary — Never Touch src/main/

This skill operates exclusively on `src/test/`. The following are STRICTLY FORBIDDEN:

- Modifying any file under `src/main/`
- Creating any file under `src/main/`
- Refactoring, renaming, or reformatting production classes to make them easier to test
- Adding, removing, or modifying annotations on production classes (e.g. `@VisibleForTesting`)
- Changing access modifiers on production methods (e.g. `private` → `package-private`)

If a class is difficult to test due to its structure (private methods, static calls,
no-interface dependencies), generate tests using the public API only.
Do NOT modify the production class. Report the limitation in the tracker as a note.

**Self-check before applying any patch:**
Read the `---` and `+++` headers. If any path contains `src/main/`: ABORT that patch,
report `BOUNDARY VIOLATION: <path>` and skip that class.

---

## 2. Sonar Exclusions — Never Add

Adding classes or packages to Sonar exclusions to artificially inflate coverage metrics
is FORBIDDEN. This includes:

- `sonar.exclusions` in `pom.xml`, `sonar-project.properties`, or any config file
- `@SuppressWarnings("squid:...")` added to production classes for coverage reasons
- JaCoCo `<exclude>` rules added to `pom.xml` to hide classes from the report

If a class is legitimately excluded (e.g. generated code, framework config), it should
already be excluded before this skill runs. Do NOT add new exclusions during a skill run.

---

## 3. Test Quality — No Empty or Trivial Tests

The following test patterns are FORBIDDEN and must never be generated:

**Trivial instantiation test:**
```java
// FORBIDDEN
@Test
void shouldCreateInstance() {
    CustomerService service = new CustomerService(repo);
    assertNotNull(service);
}
```

**Empty test body:**
```java
// FORBIDDEN
@Test
void shouldProcessOrder() {
    // TODO
}
```

**Assert-true with no real verification:**
```java
// FORBIDDEN
@Test
void shouldReturnSomething() {
    Object result = service.doSomething();
    assertTrue(result != null);
}
```

**Catch-and-ignore exception:**
```java
// FORBIDDEN
@Test
void shouldHandleError() {
    try {
        service.riskyMethod();
    } catch (Exception e) {
        // ignored
    }
}
```

A valid test must have ALL of the following:
- A meaningful `// arrange` block that sets up realistic input state
- A `// act` call that invokes the method under test
- At least one assertion that verifies a **specific observable outcome**
  (return value, state change, exception type + message, or mock interaction)

---

## 4. Test Through Public API — Simulate Real Application Flow

Tests must exercise the class through its **public methods**, simulating how
the application actually uses it. Specifically:

- Call public methods with realistic input values — not nulls or empty strings
  unless the test is explicitly covering null/empty input handling
- Use mock dependencies to simulate the surrounding system, not to bypass logic
- If a method has multiple branches, write separate test methods per scenario —
  one for the happy path, one per edge case, one per exception path
- Do NOT use reflection to access private methods or fields
- Do NOT use `Whitebox`, `ReflectionTestUtils`, or similar utilities to bypass
  encapsulation — if private logic needs testing, it must be reached via
  a public method that exercises it

**Example of a good test (Java 8 style):**
```java
@Test
public void shouldThrowWhenCustomerIdIsNull() {
    // arrange — realistic: id null simulates missing request param
    Long id = null;

    // act + assert
    try {
        customerService.findById(id);
        fail("Expected IllegalArgumentException");
    } catch (IllegalArgumentException e) {
        assertEquals("Invalid id: null", e.getMessage());
    }
}

@Test
public void shouldReturnOnlyActiveCustomers() {
    // arrange — realistic: mixed list as the repository would return
    List<Customer> all = Arrays.asList(
        new Customer(1L, "Alice", "alice@example.com", true),
        new Customer(2L, "Bob",   "bob@example.com",   false)
    );
    when(repository.findAll()).thenReturn(all);

    // act
    List<Customer> result = customerService.findActive();

    // assert — verifies specific business outcome
    assertEquals(1, result.size());
    assertEquals("Alice", result.get(0).getName());
}
```

---

## 5. Coverage Decides Generation — Not File Existence

The presence of a test file does NOT mean the class is sufficiently covered.
Before generating any test for a class:

1. Check the tracker — if STATUS is BELOW_GATE, generation is required regardless
   of whether a test file already exists.
2. Read the existing test file (if any) to understand what is already covered.
3. Cross-reference with the JaCoCo report to identify the specific uncovered
   branches and methods.
4. Generate ONLY tests that cover the identified gaps — do not duplicate existing
   test scenarios.

**This rule applies to every generation round, including complement rounds.**
Never skip a BELOW_GATE class because it already has a test file.

---

## 6. One Test Class Per Production Class

- The canonical test file is always `<ClassName>Test.java`
- Never create `<ClassName>Test2`, `<ClassName>CoverageTest`, `<ClassName>Tests`,
  or any other variant
- If the canonical file already exists, add new test methods to it — never create
  a second file for the same class
- If multiple non-canonical files exist, consolidate them first (Step 4) before
  adding any new tests

---

## 7. Self-Validation Checklist Before Submitting Any Test

Before delivering a test patch, verify each generated test method:

- [ ] Has a `// arrange`, `// act`, `// assert` structure (or equivalent)
- [ ] Uses realistic input values that reflect actual application scenarios
- [ ] Has at least one specific assertion (not just `assertNotNull`)
- [ ] Does not access `src/main/` files
- [ ] Does not add Sonar exclusions
- [ ] Does not use reflection or whitebox utilities
- [ ] Covers one scenario per test method (not multiple unrelated assertions)
- [ ] If testing an exception: verifies both the exception type AND message

If any item fails: fix the test before delivering the patch.
