# FlaUI Patterns — Referência Avançada

## Índice
1. [Busca de Elementos](#busca-de-elementos)
2. [Wait e Retry](#wait-e-retry)
3. [Interação com Controles](#interação-com-controles)
4. [Page Object Avançado](#page-object-avançado)
5. [DataGrid e Listas](#datagrid-e-listas)
6. [Screenshot e Diagnóstico](#screenshot-e-diagnóstico)

---

## Busca de Elementos

### Por AutomationId (preferido)
```csharp
var btn = window.FindFirstDescendant(cf => cf.ByAutomationId("BtnSave"))?.AsButton();
```

### Por Nome/Texto
```csharp
var label = window.FindFirstDescendant(cf => cf.ByName("Status"));
```

### Por Tipo de Controle
```csharp
var allButtons = window.FindAllDescendants(cf => cf.ByControlType(ControlType.Button));
```

### Condições combinadas
```csharp
var okBtn = window.FindFirstDescendant(
    new AndCondition(
        window.ConditionFactory.ByControlType(ControlType.Button),
        window.ConditionFactory.ByName("OK")
    )
);
```

### Substring match
```csharp
var element = window.FindFirstDescendant(
    window.ConditionFactory.ByName("Salvar", PropertyConditionFlags.MatchSubstring)
);
```

### Busca por framework
```csharp
var wpfElements = window.FindAllDescendants(cf => cf.ByFrameworkType(FrameworkType.Wpf));
```

---

## Wait e Retry

FlaUI fornece a classe `Retry` para esperas — **nunca use `Thread.Sleep()`**.

### WhileNull — esperar elemento aparecer
```csharp
var result = Retry.WhileNull(
    () => window.FindFirstDescendant(cf => cf.ByAutomationId("PnlDashboard")),
    timeout: TimeSpan.FromSeconds(5),
    interval: TimeSpan.FromMilliseconds(200)
);
var panel = result.Result; // null se timeout
```

### WhileTrue — esperar condição mudar
```csharp
Retry.WhileTrue(
    () => element.IsOffscreen,
    timeout: TimeSpan.FromSeconds(5)
);
```

### WhileException — retry em exceções transitórias
```csharp
Retry.WhileException(
    () => element.Click(),
    timeout: TimeSpan.FromSeconds(3),
    ignoreException: true
);
```

### Defaults globais
```csharp
// Configurar uma vez no setup
Retry.DefaultTimeout = TimeSpan.FromSeconds(5);
Retry.DefaultInterval = TimeSpan.FromMilliseconds(200);
```

### Outros padrões de espera
```csharp
// Esperar fila de input drenar
automation.Wait.UntilInputIsProcessed();

// Esperar app processar
app.WaitWhileBusy();
```

---

## Interação com Controles

### TextBox
```csharp
var textBox = element.AsTextBox();
textBox.Enter("texto");          // Limpa e digita
textBox.Text;                    // Lê valor atual
```

### Button
```csharp
var button = element.AsButton();
button.Invoke();                 // Clica
button.IsEnabled;                // Verifica estado
```

### ComboBox
```csharp
var combo = element.AsComboBox();
combo.Select("Opção 1");        // Seleciona por texto
combo.Select(0);                 // Seleciona por índice
combo.SelectedItem.Text;         // Lê seleção atual
```

### CheckBox
```csharp
var check = element.AsCheckBox();
check.IsChecked;                 // Estado atual
check.Toggle();                  // Alterna
```

### RadioButton
```csharp
var radio = element.AsRadioButton();
radio.IsChecked;                 // Estado atual
radio.Click();                   // Seleciona
```

---

## Page Object Avançado

### Base para Page Objects com helpers comuns

**Lição aprendida:** `FindById` deve usar `Retry.WhileNull` por padrão, não busca imediata. Controles WPF-UI podem demorar a aparecer na árvore de automação mesmo após a janela estar visível. Um find imediato causa falhas intermitentes.

```csharp
public abstract class PageBase(Window window)
{
    protected Window Window { get; } = window;

    // FindById usa Retry porque controles WPF-UI podem demorar a renderizar
    protected AutomationElement FindById(string automationId, int timeoutMs = 5000)
    {
        var element = Retry.WhileNull(
            () => Window.FindFirstDescendant(cf => cf.ByAutomationId(automationId)),
            timeout: TimeSpan.FromMilliseconds(timeoutMs),
            interval: TimeSpan.FromMilliseconds(200)
        ).Result;

        return element
            ?? throw new InvalidOperationException(
                $"Elemento '{automationId}' não encontrado após {timeoutMs}ms. " +
                "Verifique se AutomationProperties.AutomationId está no XAML.");
    }

    protected AutomationElement? TryFindById(string automationId)
    {
        return Window.FindFirstDescendant(cf => cf.ByAutomationId(automationId));
    }

    protected AutomationElement WaitForElement(string automationId,
        int timeoutMs = 5000)
    {
        return FindById(automationId, timeoutMs); // FindById já faz retry
    }

    protected void WaitForEnabled(AutomationElement element,
        int timeoutMs = 5000)
    {
        Retry.WhileTrue(
            () => !element.IsEnabled,
            timeout: TimeSpan.FromMilliseconds(timeoutMs)
        );
    }

    /// <summary>
    /// Lê texto de controles WPF-UI que podem não expor .Text via AsTextBox().
    /// Consulte references/xaml-automation.md para detalhes.
    /// </summary>
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
}
```

### Page Object com navegação
```csharp
public class NavigationPage(Window window) : PageBase(window)
{
    public void NavigateTo(string menuItemId)
    {
        var menuItem = FindById(menuItemId);
        menuItem.Click();

        // Aguardar conteúdo carregar
        WaitForElement("PnlContent");
    }

    public TPage NavigateTo<TPage>(string menuItemId)
        where TPage : PageBase
    {
        NavigateTo(menuItemId);
        return (TPage)Activator.CreateInstance(typeof(TPage), Window)!;
    }
}
```

---

## DataGrid e Listas

### Lendo dados de um DataGrid
```csharp
var grid = window.FindFirstDescendant(
    cf => cf.ByAutomationId("DgrAlerts"))?.AsDataGridView();

if (grid is not null)
{
    // Número de linhas
    var rowCount = grid.Rows.Length;

    // Ler célula específica (linha 0, coluna 1)
    var cellValue = grid.Rows[0].Cells[1].Value;

    // Iterar todas as linhas
    foreach (var row in grid.Rows)
    {
        var name = row.Cells[0].Value;
        var status = row.Cells[1].Value;
    }
}
```

### Lendo items de uma ListView
```csharp
var list = window.FindFirstDescendant(
    cf => cf.ByAutomationId("LstItems"))?.AsListBox();

if (list is not null)
{
    var items = list.Items;
    var selectedItem = list.SelectedItem;
    list.Items[2].Select();
}
```

---

## Screenshot e Diagnóstico

### Captura de tela completa
```csharp
var screenshot = FlaUI.Core.Capturing.Capture.Screen();
screenshot.ToFile("screenshot.png");
```

### Captura apenas da janela
```csharp
var windowCapture = FlaUI.Core.Capturing.Capture.Element(window);
windowCapture.ToFile("window.png");
```

### Captura de elemento específico
```csharp
var elementCapture = FlaUI.Core.Capturing.Capture.Element(button);
elementCapture.ToFile("button.png");
```

### Padrão: capturar screenshot em caso de falha
```csharp
public abstract class FlaUITestBase : IDisposable
{
    // ... campos e construtor ...

    protected void RunWithScreenshot(string testName, Action testAction)
    {
        try
        {
            testAction();
        }
        catch
        {
            CaptureScreenshot(testName);
            throw;
        }
    }

    protected void CaptureScreenshot(string testName)
    {
        try
        {
            var dir = Path.Combine(
                AppContext.BaseDirectory, "screenshots",
                DateTime.Now.ToString("yyyy-MM-dd"));
            Directory.CreateDirectory(dir);

            var path = Path.Combine(dir,
                $"{testName}_{DateTime.Now:HHmmss}.png");

            FlaUI.Core.Capturing.Capture.Screen().ToFile(path);
        }
        catch
        {
            // Screenshot failure should not mask test failure
        }
    }
}
```

---

## FlaUInspect

O **FlaUInspect** é uma ferramenta GUI para explorar a árvore de automação de qualquer aplicação Windows. Use para:

- Descobrir AutomationIds, Names e ControlTypes expostos
- Verificar se controles WPF-UI expõem propriedades de automação
- Debugar por que um seletor não encontra um elemento

Baixe em: [FlaUI GitHub Releases](https://github.com/FlaUI/FlaUI/releases) — procure por `FlaUInspect`.
