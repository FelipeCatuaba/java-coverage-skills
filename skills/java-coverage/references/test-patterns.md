# Test Patterns

Match the project. Do not pick JUnit 4 vs 5 from the Java version.

## Mirror what is already there

Before writing a new test class, open a nearby test in the same module:

- JUnit 4 (`org.junit.Test`, `@RunWith`) vs JUnit 5 (`org.junit.jupiter`, `@ExtendWith`)
- Method names (`shouldX`, `givenXWhenYThenZ`, …)
- Base class (`AbstractUnitTest`, …)
- Tags (`@Tag("unitTest")`, …)
- Mockito style (`@InjectMocks` vs constructor)

Reuse that shape. Quality still comes from
[generation-rules.md](generation-rules.md): one scenario, exact assertion,
caller-shaped data. Do not copy a weak nearby test just because it exists.

The templates below are fallbacks when `src/test/` is empty.

## Branch coverage — when it does not apply

JaCoCo reports 0% branches on types with no conditionals. Do not treat that
as `BELOW_GATE`.

Branch is **N/A** only when the file is an interface, enum, or abstract type
**and** it has no `if` / `switch` / `? :` / `&&` / `||`.

Branch **does** apply to POJOs, DTOs, and Lombok types that have any of:

- `equals` / `hashCode`
- Bean Validation (`@NotNull`, `@Size`, …)
- Lombok `@Data` / `@Value` / `@Builder` / `@EqualsAndHashCode`
- Any conditional in the source

Read the production `.java` before marking branch N/A.

## Fallback — JUnit 4

Use only when existing tests (or dependencies) are JUnit 4.

```java
@RunWith(MockitoJUnitRunner.class)
public class CustomerServiceTest {

    @Mock
    private CustomerRepository repository;

    @InjectMocks
    private CustomerService subject;

    @Test
    public void shouldReturnOnlyActiveCustomers() {
        List<Customer> all = Arrays.asList(
            new Customer(1L, "Alice", "alice@example.com", true),
            new Customer(2L, "Bob", "bob@example.com", false)
        );
        when(repository.findAll()).thenReturn(all);

        List<Customer> result = subject.findActive();

        assertEquals(1, result.size());
        assertEquals("Alice", result.get(0).getName());
    }
}
```

- Assertions: `org.junit.Assert`
- Exceptions: `@Test(expected = …)` (no `assertThrows`)

## Fallback — JUnit 5

Default when the project has `junit-jupiter` or `spring-boot-starter-test`
and no JUnit 4 tests.

```java
@ExtendWith(MockitoExtension.class)
class CustomerServiceTest {

    @Mock
    private CustomerRepository repository;

    @InjectMocks
    private CustomerService subject;

    @Test
    void shouldReturnOnlyActiveCustomers() {
        List<Customer> all = List.of(
            new Customer(1L, "Alice", "alice@example.com", true),
            new Customer(2L, "Bob", "bob@example.com", false)
        );
        when(repository.findAll()).thenReturn(all);

        List<Customer> result = subject.findActive();

        assertEquals(1, result.size());
        assertEquals("Alice", result.get(0).getName());
    }

    @Test
    void shouldThrowWhenCustomerIdIsNull() {
        IllegalArgumentException ex = assertThrows(
            IllegalArgumentException.class,
            () -> subject.findById(null)
        );
        assertEquals("Invalid id: null", ex.getMessage());
    }
}
```

- Assertions: `org.junit.jupiter.api.Assertions`
- Prefer `@ParameterizedTest` when several inputs hit the **same rule** with
  the same assertion (not a dump of leftover branches)
- If the module already uses a base class or `@Tag`, copy that — do not invent a new one

## Quality — good vs reject

```java
// GOOD — one rule, exact value
@Test
void givenIsoDateWhenParseThenLocalDate() {
    assertEquals(LocalDate.of(2026, 7, 23), DateParser.parse("2026-07-23"));
}

// GOOD — exception type + message
@Test
void givenBlankIdWhenFindThenThrows() {
    IllegalArgumentException ex = assertThrows(
        IllegalArgumentException.class,
        () -> subject.findById("  ")
    );
    assertEquals("id cannot be blank", ex.getMessage());
}

// REJECT — packed leftover branches
@Test
void givenVariousWhenParseThenCoversGaps() {
    assertTrue(DateParser.parse(null).isEmpty());
    assertTrue(DateParser.parse("32/13/2026").isEmpty());
    assertEquals(Optional.of(LocalDate.of(2026, 7, 23)), DateParser.parse("23/07/2026"));
}

// REJECT — weak assert
assertTrue(customer.document().length() >= 11);
assertFalse(result.attributes().isEmpty());
assertThrows(IllegalArgumentException.class, () -> subject.findById(input));
```
