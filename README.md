# java-coverage-skills

Skill de cobertura Java para o agente: um playbook, sem scripts. Funciona em
projetos **Maven** e **Gradle**. O agente detecta o build pelos arquivos do
repo e usa o wrapper do próprio projeto no shell do ambiente.

Skill: `java-coverage`

Escopos (inferidos do pedido):

- `full` — projeto inteiro (default)
- `module` — um módulo
- `file` — uma classe
- `diff` — só o que não está commitado

Gate: `LINES >= 92%` e `BRANCHES >= 90%` (branch N/A em interface/enum sem
lógica). No máximo 3 ondas. O que não bater o gate termina como `STILL_BELOW`.

## Como importar

Copie a pasta da skill para o lugar de skills do workspace:

```
skills/java-coverage/
```

Ou para o diretório de skills do agente do projeto (por exemplo
`.agents/.claude/skills/java-coverage` ou `.cursor/skills/java-coverage`).

O nome da skill é o da pasta: `java-coverage`.

## Como usar

Peça o escopo no chat. Exemplos:

Projeto inteiro:

- `Use a skill java-coverage no projeto <path>`
- `Gere cobertura completa do projeto`

Módulo:

- `Use java-coverage no módulo billing`
- `Gere cobertura só do módulo payment-service`

Arquivo / classe:

- `Gere cobertura para src/main/java/com/acme/OrderService.java`
- `Cubra a classe OrderService`

Só o que você desenvolveu:

- `Gere cobertura do que ainda não foi commitado`
- `Cubra só o meu diff`

Se o caminho do projeto não vier no pedido, o agente usa o workspace aberto.

## Como funciona

1. Detecta Maven (`pom.xml`) ou Gradle (`settings.gradle*` / `build.gradle*`).
2. Confere JUnit, Mockito e JaCoCo. Se faltar, para e explica — não altera o build sozinho.
3. Roda os testes + relatório JaCoCo pelo wrapper do repo.
4. Lê o XML do JaCoCo (procura; não chuta um path).
5. Escreve ou completa `<ClassName>Test.java` em `src/test/`.
6. Repete no máximo 3 vezes.

Regras fixas:

- Nunca edita `src/main/`.
- Nunca adiciona exclusão Sonar/JaCoCo para inflar o número.
- Espelha o estilo de teste do projeto (JUnit 4 ou 5, nomes, tags, classe base).
- Cada teste afirma um contrato observável (valor, mensagem, interação).
  Ramo sem contrato fica `BLOCKED — no contract` — não se inventa teste
  só para pintar o JaCoCo.
- Progresso fica no chat. Não cria `docs/coverage-tracker-*.md`.

## Pré-requisitos

- Projeto Java com Maven ou Gradle.
- JaCoCo gerando relatório XML.
- JUnit (4 ou 5) já no projeto — ou o usuário autoriza adicionar o que falta.

## Versionamento

Versão em [skill-pack.xml](./skill-pack.xml) (`<version>`).

- [CHANGELOG.md](./CHANGELOG.md)
- [RELEASE.md](./RELEASE.md)
