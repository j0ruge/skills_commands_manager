---
name: dotnet-desktop-setup
description: >
  Configura e audita projetos C#/.NET desktop (WinForms, WPF, Avalonia) para desenvolvimento
  assistido por Claude Code em Windows. Gera ou atualiza CLAUDE.md (global e por projeto),
  regras escopadas em .claude/rules/, .editorconfig, Directory.Build.props, global.json e hooks
  de pre-commit. Audita codebase existente para detectar acoplamento UI/logica, God Classes, e
  violacoes arquiteturais, recomendando refatoracao estrutural e desacoplamento. Use quando o
  usuario quiser: configurar projeto .NET desktop para Claude Code; criar ou melhorar CLAUDE.md
  de projeto C#; adicionar padroes de codificacao e convencoes de teste ao projeto; auditar
  acoplamento ou arquitetura do codebase; preparar ambiente de desenvolvimento Windows para IA;
  migrar projeto .NET Framework para .NET 8+ e reconfigurar tooling. NAO use para: escrever
  testes ou codigo especifico, resolver erros de compilacao, deploy/CI-CD, projetos web/API/mobile,
  adicionar bibliotecas, ou otimizacao de performance.
---

# dotnet-desktop-setup

Skill de setup para projetos C#/.NET desktop no Claude Code. Funciona como um wizard que analisa
o estado atual do ambiente e codebase, depois gera ou atualiza arquivos de configuracao para
maximizar a qualidade do codigo gerado pelo Claude.

Usa **progressive disclosure** — este arquivo contem o workflow e decisoes. Templates e guias
detalhados ficam em `references/` e sao lidos sob demanda.

---

## Quando usar

- Configurar um novo projeto .NET para Claude Code
- Melhorar CLAUDE.md de um projeto C# existente
- Adicionar padroes de codificacao (.editorconfig, regras escopadas)
- Preparar codebase para desacoplamento UI (WinForms -> WPF/Avalonia)
- Configurar convencoes de teste xUnit
- Auditar acoplamento UI/negocio no codebase

---

## Workflow: 8 Passos

Execute os passos em ordem. Cada passo verifica o estado atual antes de agir — nunca sobrescreve
arquivos existentes sem apresentar diff ao usuario.

### Passo 1: Auditoria do Ambiente

Tente executar `scripts/audit-environment.sh` (requer Git Bash no Windows).
Se bash nao estiver disponivel, execute os comandos equivalentes inline usando as ferramentas
Bash, Grep e Glob do Claude Code:

- `dotnet --list-sdks` para listar SDKs
- Glob para verificar existencia de arquivos de config
- Grep para escanear acoplamento (MessageBox, System.Windows.Forms, public static)
- Grep para contar [Fact] e [Theory]

O script/auditoria coleta:
- SDKs .NET instalados (`dotnet --list-sdks`)
- Arquivos de config existentes (CLAUDE.md, .editorconfig, Directory.Build.props, global.json, .claude/rules/)
- Estrutura da solution (.sln → projetos e target frameworks)
- Indicadores de acoplamento UI:
  - `MessageBox.Show()` em arquivos que NAO sao Form*.cs
  - `System.Windows.Forms` em classes fora da camada UI
  - Campos `public static` mutaveis (padrao Global.cs)
- Cobertura de testes (contagem de [Fact] e [Theory])

Apresente o relatorio ao usuario antes de prosseguir. Se o usuario pediu apenas auditoria, pare aqui.

### Passo 2: global.json

Gere `global.json` na raiz da solution para fixar a versao do SDK:

```json
{
  "sdk": {
    "version": "<versao-mais-alta-instalada>",
    "rollForward": "latestFeature"
  }
}
```

- Use a versao mais alta detectada no Passo 1
- `rollForward: latestFeature` permite patch updates sem quebrar
- Se `global.json` ja existe, mostre diff e pergunte ao usuario

### Passo 3: CLAUDE.md Global (~/.claude/CLAUDE.md)

Leia `references/global-claude-md-template.md` para o template completo.

