# Guia de Desacoplamento UI para Apps .NET Desktop

Este guia e carregado sob demanda quando o usuario pede ajuda com desacoplamento UI,
migracao de WinForms, ou arquitetura de desktop apps.

---

## O Problema

Apps WinForms legados tipicamente sofrem de:

1. **MessageBox em logica de negocio** — Impede testes unitarios, mistura UI com decisoes
2. **Estado global estatico** — `Global.cs` com `public static` mutavel atua como service locator
3. **Dialogs em metodos de negocio** — OpenFileDialog/SaveFileDialog acoplam I/O ao processamento
4. **System.Windows.Forms em dominio** — Classes de dados importam namespaces de UI
5. **Forms de 1000+ linhas** — Event handlers contem regras de negocio complexas

---

## Estrategia: Strangler Fig Pattern

NAO reescreva tudo de uma vez. Aplique o padrao Strangler Fig — envolva o codigo legado
com novas abstraccoes e substitua incrementalmente:

```
[Iteracao 1] Extrair interfaces para dependencias externas (WMI, File I/O)
[Iteracao 2] Criar service classes que encapsulam logica extraida dos Forms
[Iteracao 3] Refatorar Forms para chamar services (Forms ficam "magros")
[Iteracao 4] Adicionar DI container no Program.cs
[Iteracao 5] Escrever testes para os services
[Iteracao 6] (Futuro) Migrar UI para WPF/Avalonia com ViewModels
```

Cada iteracao deve compilar e todos os testes existentes devem passar.

---

## Passo a Passo

### 1. Extrair Return Types (Result<T>)

Substitua metodos `void` que mostram MessageBox por metodos que retornam resultado estruturado:

```csharp
// Defina uma vez, use em todo o projeto
public enum OperationStatus { Success, Warning, Error }

public class OperationResult
{
    public OperationStatus Status { get; init; }
    public string Message { get; init; } = "";

    public static OperationResult Ok() => new() { Status = OperationStatus.Success };
    public static OperationResult Warn(string msg) => new() { Status = OperationStatus.Warning, Message = msg };
    public static OperationResult Fail(string msg) => new() { Status = OperationStatus.Error, Message = msg };
}

public class OperationResult<T> : OperationResult
{
    public T? Value { get; init; }

    public static OperationResult<T> Ok(T value) => new() { Status = OperationStatus.Success, Value = value };
    public new static OperationResult<T> Fail(string msg) => new() { Status = OperationStatus.Error, Message = msg };
}
```

### 2. Extrair Interfaces para Dependencias Externas

```csharp
// Interface no Service/Domain layer
public interface IHardwareInfoProvider
{
    string GetProcessorID();
    string GetMotherBoardSerialNumber();
}

// Implementacao no Infrastructure layer
public class WmiHardwareInfoProvider : IHardwareInfoProvider
{
    public string GetProcessorID()
    {
        // Codigo WMI extraido do Form/Licenca.cs
        using var searcher = new ManagementObjectSearcher("select ProcessorId from Win32_Processor");
        // ...
    }
}
```

### 3. Criar Service Classes

O service recebe dependencias via construtor e retorna resultados estruturados:

```csharp
public class LicenseValidationService
{
    private readonly IHardwareInfoProvider _hardwareProvider;
    private readonly Cripto _cripto;

    public LicenseValidationService(IHardwareInfoProvider hardwareProvider, Cripto cripto)
    {
        _hardwareProvider = hardwareProvider;
        _cripto = cripto;
    }

    public OperationResult<LicenseInfo> Validar(string caminhoLicenca)
    {
        if (!File.Exists(caminhoLicenca))
            return OperationResult<LicenseInfo>.Fail("Arquivo de licenca nao encontrado");

        // Logica pura, sem MessageBox, sem WMI direto
        var hwId = _hardwareProvider.GetProcessorID();
        // ...
        return OperationResult<LicenseInfo>.Ok(licenseInfo);
    }
}
```

### Null-safety em Desserializacao

`JsonSerializer.Deserialize<T>()` pode retornar null mesmo com JSON valido. Services que desserializam devem validar:

```csharp
public HardwareInfo RecuperarDeArquivo(string filePath)
{
    string json = File.ReadAllText(filePath);
    var info = JsonSerializer.Deserialize<HardwareInfo>(json);
    if (info == null)
        throw new InvalidDataException($"Falha ao desserializar HardwareInfo de '{filePath}'.");
    return info;
}
```

Alternativa com Result<T>:
```csharp
var info = JsonSerializer.Deserialize<HardwareInfo>(json);
if (info == null)
    return OperationResult<HardwareInfo>.Fail("JSON invalido ou incompativel");
```

