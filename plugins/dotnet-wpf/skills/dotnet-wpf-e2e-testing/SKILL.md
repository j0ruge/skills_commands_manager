---
name: dotnet-wpf-e2e-testing
description: FlaUI + xUnit E2E testing for WPF — project setup, AutomationId annotation, Page Objects, smoke tests, file-dialog automation, CI/CD wiring. Unit tests live in dotnet-wpf-mvvm. Triggers — WPF E2E, FlaUI, AutomationId, Page Object, smoke test.
---

# Testes E2E para WPF com FlaUI

Este skill guia a criação de testes end-to-end para aplicações WPF usando FlaUI (UI Automation API do Windows) e xUnit. Ele cobre desde a configuração do projeto até Page Objects e CI/CD.

## Pirâmide de Testes — Onde E2E se Encaixa

```
                    ┌──────────┐
                    │   E2E    │  FlaUI: 2-3 smoke tests por tela
                    │  (UI)    │  Fluxos principais end-to-end
                   ┌┴──────────┴┐
                   │  ViewModel  │  xUnit: cobertura completa de lógica
                   │   Tests     │  Commands, propriedades, validação
                  ┌┴────────────┴┐
                  │   Service     │  xUnit: lógica de negócio
                  │    Tests      │  Cripto, License, Validation
                  └──────────────┘
```

Testes E2E são os mais caros de manter. Crie poucos — apenas smoke tests que verificam que a UI renderiza e os fluxos principais funcionam. Lógica de negócio pertence aos testes de ViewModel e Service.

## Workflow Completo

Siga estes passos na ordem. Cada seção referencia arquivos detalhados em `references/` quando necessário.

### Passo 1: Criar Projeto de Testes E2E

Crie um projeto **separado** dos testes unitários, pois testes E2E têm dependências diferentes e precisam rodar em ambiente com desktop interativo.

#### Estrutura recomendada

```
<SolutionRoot>/
├── MyApp/                        # Projeto WPF principal
├── MyApp.Tests/                  # Testes unitários (ViewModel, Service)
└── MyApp.E2ETests/               # Testes E2E (FlaUI)
    ├── MyApp.E2ETests.csproj
    ├── Infrastructure/
    │   ├── FlaUITestBase.cs      # Base class para todos os testes
    │   ├── TestConstants.cs      # Caminhos, timeouts, dados de teste
    │   └── FileDialogHelper.cs   # Helper para automação de file dialogs
    ├── Pages/
    │   ├── MainWindowPage.cs     # Page Object da janela principal
    │   └── ...                   # Um Page Object por tela
    └── Tests/
        ├── MainWindowTests.cs    # Smoke tests da janela principal
        └── ...                   # Testes por funcionalidade
```

#### .csproj do projeto E2E

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <!-- Deve coincidir com o TFM do projeto WPF alvo -->
    <TargetFramework>net10.0-windows7.0</TargetFramework>
    <UseWPF>true</UseWPF>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
    <IsPackable>false</IsPackable>
  </PropertyGroup>

  <ItemGroup>
    <!-- FlaUI — sempre usar UIA3 para WPF -->
    <PackageReference Include="FlaUI.Core" Version="5.0.0" />
    <PackageReference Include="FlaUI.UIA3" Version="5.0.0" />

    <!-- xUnit -->
    <PackageReference Include="xunit" Version="2.9.3" />
    <PackageReference Include="xunit.runner.visualstudio" Version="2.9.3" />
    <PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.12.0" />
    <PackageReference Include="coverlet.collector" Version="6.0.4" />
  </ItemGroup>

  <!-- Copiar arquivos de TestData/ para output (fixtures de teste) -->
  <ItemGroup>
    <None Update="TestData\**\*">
      <CopyToOutputDirectory>PreserveNewest</CopyToOutputDirectory>
    </None>
  </ItemGroup>

  <!-- NÃO adicionar referência de projeto ao app WPF.
       Testes E2E interagem via UI, não via código. -->