Este arquivo contem convencoes que se aplicam a **qualquer** projeto C#/.NET do usuario:
- Naming conventions (PascalCase publico, _camelCase privado)
- Padroes .NET CLI (--filter, --no-restore, -v q)
- Convencoes de teste (Arrange/Act/Assert, nomenclatura)
- Anti-padroes universais (MessageBox em dominio, static mutavel)
- Preferencias de linguagem C# moderna (file-scoped namespaces, pattern matching, collection expressions)

**Regra:** Se `~/.claude/CLAUDE.md` ja existe, NAO sobrescreva. Leia o conteudo atual, identifique
lacunas comparando com o template, e proponha apenas as adicoes necessarias.

### Passo 4: CLAUDE.md do Projeto

Leia `references/project-claude-md-template.md` para o template.

O CLAUDE.md do projeto segue o framework **WHAT-WHY-HOW**:
- **WHAT**: Stack exata com versoes, modelos de dados, dominio
- **WHY**: Decisoes arquiteturais e motivacoes
- **HOW**: Comandos exatos de build/test/release

Limite: **300 linhas maximo**. Se o existente ja esta bom (como projetos com CLAUDE.md detalhado),
proponha apenas melhorias incrementais:
- Adicionar secao de convencoes se ausente
- Adicionar referencia a codigo canonico (ex: "Para novo service, veja `Services/LicenseValidationService.cs`")
- Adicionar anti-padroes especificos do projeto

### Passo 5: Regras Escopadas (.claude/rules/)

Leia `references/scoped-rules-templates.md` para os 4 templates.

Regras escopadas usam YAML frontmatter com `paths:` para ativar apenas em arquivos relevantes:

| Arquivo | Escopo | Conteudo |
|---------|--------|----------|
| `testing.md` | `**/*Tests*/**` | Convencoes xUnit, Arrange/Act/Assert, nomenclatura |
| `ui-decoupling.md` | `**/*.cs` | Onde MessageBox e permitido, separacao de camadas |
| `architecture.md` | `**/*.cs` | Direcao de dependencias, DI, camadas |
| `domain.md` | `**/*.cs` | Glossario de dominio, regras de validacao especificas |

Para `domain.md`, analise o CLAUDE.md existente e extraia terminologia do projeto.

Crie o diretorio `.claude/rules/` se nao existir. Para regras que ja existem, mostre diff.

### Passo 6: .editorconfig

Leia `references/editorconfig-template.md` para o template completo.

Pontos criticos para projetos .NET desktop:
- `charset = utf-8-bom` — necessario para caracteres especiais (portugues, acentos)
- `end_of_line = crlf` — padrao Windows
- Naming rules com severity `warning` (nao `error`) para adocao gradual
- Analyzers CA relevantes habilitados, CA2007 desabilitado (nao relevante para desktop)

Se `.editorconfig` ja existe, mostre diff. Nunca sobrescreva.

### Passo 7: Directory.Build.props

Gere `Directory.Build.props` na raiz da solution com propriedades compartilhadas.

**Cuidado com frameworks mistos!** Se a solution tem projetos em net5.0, net6.0 e net8.0,
use condicoes para nao quebrar builds:

```xml
<Project>
  <PropertyGroup>
    <Nullable>enable</Nullable>
    <TreatWarningsAsErrors>false</TreatWarningsAsErrors>
  </PropertyGroup>
  <PropertyGroup Condition="$([MSBuild]::IsTargetFrameworkCompatible('$(TargetFramework)', 'net6.0'))">
    <ImplicitUsings>enable</ImplicitUsings>
  </PropertyGroup>
</Project>
```

Apos gerar, **sempre** valide: `dotnet build <solution>.sln`

Se `Directory.Build.props` ja existe, mostre diff. Nunca sobrescreva.

### Passo 8: Hooks Claude Code (recomendacao)

