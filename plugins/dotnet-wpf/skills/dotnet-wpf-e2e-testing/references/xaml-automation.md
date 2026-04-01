# XAML Automation Setup — AutomationId e WPF-UI

## Índice
1. [AutomationProperties.AutomationId](#automationid)
2. [Convenções de Nomeação](#convenções-de-nomeação)
3. [WPF-UI (Fluent) Specifics](#wpf-ui-specifics)
4. [Custom AutomationPeer](#custom-automationpeer)
5. [Checklist por Tipo de Controle](#checklist)

---

## AutomationId

`AutomationProperties.AutomationId` é a forma mais confiável de identificar controles em testes automatizados. Diferente de `x:Name` (que é para binding no code-behind), AutomationId é exposto pela UI Automation API e é imune a mudanças de layout, texto ou localização.

### Sintaxe básica
```xml
<Button AutomationProperties.AutomationId="BtnSaveLicense"
        Content="Salvar Licença"
        Command="{Binding SalvarLicencaCommand}" />
```

### Diferenças entre x:Name e AutomationId

| Aspecto | `x:Name` | `AutomationProperties.AutomationId` |
|---------|----------|--------------------------------------|
| Propósito | Code-behind / binding | UI Automation / testes |
| Visível para FlaUI | Às vezes (não confiável) | Sempre |
| Convenção | camelCase | PascalCase com prefixo |
| Quando usar | Quando precisa acessar no .cs | Sempre que o controle será testado |

Ambos podem coexistir no mesmo elemento:
```xml
<TextBox x:Name="txtCompany"
         AutomationProperties.AutomationId="TxtCompanyName"
         Text="{Binding CompanyName}" />
```

---

## Convenções de Nomeação

Use prefixos consistentes baseados no tipo do controle:

| Tipo WPF | Prefixo | Exemplo |
|----------|---------|---------|
| `Button` | `Btn` | `BtnSaveLicense`, `BtnLoadHardwareId` |
| `TextBox` | `Txt` | `TxtCompanyName`, `TxtProcessorId` |
| `TextBlock` | `Lbl` | `LblStatusMessage`, `LblVersion` |
| `ComboBox` | `Cmb` | `CmbVdrModel`, `CmbAlertType` |
| `CheckBox` | `Chk` | `ChkIncludeEpirb`, `ChkAutoUpdate` |
| `RadioButton` | `Rdo` | `RdoEngineerMode`, `RdoCoCMode` |
| `DataGrid` | `Dgr` | `DgrAlertList`, `DgrChannels` |
| `ListView` | `Lst` | `LstSensors`, `LstLogs` |
| `TabControl` | `Tab` | `TabMainNavigation` |
| `TabItem` | `Tbi` | `TbiOverview`, `TbiDetails` |
| `Menu` | `Mnu` | `MnuFile`, `MnuEdit` |
| `MenuItem` | `Mni` | `MniOpen`, `MniSave` |
| `ProgressBar` | `Prg` | `PrgLoading` |
| `Slider` | `Sld` | `SldVolume` |
| `ToggleSwitch` | `Tgl` | `TglDarkMode` |
| `Window` | `Wnd` | `WndMainWindow` |
| `Border/Panel` | `Pnl` | `PnlHardwareInfo`, `PnlActions` |

### Formato: `{Prefixo}{Descrição}`
- Descrição em PascalCase, descrevendo o propósito do controle
- Em inglês para consistência com código
- Sufixos opcionais: `_Header`, `_Footer` para variantes

---

## WPF-UI Specifics

O WPF-UI (lepoco/wpfui) usa controles custom que substituem os padrão do WPF. A boa notícia é que `AutomationProperties.AutomationId` funciona em todos eles.

### Controles WPF-UI com AutomationId

```xml
<!-- ui:Button (herda de WPF Button) -->
<ui:Button AutomationProperties.AutomationId="BtnPrimary"
           Appearance="Primary"
           Content="Salvar"
           Command="{Binding SaveCommand}" />

<!-- ui:TextBox (custom control) -->
<ui:TextBox AutomationProperties.AutomationId="TxtSearch"
            PlaceholderText="Buscar..."
            Text="{Binding SearchQuery}" />

<!-- ui:NavigationView -->
<ui:NavigationView AutomationProperties.AutomationId="NavMain">
    <ui:NavigationView.MenuItems>
        <ui:NavigationViewItem AutomationProperties.AutomationId="NavOverview"
                               Content="Visão Geral"
                               Icon="{ui:SymbolIcon Home24}" />
    </ui:NavigationView.MenuItems>
</ui:NavigationView>

<!-- ui:CardControl -->
<ui:CardControl AutomationProperties.AutomationId="CrdLicenseInfo"
                Header="Informações da Licença" />

<!-- ui:ToggleSwitch -->
<ui:ToggleSwitch AutomationProperties.AutomationId="TglAutoUpdate"
                  Content="Atualização automática"
                  IsChecked="{Binding AutoUpdate}" />

<!-- FluentWindow -->
<ui:FluentWindow AutomationProperties.AutomationId="WndMain"
                  Title="Meu App">
    <!-- conteúdo -->
</ui:FluentWindow>
```

### WPF-UI TextBox — Leitura de Texto via ValuePattern

Controles `ui:TextBox` do WPF-UI podem não expor a propriedade `.Text` corretamente via `AsTextBox().Text` do FlaUI. Isso acontece porque o WPF-UI implementa controles custom que nem sempre surfaçam o texto pela interface padrão de TextBox.

**Solução: usar ValuePattern como abordagem primária:**

```csharp
/// <summary>
/// Lê texto de controles WPF-UI que podem não expor .Text diretamente.
/// Tenta ValuePattern → AsTextBox().Text → Name, nesta ordem.
/// </summary>
public static string GetText(AutomationElement element)
{
    // ValuePattern é o mais confiável para controles WPF-UI
    if (element.Patterns.Value.IsSupported)
    {
        return element.Patterns.Value.Pattern.Value.Value ?? string.Empty;
    }

    // Fallback para TextBox padrão
    var textBox = element.AsTextBox();
    if (!string.IsNullOrEmpty(textBox.Text))
    {
        return textBox.Text;
    }

    // Último recurso: propriedade Name da automação
    return element.Name ?? string.Empty;
}
```

**Impacto no Page Object:** Para propriedades de leitura (read-only) em controles `ui:TextBox`, declare como `AutomationElement` (não `TextBox`) e use o helper `GetText()`:

```csharp
// Em vez de:
public TextBox CompanyNameTextBox => FindById("TxtCompanyName").AsTextBox();
Assert.Empty(page.CompanyNameTextBox.Text);  // Pode falhar com WPF-UI!

// Use:
public AutomationElement CompanyNameTextBox => FindById("TxtCompanyName");
Assert.Empty(MainWindowPage.GetText(page.CompanyNameTextBox));  // Funciona sempre
```

Para campos de entrada (editáveis) como data de expiração, `AsTextBox().Enter()` funciona normalmente — o problema é apenas na **leitura** do valor.

### TitleBar — Caso especial

O `ui:TitleBar` do WPF-UI substitui a barra de título do Windows. Para testes, é mais confiável verificar o título via `Window.Title` do FlaUI do que tentar encontrar elementos dentro do TitleBar.

```csharp
// Em vez de buscar TitleBar no XAML:
Assert.Contains("Licence Manager", mainWindow.Title);
```

### Controles que podem não expor automação

Se um controle WPF-UI custom não aparece no FlaUInspect:

1. Adicione `AutomationProperties.AutomationId` — geralmente resolve
2. Adicione `AutomationProperties.Name` para dar um nome legível
3. Se necessário, implemente um `AutomationPeer` custom (seção abaixo)

---

## Custom AutomationPeer

Raramente necessário, mas útil quando um controle custom não expõe automação adequada.

```csharp
using System.Windows.Automation.Peers;

public class CustomCardAutomationPeer(CustomCard owner)
    : FrameworkElementAutomationPeer(owner)
{
    protected override string GetClassNameCore() => "CustomCard";

    protected override AutomationControlType GetAutomationControlTypeCore()
        => AutomationControlType.Group;

    protected override string GetNameCore()
        => ((CustomCard)Owner).Header?.ToString() ?? base.GetNameCore();
}

// No controle custom:
public class CustomCard : Control
{
    protected override AutomationPeer OnCreateAutomationPeer()
        => new CustomCardAutomationPeer(this);
}
```

### Quando criar AutomationPeer

- Controle custom que não aparece no FlaUInspect
- Controle que aparece mas com ControlType errado (ex: Group em vez de Button)
- Controle que não expõe patterns necessários (IInvokeProvider, IValueProvider)

### Quando NÃO criar AutomationPeer

- `AutomationProperties.AutomationId` já resolve o problema
- O controle é de terceiro (WPF-UI) e já funciona com FlaUI
- É apenas um container de layout (Grid, StackPanel)

---

## Checklist

Ao preparar uma tela XAML para testes E2E, adicione AutomationId nos seguintes controles:

### Sempre adicionar
- [ ] Todos os `Button` (incluindo `ui:Button`)
- [ ] Todos os `TextBox` / `ui:TextBox` interativos
- [ ] Labels/TextBlocks que mostram status ou resultados
- [ ] `ComboBox` com seleção do usuário
- [ ] `CheckBox` / `ToggleSwitch`
- [ ] `DataGrid` / `ListView` com dados

### Adicionar se necessário
- [ ] Containers (Border, Grid) que serão verificados por visibilidade
- [ ] `TabControl` e `TabItem` para navegação
- [ ] `NavigationView` e items
- [ ] `ProgressBar` para verificar loading state

### Geralmente não precisa
- Elementos puramente decorativos (linhas, separadores, ícones estáticos)
- Grid/StackPanel de layout interno
- Resources e Styles