</Project>
```

> **Importante:** Testes E2E não devem ter `ProjectReference` ao app WPF. Eles interagem com o executável compilado via UI Automation, simulando um usuário real.

### Passo 2: Adicionar AutomationIds ao XAML

Antes de escrever qualquer teste, cada controle interativo do XAML precisa de um `AutomationProperties.AutomationId`. Sem isso, testes ficam frágeis e quebram com qualquer mudança de layout.

→ Consulte `references/xaml-automation.md` para convenções de nomeação, exemplos com WPF-UI, e checklist de controles.

#### Regras rápidas

```xml
<!-- Botões -->
<Button AutomationProperties.AutomationId="BtnSaveLicense"
        Content="Salvar" Command="{Binding SalvarCommand}" />

<!-- TextBoxes -->
<ui:TextBox AutomationProperties.AutomationId="TxtCompanyName"
            Text="{Binding CompanyName, Mode=OneWay}" />

<!-- Labels/Status -->
<TextBlock AutomationProperties.AutomationId="LblStatusMessage"
           Text="{Binding StatusMessage}" />
```

**Convenção de nomeação:**
| Tipo | Prefixo | Exemplo |
|------|---------|---------|
| Button | `Btn` | `BtnSaveLicense` |
| TextBox | `Txt` | `TxtCompanyName` |
| ComboBox | `Cmb` | `CmbVdrModel` |
| CheckBox | `Chk` | `ChkIncludeEpirb` |
| DataGrid | `Dgr` | `DgrAlertList` |
| Label/TextBlock | `Lbl` | `LblStatusMessage` |
| Window | `Wnd` | `WndMainWindow` |

### Passo 3: Criar FlaUITestBase

A classe base gerencia o ciclo de vida da aplicação (launch/close) e fornece acesso à janela principal.

```csharp
using System.IO;
using FlaUI.Core;
using FlaUI.Core.AutomationElements;
using FlaUI.Core.Tools;
using FlaUI.UIA3;

namespace MyApp.E2ETests.Infrastructure;

public abstract class FlaUITestBase : IDisposable
{
    protected Application App { get; }
    protected UIA3Automation Automation { get; }
    protected Window MainWindow { get; }

    protected FlaUITestBase()
    {
        Automation = new UIA3Automation();

        var exePath = TestConstants.AppExePath;

        // Validar que o executável existe antes de tentar lançar
        if (!File.Exists(exePath))
        {
            throw new FileNotFoundException(
                $"Executável não encontrado em: {exePath}. " +
                "Build o projeto WPF em Debug antes de rodar testes E2E.");
        }

        App = Application.Launch(exePath);

        // Aguardar janela principal com retry (não use Thread.Sleep)
        var window = Retry.WhileNull(
            () => App.GetMainWindow(Automation),
            timeout: TimeSpan.FromSeconds(TestConstants.WindowTimeoutSeconds),
            interval: TimeSpan.FromMilliseconds(500)
        ).Result;

        MainWindow = window
            ?? throw new InvalidOperationException(
                $"Janela principal não encontrada após {TestConstants.WindowTimeoutSeconds}s");
    }

    /// <summary>
    /// Captura screenshot para diagnóstico em caso de falha.
    /// </summary>
    protected void CaptureScreenshot(string testName)
    {
        try
        {
            var dir = Path.Combine(TestConstants.ScreenshotDir, DateTime.Now.ToString("yyyy-MM-dd"));
            Directory.CreateDirectory(dir);
            var path = Path.Combine(dir, $"{testName}_{DateTime.Now:HHmmss}.png");

            FlaUI.Core.Capturing.Capture.Screen().ToFile(path);
        }
        catch
        {
            // Screenshot failure should not mask test failure
        }
    }

    public void Dispose()
    {
        App?.Close();
        Automation?.Dispose();
        GC.SuppressFinalize(this);
    }
}
```

```csharp
using System.IO;

namespace MyApp.E2ETests.Infrastructure;

public static class TestConstants
{
    // Ajustar para o caminho real do executável compilado
    public static string AppExePath => Path.GetFullPath(
        Path.Combine(AppContext.BaseDirectory,
            "..", "..", "..", "..", "MyApp", "bin", "Debug",
            "net10.0-windows7.0", "MyApp.exe"));

    public const int WindowTimeoutSeconds = 15;
    public const int ElementTimeoutMs = 5000;

