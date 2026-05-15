# POM Dependency Blocks

Use these blocks to add missing dependencies. Always apply as a patch.
Add dependencies inside <dependencies> and plugins inside <build><plugins>.

---

## JUnit 4 (Java 8)

```xml
<dependency>
    <groupId>junit</groupId>
    <artifactId>junit</artifactId>
    <version>4.13.2</version>
    <scope>test</scope>
</dependency>
```

## JUnit 5 (Java 11 / 17+)

```xml
<dependency>
    <groupId>org.junit.jupiter</groupId>
    <artifactId>junit-jupiter</artifactId>
    <version>5.10.2</version>
    <scope>test</scope>
</dependency>
```

## Mockito (Java 8)

```xml
<dependency>
    <groupId>org.mockito</groupId>
    <artifactId>mockito-core</artifactId>
    <version>3.12.4</version>
    <scope>test</scope>
</dependency>
```

## Mockito (Java 11)

```xml
<dependency>
    <groupId>org.mockito</groupId>
    <artifactId>mockito-core</artifactId>
    <version>4.11.0</version>
    <scope>test</scope>
</dependency>
```

## Mockito (Java 17+)

```xml
<dependency>
    <groupId>org.mockito</groupId>
    <artifactId>mockito-core</artifactId>
    <version>5.11.0</version>
    <scope>test</scope>
</dependency>
```

## JaCoCo Maven Plugin

```xml
<plugin>
    <groupId>org.jacoco</groupId>
    <artifactId>jacoco-maven-plugin</artifactId>
    <version>0.8.12</version>
    <executions>
        <execution>
            <goals>
                <goal>prepare-agent</goal>
            </goals>
        </execution>
        <execution>
            <id>report</id>
            <phase>test</phase>
            <goals>
                <goal>report</goal>
            </goals>
        </execution>
    </executions>
</plugin>
```

## Mockito JUnit Jupiter (needed for Java 11/17+ with @ExtendWith)

```xml
<dependency>
    <groupId>org.mockito</groupId>
    <artifactId>mockito-junit-jupiter</artifactId>
    <version>5.11.0</version>
    <scope>test</scope>
</dependency>
```

---

## Error Section

### UNSUPPORTED_STRUCTURE
If `check-pom-deps.py` returns `UNSUPPORTED_STRUCTURE`, the pom.xml may be:
- A BOM (Bill of Materials) pom with no dependencies section
- Using a parent pom that manages all versions (version tags absent by design)
- Malformed XML

In these cases: report to the user with the exact pom path and do not attempt
to add dependencies automatically. Ask which pom manages test dependencies.
