# Guia de Testes xUnit para .NET Desktop

Este guia e carregado sob demanda quando o usuario pede ajuda com setup de testes,
padroes de teste, ou cobertura.

---

## Setup do Projeto de Teste

### Criar projeto de teste

```bash
dotnet new xunit -n MeuProjeto.Tests
dotnet sln add MeuProjeto.Tests
dotnet add MeuProjeto.Tests reference MeuProjeto
```

### Pacotes recomendados

```xml
<ItemGroup>
  <!-- Framework -->
  <PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.*" />
  <PackageReference Include="xunit" Version="2.*" />
  <PackageReference Include="xunit.runner.visualstudio" Version="2.*" />

  <!-- Mocking (escolha UM) -->
  <PackageReference Include="NSubstitute" Version="5.*" />
  <!-- OU -->
  <PackageReference Include="Moq" Version="4.*" />

  <!-- Opcional: assertions mais legiveiss -->
  <PackageReference Include="FluentAssertions" Version="7.*" />
</ItemGroup>
```

**Antes de adicionar pacotes:** verifique o que o projeto ja usa. Nao misture NSubstitute com Moq,
nem FluentAssertions com Assert nativo, no mesmo projeto.

### Target Framework

O projeto de teste deve usar o **mesmo target framework** do projeto principal:
```xml
<TargetFramework>net8.0-windows7.0</TargetFramework>
```

Se o projeto principal usa `-windows`, o teste tambem precisa (para resolver tipos WinForms).
Mas o codigo de teste NAO deve instanciar Forms nem usar controles UI.

---

## Organizacao dos Testes

### Estrutura de diretorios

Espelhe a estrutura do projeto fonte:

```
MeuProjeto/
├── Services/
│   └── LicenseValidationService.cs
├── Classes/
│   └── Mmsi.cs
└── Infrastructure/
    └── WmiHardwareInfoProvider.cs

MeuProjeto.Tests/
├── Services/
│   └── LicenseValidationServiceTests.cs
├── Classes/
│   └── MmsiTests.cs
└── Infrastructure/
    └── WmiHardwareInfoProviderTests.cs  (integration test)
```

### Nomenclatura

| Elemento | Convencao | Exemplo |
|----------|-----------|---------|
| Classe | `{Classe}Tests` | `MmsiTests` |
| Metodo | `{Metodo}_{Cenario}_{Resultado}` | `IsValidBits_StringVazia_LancaArgumentException` |
| Idioma | Siga o projeto | PT-BR OK: `Validar_ArquivoVazio_RetornaErro` |

---

## Padroes por Tipo de Classe

### Classes de Dominio (logica pura)

Mais faceis de testar — sem mocks necessarios:

```csharp
public class MmsiTests
{
    [Theory]
    [Trait("Category", "MMSI")]
    [InlineData("219393000", true)]
    [InlineData("12345", false)]
    [InlineData("", false)]
    [InlineData(null, false)]
    public void IsValid_VariousInputs_ReturnsExpected(string? mmsi, bool expected)
    {
        // Act
        var result = Mmsi.IsValid(mmsi);

        // Assert
        Assert.Equal(expected, result);
    }
}
```

### Service Classes (com dependencias)

Use mocks para isolar o service:

