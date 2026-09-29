# Build Tooling

Show this file only when the project is missing JUnit, Mockito, or JaCoCo XML
reports. Do **not** apply these snippets unless the user asks.

Parent BOMs, `dependencyManagement`, and `spring-boot-starter-test` already
count as present. Do not add a second copy.

## What “present” means

| Need | Maven | Gradle |
|---|---|---|
| JUnit | `junit`, `junit-jupiter`, `junit-bom`, or `spring-boot-starter-test` | same artifacts in `testImplementation` / a BOM |
| Mockito | `mockito-core`, `mockito-junit-jupiter`, or a starter that brings it | same |
| JaCoCo | `jacoco-maven-plugin` | `id 'jacoco'` / `id("jacoco")` or a `jacoco { }` block |
| XML report | plugin executions that run `report` | `jacocoTestReport` with `xml.required = true` |

After a test run, the XML must exist somewhere under:

- Maven: `**/target/site/jacoco/**/jacoco.xml`
- Gradle: `**/build/reports/jacoco/**/*.xml`

If tests pass but no XML appears, the report is not enabled — that is the
gap, not a missing dependency.

## Maven — JaCoCo plugin

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

JUnit 5 + Mockito, only if nothing equivalent exists (including a parent POM):

```xml
<dependency>
    <groupId>org.junit.jupiter</groupId>
    <artifactId>junit-jupiter</artifactId>
    <version>5.10.2</version>
    <scope>test</scope>
</dependency>
<dependency>
    <groupId>org.mockito</groupId>
    <artifactId>mockito-junit-jupiter</artifactId>
    <version>5.11.0</version>
    <scope>test</scope>
</dependency>
```

JUnit 4, only if the project already uses JUnit 4:

```xml
<dependency>
    <groupId>junit</groupId>
    <artifactId>junit</artifactId>
    <version>4.13.2</version>
    <scope>test</scope>
</dependency>
<dependency>
    <groupId>org.mockito</groupId>
    <artifactId>mockito-core</artifactId>
    <version>3.12.4</version>
    <scope>test</scope>
</dependency>
```

If versions live in a parent / BOM, omit `<version>` and say so.

## Gradle — JaCoCo report XML

```groovy
plugins {
    id 'jacoco'
}

jacoco {
    toolVersion = '0.8.12'
}

tasks.named('jacocoTestReport', JacocoReport) {
    reports {
        xml.required = true
    }
}

tasks.withType(Test).configureEach { testTask ->
    testTask.finalizedBy tasks.named('jacocoTestReport')
}
```

Kotlin DSL equivalent: `xml.required.set(true)` on `jacocoTestReport`.

JUnit 5 + Mockito, only if nothing equivalent exists:

```groovy
dependencies {
    testImplementation platform('org.junit:junit-bom:5.11.4')
    testImplementation 'org.junit.jupiter:junit-jupiter'
    testImplementation 'org.mockito:mockito-junit-jupiter:5.14.0'
    testRuntimeOnly 'org.junit.jupiter:junit-jupiter-engine'
}

tasks.named('test') {
    useJUnitPlatform()
}
```

## Tasks to run (names only)

Use the repository wrapper through the environment shell. Do not invent
OS-specific executables.

- Maven: `test`, `jacoco:report`. Module scope: `-pl <module> -am`
- Gradle: `test`, `jacocoTestReport`. Module scope: the module's own tasks

Prefer the command already documented in README or CI when it differs.
