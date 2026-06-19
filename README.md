# java-coverage-skills

Conjunto de skills para automação de cobertura de testes Java com foco em Maven + JaCoCo.

Escopos disponíveis:

- `java-coverage-full`: cobertura do projeto inteiro.
- `java-coverage-module`: cobertura de um módulo específico.
- `java-coverage-file`: cobertura de uma classe/arquivo específico.
- `java-coverage-diff`: cobertura apenas do que está em desenvolvimento (não commitado), com gate por linhas em diff.

**Como Importar No Seu Workspace**
Você pode usar este pacote em um workspace local ou dentro de `.agents/.claude`.

Opção 1: copiar a pasta inteira para o workspace:

```bash
cp -r java-coverage-skills /caminho/do/seu-workspace/skills/
```

Opção 2: versionar como subpasta do repositório do projeto:

```bash
mkdir -p .agents/.claude/skills
cp -r java-coverage-skills .agents/.claude/skills/
```

Depois da importação, as skills ficam disponíveis pelos nomes de cada pasta (`java-coverage-full`, `java-coverage-module`, `java-coverage-file`, `java-coverage-diff`).

**Como Usar (Exemplos de Prompt)**
No chat com o agente, peça explicitamente o escopo desejado.

Projeto inteiro:

- `Use a skill java-coverage-full no projeto /path/do-projeto`
- `Gere cobertura completa do projeto /path/do-projeto`
- `Use a skill java-coverage-full para o projeto tal`

Se você não informar caminho no `java-coverage-full`, o agente deve inferir o projeto
pelos projetos abertos no workspace/IDE. Somente quando não houver candidato claro
ele deve pedir explicitamente o caminho.

Módulo específico:

- `Use a skill java-coverage-module no módulo billing do projeto /path/do-projeto`
- `Rode cobertura apenas no módulo payment-service`

Arquivo/classe específica:

- `Use a skill java-coverage-file para src/main/java/com/acme/OrderService.java`
- `Gere cobertura para a classe OrderService`

Somente o que você desenvolveu:

- `Use a skill java-coverage-diff neste projeto`
- `Gere cobertura só para o que ainda não foi commitado`

**Como As Skills Funcionam**
Fluxo base (todas):

1. Valida prontidão do projeto.
2. Valida dependências de teste no `pom.xml` (`junit`, `mockito`, `jacoco`).
3. Analisa cobertura inicial.
4. Planeja geração por prioridade de gap.
5. Gera/ajusta testes.
6. Compila e executa testes.
7. Reanalisa cobertura e repete em ondas até bater gate ou bloquear com motivo explícito.

Regras de gate:

- `full/module/file`: gate por classe (`LINES >= 92%` e `BRANCHES >= 90%`, com exceções de classes sem branch aplicável).
- `diff`: gate só nas linhas alteradas não commitadas (`staged`, `unstaged`, `untracked`), sem penalizar linhas antigas fora do diff.

Política de progresso:

- `full/module`: geram tracker em `docs/*.md` e atualizam a cada onda.
- `file/diff`: progresso em memória/console (sem tracker persistido).

Regra importante:

- Se já existe teste para uma classe mas ela continua abaixo do gate, a skill deve adicionar novos testes no arquivo existente para cobrir os gaps.

**Pré-Requisitos**

- Projeto Java com Maven.
- JaCoCo disponível no build.
- Recomendado: `mvn test jacoco:report` executável no projeto.

**Versionamento**
A versão do pacote é centralizada em [skill-pack.xml](./skill-pack.xml) no campo `<version>`.

Arquivos de apoio:

- [CHANGELOG.md](./CHANGELOG.md)
- [RELEASE.md](./RELEASE.md)

## Uso por caminho absoluto (como no seu pedido)

Voce pode pedir explicitamente com caminho local, por exemplo:

- `Utilize a skill C:\Users\Felipe Catuaba\Projetos\skills\java-coverage-skills no projeto hermes-finance`

Comportamento esperado do agente:

1. Ler `skill-pack.xml` para descobrir as skills disponiveis.
2. Resolver automaticamente a skill `java-coverage-full` quando o pedido for cobertura completa.
3. Executar os scripts da skill usando Maven via prioridade:
   - `mvn` no PATH;
   - `mvnw.cmd` (Windows) no `project_root`;
   - `mvnw` (Linux/macOS) no `project_root`.
4. Tratar classes sem branch aplicavel como `BRANCHES = N/A` no gate.

Isso evita falha por "mvn not found" em Windows quando o projeto usa wrapper Maven.

## Performance e consistencia (obrigatorio)

- Nunca execute comandos Maven em paralelo no mesmo `project_root`.
- Fluxo recomendado por onda:
  1. `run-tests-and-verify.py` (executa `mvn test` uma vez)
  2. `run-jacoco-report.py` (fast path: `-DskipTests jacoco:report`)
  3. fallback automatico para `test jacoco:report` apenas se artefatos JaCoCo estiverem ausentes.
- Isso reduz tempo total sem quebrar o gate: validacao de testes continua obrigatoria e o gate e sempre calculado do JaCoCo final.