### 4. Refatorar Form para ser "Magro"

O Form so faz: abrir dialog → chamar service → mostrar resultado:

```csharp
public partial class FormPrincipal : Form
{
    private readonly LicenseValidationService _licenseService;

    public FormPrincipal(LicenseValidationService licenseService)
    {
        _licenseService = licenseService;
        InitializeComponent();
    }

    private void ButtonValidar_Click(object sender, EventArgs e)
    {
        var resultado = _licenseService.Validar(txtPath.Text);

        if (resultado.Status == OperationStatus.Error)
            MessageBox.Show(resultado.Message, "Erro", MessageBoxButtons.OK, MessageBoxIcon.Error);
        else
            PopularCampos(resultado.Value!);
    }
}
```

### 5. Configurar DI no Program.cs

```csharp
static class Program
{
    [STAThread]
    static void Main()
    {
        Application.SetHighDpiMode(HighDpiMode.SystemAware);
        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);

        var services = new ServiceCollection();
        ConfigureServices(services);

        using var provider = services.BuildServiceProvider();
        Application.Run(provider.GetRequiredService<FormPrincipal>());
    }

    static void ConfigureServices(IServiceCollection services)
    {
        // Infrastructure
        services.AddSingleton<IHardwareInfoProvider, WmiHardwareInfoProvider>();
        services.AddSingleton<Cripto>();

        // Services
        services.AddTransient<LicenseValidationService>();

        // Forms
        services.AddTransient<FormPrincipal>();
    }
}
```

Pacote necessario: `Microsoft.Extensions.DependencyInjection`

### 6. Escrever Testes

Com o service desacoplado, testes sao simples:

```csharp
public class LicenseValidationServiceTests
{
    [Fact]
    [Trait("Category", "License")]
    public void Validar_ArquivoNaoExiste_RetornaErro()
    {
        // Arrange
        var mockHw = Substitute.For<IHardwareInfoProvider>();
        var cripto = new Cripto();
        var sut = new LicenseValidationService(mockHw, cripto);

        // Act
        var resultado = sut.Validar("/caminho/inexistente.lic");

        // Assert
        Assert.Equal(OperationStatus.Error, resultado.Status);
        Assert.Contains("nao encontrado", resultado.Message);
    }
}
```

---

## WinForms Designer e DI

O designer do WinForms exige construtor sem parametros. Duas abordagens:

### Opcao A: Construtor duplo (bridge)
```csharp
public FormPrincipal() : this(null!) { } // Designer
public FormPrincipal(IMyService service) { _service = service; InitializeComponent(); }
```

### Opcao B: Property injection (temporario)
```csharp
public IMyService MyService { get; set; } = null!;
// Setado pelo DI apos construcao
```

Opcao A e preferivel. O construtor sem parametros so e chamado pelo designer em tempo de design.

---

## Caminho para UI Moderna

Apos desacoplar com services + DI, a migracao de UI fica simples:

| De | Para | Esforco | Quando |
|----|------|---------|--------|
| WinForms | WinForms + MVP | Baixo | Ja esta pronto quando services existem |
| WinForms | WPF + MVVM | Medio | Services viram base dos ViewModels |
| WinForms | Avalonia + MVVM | Medio | Cross-platform, similar a WPF |
| WinForms | MAUI | Alto | Melhor para mobile-first |

**Recomendacao para projetos Windows-only:** WPF com CommunityToolkit.Mvvm.
**Recomendacao para cross-platform:** Avalonia UI.

Em ambos os casos, os services criados no desacoplamento sao reutilizados — so muda a camada UI.

---

## Exemplo Canonico

Se o projeto tem um SPEC de refatoracao (como `SPEC-LicenceManager-Refactoring.md`),
use-o como referencia para o padrao de desacoplamento. Ele documenta:
- Estado atual (acoplamento)
- Arquitetura-alvo (camadas)
- Tarefas sequenciais
- Testes novos
- Criterios de aceite

---

## Checklist Pos-Migracao

Apos completar migracao de UI framework (ex: WinForms → WPF), atualizar:

1. [ ] CLAUDE.md do projeto — descricao do stack e UI framework
2. [ ] CLAUDE.md do projeto — referencias a arquivos UI deletados/criados (Form*.cs → MainWindow.xaml)
3. [ ] CLAUDE.md do projeto — tabela de projetos da solution
4. [ ] .gitignore — adicionar exclusoes para runtimes do novo framework (ex: EBWebView/ para WebView2)
5. [ ] Remover referencias a classes/arquivos que nao existem mais