Apresente ao usuario como **recomendacao**, nao aplique automaticamente:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "command": "dotnet build --no-restore -v q 2>&1 | tail -5",
        "description": "Build rapido apos editar arquivo C#"
      }
    ],
    "PreCommit": [
      {
        "command": "dotnet test --no-build -v q",
        "description": "Roda testes antes de commit"
      }
    ]
  }
}
```

Explique: hooks de build a cada edicao podem ser lentos em solutions grandes. O usuario decide.

---

## Tratamento de Cenarios

### Projeto novo (sem configs)
Execute todos os 8 passos na ordem.

### Projeto existente com config parcial
1. Execute Passo 1 (auditoria)
2. Apresente o que existe vs o que falta
3. Pergunte ao usuario quais passos executar
4. Para cada arquivo existente, mostre diff das adicoes propostas

### Apenas auditoria
Execute apenas Passo 1, apresente relatorio.

### Apenas regras escopadas
Execute Passo 1 (rapido) + Passo 5.

---

## Guias de Referencia (progressive disclosure level 3)

Leia estes arquivos **somente quando necessario** no passo correspondente:

| Arquivo | Leia quando... |
|---------|----------------|
| `references/global-claude-md-template.md` | Passo 3 — criando/atualizando CLAUDE.md global |
| `references/project-claude-md-template.md` | Passo 4 — criando/atualizando CLAUDE.md do projeto |
| `references/scoped-rules-templates.md` | Passo 5 — criando regras em .claude/rules/ |
| `references/editorconfig-template.md` | Passo 6 — criando .editorconfig |
| `references/decoupling-guide.md` | Usuario pede ajuda com desacoplamento UI ou arquitetura |
| `references/testing-guide.md` | Usuario pede ajuda com setup/padroes de testes xUnit |

---

## Detalhes Criticos (aprendidos nos testes)

Estes pontos falharam consistentemente quando a skill NAO foi usada — preste atencao especial:

1. **utf-8-bom, NAO utf-8** — Projetos em portugues PRECISAM de `charset = utf-8-bom` no .editorconfig. utf-8 sem BOM causa problemas com acentos em builds do Visual Studio.

2. **YAML frontmatter nas regras escopadas** — Toda regra em `.claude/rules/` DEVE ter frontmatter com `paths:`. Sem isso, a regra carrega em todo contexto e polui o prompt.

3. **Condicoes no Directory.Build.props** — Solutions com frameworks mistos (net5.0 + net8.0) QUEBRAM se voce aplicar `<ImplicitUsings>enable</ImplicitUsings>` sem condicao de framework. Sempre use `Condition="$([MSBuild]::IsTargetFrameworkCompatible(...))"`.

4. **CLAUDE.md global vs projeto** — O modelo sem skill nao conhece a hierarquia `~/.claude/CLAUDE.md` (global) vs `./CLAUDE.md` (projeto). Sempre crie ambos.

5. **Nunca sobrescrever CLAUDE.md existente** — Proponha adicoes como diff. O usuario pode ter contexto importante que seria perdido.

6. **Global.cs e estado estatico** — Sempre incluir na auditoria a busca por `public static` mutavel. E o acoplamento mais insidioso e facil de esquecer.

7. **Atualizar docs apos migracao UI** — Quando a skill gera CLAUDE.md para um projeto que depois migra de WinForms para WPF, os nomes de arquivos UI e a descricao do stack ficam desatualizados. Sempre verificar se referencias a Form*.cs ainda existem apos migracao. Veja `references/decoupling-guide.md` secao "Checklist Pos-Migracao".

---

## Anti-padroes desta Skill

Evite estes erros ao executar o workflow:

- **Sobrescrever sem perguntar** — Sempre mostre diff para arquivos existentes
- **Directory.Build.props sem condicoes** — Solutions com frameworks mistos quebram se voce assume net8.0 para todos
- **Fixar SDK nao instalado** — global.json deve refletir o que `dotnet --list-sdks` retorna
- **Adicionar pacotes sem consultar** — Nao adicione FluentAssertions, NSubstitute etc. sem perguntar
- **Forcar MVVM em WinForms** — WinForms nao tem data binding nativo. Use Passive View/MVP como intermediario
- **Ignorar convencoes existentes** — Se o projeto usa portugues nos testes, mantenha. Se usa Assert direto, nao force FluentAssertions
- **CLAUDE.md gigante** — Se passar de 300 linhas, mova conteudo para .claude/rules/