    // Constantes de timing para file dialogs — valores ajustáveis por máquina/CI
    public const int DialogRenderDelayMs = 1000;
    public const int DialogFocusDelayMs = 500;
    public const int KeystrokeDelayMs = 100;
    public const int FieldActivationDelayMs = 300;
    public const int InputProcessingDelayMs = 500;
    public const int NavigationDelayMs = 1000;

    public static string ScreenshotDir => Path.Combine(
        AppContext.BaseDirectory, "screenshots");

    public static string TestDataDir => Path.Combine(
        AppContext.BaseDirectory, "TestData");
}
```

> **Nota:** Mesmo com `<ImplicitUsings>enable</ImplicitUsings>`, projetos WPF com `<UseWPF>true</UseWPF>` podem não incluir `System.IO` automaticamente. Sempre adicione `using System.IO;` explicitamente.

### Passo 4: Criar Page Objects

O Page Object Pattern centraliza seletores e ações da UI, tornando testes mais legíveis e resilientes a mudanças de layout.

→ Consulte `references/flaui-patterns.md` para padrões avançados, incluindo wait helpers, listas, e navegação.

```csharp
using FlaUI.Core.AutomationElements;
using FlaUI.Core.Tools;

namespace MyApp.E2ETests.Pages;

public class MainWindowPage(Window window)
{
    // ─── Elementos ───────────────────────────────────────────
    // Para controles WPF-UI read-only, use AutomationElement (não TextBox)
    // e leia o texto via GetText() — WPF-UI pode não expor .Text diretamente

    public AutomationElement CompanyNameTextBox => FindById("TxtCompanyName");
    public AutomationElement ProcessorIdTextBox => FindById("TxtProcessorId");
    public AutomationElement MotherboardSerialTextBox => FindById("TxtMotherboardSerial");
    public TextBox ExpirationDateTextBox => FindById("TxtExpirationDate").AsTextBox();
    public Button LoadHardwareButton => FindById("BtnLoadHardwareId").AsButton();
    public Button SaveLicenseButton => FindById("BtnSaveLicense").AsButton();
    public AutomationElement StatusMessage => FindById("LblStatusMessage");

    // ─── Ações ───────────────────────────────────────────────

    public bool IsSaveEnabled => SaveLicenseButton.IsEnabled;

    public string GetStatusText() => StatusMessage.Name ?? string.Empty;

    public void ClickLoadHardware() => LoadHardwareButton.Invoke();

    public void ClickSaveLicense() => SaveLicenseButton.Invoke();

    public void SetExpirationDate(string date) => ExpirationDateTextBox.Enter(date);

    // ─── GetText Helper ──────────────────────────────────────
    // Controles WPF-UI (ui:TextBox) podem não expor .Text via AsTextBox().
    // Esta abordagem tenta ValuePattern primeiro, que é o mais confiável.

    public static string GetText(AutomationElement element)
    {
        if (element.Patterns.Value.IsSupported)
        {
            return element.Patterns.Value.Pattern.Value.Value ?? string.Empty;
        }

        var textBox = element.AsTextBox();
        if (!string.IsNullOrEmpty(textBox.Text))
        {
            return textBox.Text;
        }

        return element.Name ?? string.Empty;
    }

    // ─── Internal ────────────────────────────────────────────
    // FindById usa Retry.WhileNull porque controles WPF-UI podem
    // demorar a aparecer na árvore de automação após a janela abrir.

    private AutomationElement FindById(string automationId)
    {
        var element = Retry.WhileNull(
            () => window.FindFirstDescendant(cf => cf.ByAutomationId(automationId)),
            timeout: TimeSpan.FromMilliseconds(TestConstants.ElementTimeoutMs),
            interval: TimeSpan.FromMilliseconds(200)
        ).Result;

        return element
            ?? throw new InvalidOperationException(
                $"Elemento '{automationId}' não encontrado após {TestConstants.ElementTimeoutMs}ms. " +
                "Verifique se AutomationProperties.AutomationId está definido no XAML.");
    }
}
```

### Passo 5: Escrever Smoke Tests

Smoke tests verificam que a UI renderiza corretamente e que os fluxos básicos funcionam. Mantenha poucos — 2-3 por tela.

```csharp
using MyApp.E2ETests.Infrastructure;
using MyApp.E2ETests.Pages;
using Xunit;

