# Templates: Regras Escopadas (.claude/rules/)

Este arquivo e usado no Passo 5 do workflow. Cada secao abaixo e um arquivo separado
a ser criado em `.claude/rules/`.

Regras escopadas usam YAML frontmatter com `paths:` — a regra so carrega no contexto
quando o Claude esta trabalhando em arquivos que casam com o glob pattern.

---

## 1. testing.md

```markdown
---
description: Convencoes de teste xUnit para projetos .NET
paths:
  - "**/*Tests*/**"
  - "**/*Test*/**"
---

# Convencoes de Teste

## Framework e Ferramentas

- xUnit como framework de teste
- Verificar se o projeto ja usa FluentAssertions ou Assert nativo antes de escolher
- NSubstitute ou Moq para mocking — siga o que o projeto ja usa

## Estrutura de Teste

Sempre use o padrao Arrange/Act/Assert com comentarios de secao:

```csharp
[Fact]
[Trait("Category", "UnitTest")]
public void NomeDoMetodo_Cenario_ResultadoEsperado()
{
    // Arrange
    var sut = new MinhaClasse();

    // Act
    var resultado = sut.Executar();

    // Assert
    Assert.Equal(esperado, resultado);
}
```

## Nomenclatura

- Classe de teste: `{ClasseTestada}Tests` (ex: `MmsiTests`, `LicenseServiceTests`)
- Metodo de teste: `{Metodo}_{Cenario}_{Resultado}` (ex: `Validar_ArquivoVazio_RetornaErro`)
- Idioma dos metodos: siga a convencao existente no projeto (portugues ou ingles)

## Parametrizacao

Prefira [Theory] + [InlineData] para multiplos inputs sobre multiplos [Fact]:

```csharp
[Theory]
[Trait("Category", "Conversion")]
[InlineData("1111", "F")]
[InlineData("0000", "0")]
public void ConverterBinarioParaHex_ValorValido_RetornaCorreto(string input, string expected)
{
    var result = Converter.BinToHex(input);
    Assert.Equal(expected, result);
}
```

## Categorias com [Trait]

Sempre adicione `[Trait("Category", "...")]` para permitir filtro:
- `"UnitTest"` — testes sem dependencia externa
- `"Integration"` — testes que acessam arquivo, rede, hardware
- Use categorias de dominio tambem: `"MMSI"`, `"PDF"`, `"License"`

## Regras

- Um conceito logico por teste (multiplos Assert OK se testam a mesma coisa)
- NAO referencie System.Windows.Forms em projetos de teste
- Use `Path.GetTempPath()` + diretorio unico para testes de I/O
- Limpe arquivos temporarios no Dispose/finally
- Para classes que usam MessageBox internamente: refatore primeiro (veja decoupling-guide)
```

---

## 2. ui-decoupling.md

```markdown
---
description: Regras de separacao entre UI e logica de negocio
paths:
  - "**/*.cs"
---

# Regras de Desacoplamento UI

## Onde cada coisa pode viver

| Elemento | Permitido em | Proibido em |
|----------|-------------|-------------|
| `MessageBox.Show()` | `Form*.cs`, `Program.cs` | Qualquer outra classe |
| `OpenFileDialog` / `SaveFileDialog` | `Form*.cs` | Qualquer outra classe |
| `System.Windows.Forms` (using) | `Form*.cs`, controles UI | Classes em `/Classes/`, `/Services/`, `/Infrastructure/` |
| `System.Management` (WMI) | Classes `*Provider.cs` em Infrastructure | Forms, Services, Domain |
| `public static` mutavel | Evitar. Se necessario, apenas em `Global.cs` | Services, Domain, Infrastructure |

## Padrao para desacoplar

Quando encontrar logica de negocio misturada com UI, aplique este padrao:

### Antes (acoplado):
```csharp
// Em FormPrincipal.cs
private void ValidarLicenca()
{
    if (!File.Exists(path))
    {
        MessageBox.Show("Arquivo nao encontrado");
        return;
    }
    // ... 50 linhas de logica ...
    MessageBox.Show("Licenca valida!");
}
```

### Depois (desacoplado):
```csharp
// Em LicenseValidationService.cs
public ValidacaoDetalhe Validar(string caminhoLicenca)
{
    if (!File.Exists(caminhoLicenca))
        return new ValidacaoDetalhe { Resultado = ValidacaoResultado.ArquivoNaoEncontrado };
    // ... logica pura, sem UI ...
    return new ValidacaoDetalhe { Resultado = ValidacaoResultado.Valida };
}

