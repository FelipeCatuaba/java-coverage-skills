# Java Version Test Patterns

## Class Type Exclusions — Branch Coverage

JaCoCo reports 0% branch coverage for class types that have no conditional logic.
These classes must NOT be flagged as NEEDS_REVIEW solely due to branch coverage.

Apply this rule in Step 3 (tracker snapshot) and Step 9 (gate validation):
if `BRANCHES% = 0` AND the class matches any pattern below, treat branch coverage
as NOT APPLICABLE and evaluate gate using line coverage only.

| Class Type | Detection Pattern | Branch Rule |
|---|---|---|
| Interface | only method signatures, no method bodies | BRANCH = N/A |
| Enum without logic | `enum` keyword, no `if`/`switch` inside methods | BRANCH = N/A |
| Abstract class (no logic) | only abstract methods, no concrete bodies with branches | BRANCH = N/A |

**POJOs, DTOs, and Lombok classes: always require branch coverage.**
Even classes that appear simple must be covered if they contain ANY of:
- `equals()` / `hashCode()` — has implicit branches
- `@NotNull`, `@Size`, `@Pattern` or other Bean Validation annotations — validators branch
- `@Builder`, `@Data`, `@Value` (Lombok) — generated code has branches JaCoCo tracks
- Custom constructors with validation logic
- `if` / `switch` / `? :` / `&&` / `||` anywhere in the file

**Detection heuristic for the agent:**
Read the production `.java` file before assigning BRANCH = N/A.
Only skip branch coverage when the file is an interface or an enum/abstract class
with zero conditional operators. For everything else — including POJOs and DTOs —
branch coverage applies and must reach the 90% gate.

---


## Java 8

### Dependencies
- JUnit: `junit:junit:4.13.2` (scope test)
- Mockito: `org.mockito:mockito-core:3.x` (scope test)
- Runner: no @ExtendWith — use `@RunWith(MockitoJUnitRunner.class)`

### Class Template
```java
import org.junit.Test;
import org.junit.Before;
import org.junit.runner.RunWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.MockitoJUnitRunner;
import static org.junit.Assert.*;
import static org.mockito.Mockito.*;

@RunWith(MockitoJUnitRunner.class)
public class <ClassName>Test {

    @Mock
    private <Dependency> dependency;

    @InjectMocks
    private <ClassName> subject;

    @Before
    public void setUp() { }

    @Test
    public void should<Behavior>() {
        // arrange
        // act
        // assert
    }
}
```

### Rules
- Use `Assert.assertEquals`, `Assert.assertTrue`, `Assert.assertNull` (not assertThat).
- Exception testing: `@Test(expected = SomeException.class)`.
- No `assertThrows` — not available in JUnit 4.
- Static methods: use `PowerMockito` only if already on classpath; otherwise refactor.

---

## Java 11

### Dependencies
- JUnit: `org.junit.jupiter:junit-jupiter:5.9.x` (scope test)
- Mockito: `org.mockito:mockito-core:4.x` (scope test)
- Runner: `@ExtendWith(MockitoExtension.class)`

### Class Template
```java
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class <ClassName>Test {

    @Mock
    private <Dependency> dependency;

    @InjectMocks
    private <ClassName> subject;

    @BeforeEach
    void setUp() { }

    @Test
    void should<Behavior>() {
        // arrange
        // act
        // assert
    }
}
```

### Rules
- Use `assertEquals`, `assertTrue`, `assertThrows` from `org.junit.jupiter.api.Assertions`.
- Exception testing: `assertThrows(SomeException.class, () -> subject.method())`.
- Class visibility: package-private (no `public` on class).

---

## Java 17+

### Dependencies
- JUnit: `org.junit.jupiter:junit-jupiter:5.10.x` (scope test)
- Mockito: `org.mockito:mockito-core:5.x` (scope test)
- Runner: `@ExtendWith(MockitoExtension.class)`

### Class Template
```java
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.extension.ExtendWith;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class <ClassName>Test {

    @Mock
    private <Dependency> dependency;

    @InjectMocks
    private <ClassName> subject;

    @BeforeEach
    void setUp() { }

    @Test
    void should<Behavior>() {
        // arrange
        // act
        // assert
    }

    @ParameterizedTest
    @ValueSource(strings = { "input1", "input2" })
    void should<Behavior>WithParam(String input) {
        // use for branch coverage with multiple inputs
    }
}
```

### Rules
- Prefer `@ParameterizedTest` for branch coverage over duplicating test methods.
- Use records and sealed classes in arrange blocks when testing domain objects.
- Class visibility: package-private.
- Mockito 5.x: no need for `openMocks` — `@ExtendWith` handles lifecycle.