// Testes E2E abrem janelas reais — rodar em paralelo causa conflitos
[assembly: CollectionBehavior(DisableTestParallelization = true)]

namespace MyApp.E2ETests.Tests;

[Trait("Category", "E2E")]
public class MainWindowTests : FlaUITestBase
{
    [Fact]
    public void JanelaPrincipal_DeveAbrirComTituloCorreto()
    {
        Assert.NotNull(MainWindow);
        // Use o título real da janela (pode ser português, inglês, etc.)
        Assert.Contains("Licenças", MainWindow.Title);
    }

    [Fact]
    public void BotaoSalvar_DeveEstarDesabilitadoNoInicio()
    {
        // Arrange
        var page = new MainWindowPage(MainWindow);

        // Assert
        Assert.False(page.IsSaveEnabled);
    }

    [Fact]
    public void CamposHardware_DevemEstarVaziosNoInicio()
    {
        // Arrange
        var page = new MainWindowPage(MainWindow);

        // Assert — use GetText() para controles WPF-UI
        Assert.Empty(MainWindowPage.GetText(page.CompanyNameTextBox));
        Assert.Empty(MainWindowPage.GetText(page.ProcessorIdTextBox));
        Assert.Empty(MainWindowPage.GetText(page.MotherboardSerialTextBox));
    }
}
```

#### Cuidado com linters e auto-formatters

Testes E2E têm fluxos complexos (Arrange → Act com dialog → Assert) que podem ser quebrados por linters ou auto-formatters que reorganizam código sem entender a lógica. Uma linter pode remover uma chamada de helper (como `LoadHardwareId()`) por achar que é "código morto" ou substituir strings hardcoded por `CultureInfo.CurrentCulture`. Isso quebra silenciosamente o teste.

Recomendações:
- Use formato de data **fixo** (`"31/12/2027"`) em vez de `CultureInfo.CurrentCulture` — o ViewModel espera `dd/MM/yyyy` explícito
- Após qualquer modificação automática, verifique que o Act section ainda contém a ação correta
- Considere adicionar comentário `// DO NOT REMOVE — core test action` em chamadas críticas de helpers

#### Extraindo helpers para reduzir duplicação

Quando múltiplos testes compartilham fluxos (ex: carregar arquivo, preencher campos, salvar), extraia métodos helpers privados na classe de teste. Isso centraliza screenshot on failure e evita copiar/colar blocos de 20+ linhas entre testes:

```csharp
// Helper reutilizado por todos os testes que carregam .hid
private void LoadHardwareId(MainWindowPage page)
{
    var hidPath = Path.GetFullPath(TestConstants.SampleHidPath);
    try
    {
        page.ClickLoadHardware();
        FileDialogHelper.SelectFile(MainWindow, hidPath);
    }
    catch (Exception ex)
    {
        CaptureScreenshot("LoadHardwareId_Error");
        throw new InvalidOperationException($"Dialog falhou: {ex.Message}", ex);
    }
    Retry.WhileTrue(
        () => string.IsNullOrEmpty(MainWindowPage.GetText(page.CompanyNameTextBox)),
        timeout: TimeSpan.FromSeconds(10));
}
```

### Passo 6: Lidar com File Dialogs

File dialogs (`OpenFileDialog`, `SaveFileDialog`) são janelas Win32 fora da árvore visual WPF. Existem duas estratégias:

#### Estratégia A: Abstrair com IFileDialogService (Recomendado)

A melhor abordagem para testabilidade é abstrair dialogs atrás de uma interface, permitindo substituição por fake em testes.

```csharp
// Interface
public interface IFileDialogService
{
    string? OpenFile(string filter);
    string? SaveFile(string filter, string defaultFileName);
}

// Produção
public class WpfFileDialogService : IFileDialogService
{
    public string? OpenFile(string filter)
    {
        var dlg = new Microsoft.Win32.OpenFileDialog { Filter = filter };
        return dlg.ShowDialog() == true ? dlg.FileName : null;
    }

    public string? SaveFile(string filter, string defaultFileName)
    {
        var dlg = new Microsoft.Win32.SaveFileDialog
        {
            Filter = filter,
            FileName = defaultFileName
        };
        return dlg.ShowDialog() == true ? dlg.FileName : null;
    }
}
```