// Em FormPrincipal.cs
private void ValidarLicenca()
{
    var resultado = _validationService.Validar(path);
    switch (resultado.Resultado)
    {
        case ValidacaoResultado.ArquivoNaoEncontrado:
            MessageBox.Show("Arquivo nao encontrado");
            break;
        case ValidacaoResultado.Valida:
            MessageBox.Show("Licenca valida!");
            break;
    }
}
```

## Result<T> Pattern

Para metodos que podem falhar por motivos de negocio, use resultado estruturado em vez de excecoes:

```csharp
public class Result<T>
{
    public bool Success { get; init; }
    public T? Value { get; init; }
    public string? ErrorMessage { get; init; }

    public static Result<T> Ok(T value) => new() { Success = true, Value = value };
    public static Result<T> Fail(string error) => new() { Success = false, ErrorMessage = error };
}
```

## WinForms e Constructors

WinForms designer exige construtor sem parametros. Para usar DI:

```csharp
public partial class FormPrincipal : Form
{
    private readonly ILicenseService _licenseService;

    // Designer usa este
    public FormPrincipal() : this(null!) { InitializeComponent(); }

    // DI usa este
    public FormPrincipal(ILicenseService licenseService)
    {
        _licenseService = licenseService;
        InitializeComponent();
    }
}
```

Ou use property injection como bridge temporario durante a migracao.
```

---

## 3. architecture.md

```markdown
---
description: Regras de arquitetura e camadas para projetos .NET desktop
paths:
  - "**/*.cs"
---

# Arquitetura em Camadas

## Direcao de Dependencias

```
UI Layer ──────► Service Layer ──────► Domain Layer
                      │                     ▲
                      │                     │
                      └──► Infrastructure ──┘
```

- UI conhece Service e Domain
- Service conhece Domain
- Infrastructure conhece Domain (implementa interfaces)
- Domain NAO conhece ninguem (camada mais interna)

## O que vai em cada camada

### UI Layer (`Form*.cs`, `*ViewModel.cs`, controles)
- Event handlers de controles
- Data binding / populacao de campos
- MessageBox, dialogs, navegacao entre forms
- Nao contem logica de negocio

### Service Layer (`*Service.cs`)
- Orquestracao de operacoes
- Regras de negocio
- Retorna Result<T> ou tipos de dominio
- NAO referencia System.Windows.Forms

### Domain Layer (POCOs, enums, value objects)
- Classes de dados puras
- Enums de estado/resultado
- Validacao intrinseca (ex: MMSI tem 9 digitos)
- Zero dependencias externas

### Infrastructure (`*Provider.cs`, `*Repository.cs`, API clients)
- Implementa interfaces definidas no Service/Domain
- Acesso a hardware (WMI), file system, rede, banco
- Pode ser substituido por mock nos testes

## Dependency Injection

Registre no composition root (Program.cs ou metodo dedicado):

```csharp
var services = new ServiceCollection();
services.AddSingleton<IHardwareInfoProvider, WmiHardwareInfoProvider>();
services.AddTransient<LicenseValidationService>();
services.AddTransient<FormPrincipal>();

var provider = services.BuildServiceProvider();
Application.Run(provider.GetRequiredService<FormPrincipal>());
```

Pacote: `Microsoft.Extensions.DependencyInjection`

## Ao Criar Novos Arquivos

1. Defina interface no Service/Domain layer se o code sera testado
2. Implemente no Infrastructure se acessa recurso externo
3. Registre no DI container
4. Injete via construtor
5. Escreva teste usando mock da interface
```

---

## 4. domain.md

```markdown
---
description: Terminologia e regras de dominio do projeto
paths:
  - "**/*.cs"
---

# Dominio do Projeto

## Glossario

{{DOMAIN_GLOSSARY}}

> Nota: Este glossario deve ser preenchido com os termos especificos do projeto.
> Extraia do CLAUDE.md existente ou pergunte ao usuario.

## Exemplo (dominio maritimo):

| Termo | Significado | Validacao |
|-------|-------------|-----------|
| MMSI | Maritime Mobile Service Identity | Exatamente 9 digitos |
| IMO | International Maritime Organization number | 7 digitos com check digit |
| EPIRB | Emergency Position Indicating Radio Beacon | — |
| VDR | Voyage Data Recorder | Modelos: 1800, 1900 |
| APT | Annual Production Test | Relatorio PDF |
| CoC | Certificate of Conformance | Modo de operacao |
| DSC | Digital Selective Calling | Sistema de radio |

## Convencoes de Idioma

- **Codigo (nomes de classes, metodos, propriedades):** siga a convencao existente do projeto
- **Comentarios:** mesmo idioma do projeto existente
- **Testes:** nomenclatura pode ser no idioma do dominio
- **Commits:** siga a convencao existente
```

---

## Notas de Adaptacao

- Para `domain.md`, sempre analise o CLAUDE.md existente e o codigo para extrair termos
- Se o projeto nao tem dominio especifico, a regra de dominio pode ser omitida
- As regras de `architecture.md` assumem que o projeto esta em processo de desacoplamento;
  para projetos ja bem estruturados, podem ser simplificadas