```csharp
public class LicenseValidationServiceTests
{
    private readonly IHardwareInfoProvider _mockHw;
    private readonly Cripto _cripto;
    private readonly LicenseValidationService _sut;

    public LicenseValidationServiceTests()
    {
        // Arrange (compartilhado)
        _mockHw = Substitute.For<IHardwareInfoProvider>();
        _mockHw.GetProcessorID().Returns("PROC123");
        _mockHw.GetMotherBoardSerialNumber().Returns("MB456");
        _cripto = new Cripto();
        _sut = new LicenseValidationService(_mockHw, _cripto);
    }

    [Fact]
    [Trait("Category", "License")]
    public void Validar_ArquivoNaoExiste_RetornaErro()
    {
        // Act
        var resultado = _sut.Validar("/inexistente.lic");

        // Assert
        Assert.Equal(OperationStatus.Error, resultado.Status);
    }

    [Fact]
    [Trait("Category", "License")]
    public void Validar_LicencaValida_RetornaOk()
    {
        // Arrange
        var tempFile = CriarLicencaTemporaria("PROC123", "MB456", DateTime.Now.AddDays(60));

        // Act
        var resultado = _sut.Validar(tempFile);

        // Assert
        Assert.Equal(OperationStatus.Success, resultado.Status);
        Assert.NotNull(resultado.Value);

        // Cleanup
        File.Delete(tempFile);
    }
}
```

### Testes de I/O (integracao)

Use diretorios temporarios e limpe apos:

```csharp
public class LicenseServiceTests : IDisposable
{
    private readonly string _tempDir;

    public LicenseServiceTests()
    {
        _tempDir = Path.Combine(Path.GetTempPath(), $"test_{Guid.NewGuid():N}");
        Directory.CreateDirectory(_tempDir);
    }

    [Fact]
    [Trait("Category", "Integration")]
    public void SalvarParaArquivo_DadosCompletos_ArquivoCriado()
    {
        // Arrange
        var service = new LicenseService(new Cripto());
        var path = Path.Combine(_tempDir, "test.lic");
        var info = new LicenseInfo { /* ... */ };

        // Act
        service.SalvarParaArquivo(info, path);

        // Assert
        Assert.True(File.Exists(path));
    }

    public void Dispose()
    {
        if (Directory.Exists(_tempDir))
            Directory.Delete(_tempDir, recursive: true);
    }
}
```

### Classes que AINDA usam MessageBox (legado)

NAO tente testar o MessageBox. Em vez disso:

1. Extraia a logica para um service (veja decoupling-guide.md)
2. Teste o service
3. O Form fica como "thin wrapper" — nao precisa de teste unitario

Se a extracao ainda nao foi feita, documente como lacuna de teste e siga em frente.

---

## Executando Testes

```bash
# Todos os testes
dotnet test

# Uma classe especifica
dotnet test --filter "FullyQualifiedName~MmsiTests"

# Uma categoria
dotnet test --filter "Category=License"

# Com output detalhado
dotnet test -v normal

# Excluindo testes de integracao
dotnet test --filter "Category!=Integration"
```

---

## Categorias Recomendadas com [Trait]

| Categoria | Quando usar |
|-----------|-------------|
| `UnitTest` | Testes sem I/O nem dependencia externa |
| `Integration` | Testes que acessam filesystem, rede, hardware |
| Dominio especifico | `MMSI`, `License`, `PDF`, `VDR` etc. |

---

## Checklist de Cobertura

Ao auditar a cobertura de um projeto, verifique:

- [ ] Classes de dominio (POCOs com logica) — devem ter testes
- [ ] Services — devem ter testes com mocks
- [ ] Conversores/parsers — devem ter testes com edge cases
- [ ] Validacao — deve testar happy path + todos os erros
- [ ] Forms — NAO precisam de teste unitario (testar os services que eles chamam)
- [ ] Infrastructure (WMI, API) — testes de integracao opcionais, marcados com [Trait]

---

## Erros Comuns

1. **Testar implementacao, nao comportamento** — Nao teste que um metodo privado foi chamado;
   teste que o resultado publico esta correto
2. **Mocks excessivos** — Se voce precisa de 5+ mocks, o service esta fazendo demais; refatore
3. **Testes frageis** — Nao teste strings exatas de MessageBox; teste o resultado/status
4. **Esquecer cleanup** — Arquivos temporarios acumulam; use IDisposable
5. **Copiar testes ao inves de parametrizar** — Use [Theory]+[InlineData] para inputs multiplos