No ViewModel, injete `IFileDialogService` e separe a lógica testável do dialog:

```csharp
public partial class MainWindowViewModel(
    LicenseService licenseService,
    IFileDialogService fileDialog) : ObservableObject
{
    [RelayCommand]
    private void CarregarHardwareId()
    {
        var path = fileDialog.OpenFile("Hardware ID|*.hid");
        if (path is not null)
        {
            PopularCampos(licenseService.RecuperarDeArquivo(path));
        }
    }

    // Método testável separado — sem dependência de dialog
    public void PopularCampos(HardwareInfo info) { /* ... */ }
}
```

#### Estratégia B: Automatizar o Dialog Diretamente

Para testes E2E reais que precisam testar o fluxo completo incluindo o dialog, automatize o dialog Win32 via FlaUI. A automação de file dialogs é significativamente mais complexa do que parece — requer múltiplas estratégias de fallback e waits explícitos porque o dialog Win32 varia entre versões do Windows e localizações.

```csharp
using System.IO;
using System.Threading;
using FlaUI.Core.AutomationElements;
using FlaUI.Core.Input;
using FlaUI.Core.Tools;
using FlaUI.Core.WindowsAPI;

namespace MyApp.E2ETests.Infrastructure;

public static class FileDialogHelper
{
    public static void SelectFile(Window parentWindow, string filePath,
        int timeoutMs = TestConstants.ElementTimeoutMs)
    {
        if (!File.Exists(filePath))
        {
            throw new FileNotFoundException($"Arquivo não existe: {filePath}");
        }

        InteractWithDialog(parentWindow, filePath, timeoutMs);
    }

    public static void SaveFile(Window parentWindow, string filePath,
        int timeoutMs = TestConstants.ElementTimeoutMs)
    {
        var dir = Path.GetDirectoryName(filePath);
        if (dir is not null) { Directory.CreateDirectory(dir); }

        InteractWithDialog(parentWindow, filePath, timeoutMs);
    }

    private static void InteractWithDialog(Window parentWindow, string filePath,
        int timeoutMs)
    {
        // 1. Esperar o dialog modal aparecer
        var dialog = Retry.WhileNull(
            () => parentWindow.ModalWindows.FirstOrDefault(),
            timeout: TimeSpan.FromMilliseconds(timeoutMs),
            interval: TimeSpan.FromMilliseconds(300)
        ).Result ?? throw new TimeoutException(
            $"File dialog não apareceu após {timeoutMs}ms");

        // 2. Esperar dialog renderizar completamente
        //    Thread.Sleep é necessário aqui — Retry não resolve porque o dialog
        //    aparece na árvore antes dos controles internos estarem prontos
        Thread.Sleep(TestConstants.DialogRenderDelayMs);
        dialog.SetForeground();
        Thread.Sleep(TestConstants.DialogFocusDelayMs);

        // 3. Encontrar campo filename (AutomationId "1148" no Win10/11)
        var fileNameEdit = dialog.FindFirstDescendant(
            cf => cf.ByAutomationId("1148"));

        if (fileNameEdit is not null)
        {
            // Click → Ctrl+A → Delete → Type caminho completo
            fileNameEdit.Click();
            Thread.Sleep(TestConstants.FieldActivationDelayMs);
            Keyboard.TypeSimultaneously(VirtualKeyShort.CONTROL, VirtualKeyShort.KEY_A);
            Thread.Sleep(TestConstants.KeystrokeDelayMs);
            Keyboard.Press(VirtualKeyShort.DELETE);
            Thread.Sleep(TestConstants.KeystrokeDelayMs);
            Keyboard.Type(filePath);
            Thread.Sleep(TestConstants.InputProcessingDelayMs);
        }
        else
        {
            // Fallback: Alt+D foca a barra de endereço, Alt+N foca filename
            Keyboard.TypeSimultaneously(VirtualKeyShort.ALT, VirtualKeyShort.KEY_D);
            Thread.Sleep(TestConstants.InputProcessingDelayMs);
            Keyboard.Type(Path.GetDirectoryName(filePath) ?? filePath);
            Thread.Sleep(TestConstants.FieldActivationDelayMs);
            Keyboard.Press(VirtualKeyShort.ENTER);
            Thread.Sleep(TestConstants.NavigationDelayMs);
            Keyboard.TypeSimultaneously(VirtualKeyShort.ALT, VirtualKeyShort.KEY_N);
            Thread.Sleep(TestConstants.FieldActivationDelayMs);
            Keyboard.Type(Path.GetFileName(filePath));
            Thread.Sleep(TestConstants.FieldActivationDelayMs);
        }

        // 4. Confirmar — tentar botão por AutomationId, por nome, ou Enter
        var confirmBtn = dialog.FindFirstDescendant(
            cf => cf.ByAutomationId("1"))?.AsButton();
        if (confirmBtn is not null)
        {
            confirmBtn.Invoke();
        }
        else
        {
            var namedBtn = dialog.FindFirstDescendant(
                cf => cf.ByName("Abrir"))?.AsButton()
                ?? dialog.FindFirstDescendant(cf => cf.ByName("Open"))?.AsButton()
                ?? dialog.FindFirstDescendant(cf => cf.ByName("Salvar"))?.AsButton();
            if (namedBtn is not null) { namedBtn.Invoke(); }
            else { Keyboard.Press(VirtualKeyShort.ENTER); }
        }

        // 5. Esperar dialog fechar
        Retry.WhileTrue(
            () => parentWindow.ModalWindows.Length > 0,
            timeout: TimeSpan.FromMilliseconds(timeoutMs + 5000),
            interval: TimeSpan.FromMilliseconds(500));
    }
}
```

> **Sobre Thread.Sleep em file dialogs:** Embora a orientação geral seja evitar `Thread.Sleep()`, dialogs Win32 são uma exceção legítima. O dialog aparece na árvore de automação antes dos controles internos estarem prontos para interação. Os sleeps entre operações de teclado garantem que cada keystroke é processado antes do próximo. Sem eles, a automação é instável.

### Passo 7: Configurar CI/CD

Testes FlaUI precisam de sessão interativa do Windows (desktop visível). Não funcionam em containers Linux nem em runners headless.

→ Consulte `references/ci-cd-setup.md` para configuração detalhada de GitHub Actions, Azure DevOps, e runners self-hosted.

#### Resumo rápido

```bash
# Rodar apenas testes unitários (CI padrão — funciona em qualquer runner)
dotnet test --filter "Category!=E2E"

# Rodar apenas testes E2E (requer runner com desktop interativo)
dotnet test --filter "Category=E2E"
```

## Checklist de Implementação

Ao criar testes E2E para uma tela WPF, siga este checklist:

- [ ] Criar projeto `*.E2ETests.csproj` com FlaUI.UIA3 e xUnit
- [ ] Adicionar `AutomationProperties.AutomationId` em todos os controles interativos do XAML
- [ ] Criar `FlaUITestBase` com launch/dispose do app
- [ ] Criar `TestConstants` com caminho do executável e timeouts
- [ ] Criar Page Object para a tela (um por janela/tela)
- [ ] Escrever 2-3 smoke tests por tela (estado inicial, fluxo principal)
- [ ] Marcar testes com `[Trait("Category", "E2E")]`
- [ ] Desabilitar paralelização: `[assembly: CollectionBehavior(DisableTestParallelization = true)]`
- [ ] Abstrair file dialogs com `IFileDialogService` se necessário
- [ ] Extrair helpers para fluxos reutilizados entre testes (ex: `LoadHardwareId()`)
- [ ] Configurar screenshot on failure para diagnóstico
- [ ] Separar execução E2E no CI com `--filter "Category=E2E"`

## Referências Detalhadas

| Arquivo | Conteúdo | Quando consultar |
|---------|----------|------------------|
| `references/flaui-patterns.md` | Padrões avançados FlaUI, wait strategies, DataGrid, navegação | Ao criar Page Objects complexos ou lidar com controles específicos |
| `references/xaml-automation.md` | Setup de AutomationId, WPF-UI specifics, AutomationPeer | Ao preparar XAML para testes, especialmente com controles WPF-UI |
| `references/ci-cd-setup.md` | GitHub Actions, Azure DevOps, runners self-hosted | Ao configurar pipeline de CI/CD para testes E2E |
