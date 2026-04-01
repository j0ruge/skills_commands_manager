---
name: dotnet-wpf-mvvm
description: >
  Guia completo para migrar projetos WinForms para WPF com MVVM usando CommunityToolkit.Mvvm
  e WPF-UI. Cria ViewModels, configura DataBinding, Commands, navegacao e DI. Use quando o
  usuario quiser: migrar WinForms para WPF; adicionar MVVM a projeto WPF existente; criar
  ViewModel para uma tela; configurar navegacao WPF-UI com MVVM; substituir code-behind por
  bindings e commands; configurar DI com Microsoft.Extensions.Hosting em WPF; usar
  CommunityToolkit.Mvvm (ObservableProperty, RelayCommand); criar ObservableCollection para
  listas; implementar Messenger para comunicacao entre ViewModels. Tambem use quando o usuario
  mencionar "MVVM", "ViewModel", "data binding WPF", "migrar WinForms", "code-behind para
  commands", ou "navegacao WPF". NAO use para: setup inicial de projeto .NET (use
  dotnet-desktop-setup), testes unitarios, deploy, CI/CD, projetos web/API/mobile, ou
  configuracao de .editorconfig/CLAUDE.md.
---

# dotnet-wpf-mvvm

Skill para migrar projetos WinForms para WPF com MVVM e para construir novas telas WPF
seguindo o padrao MVVM moderno com CommunityToolkit.Mvvm + WPF-UI.

Usa **progressive disclosure** — este arquivo contem o workflow e decisoes. Templates,
exemplos de codigo e guias detalhados ficam em `references/` e sao lidos sob demanda.

---

## Stack Recomendada

| Componente | Pacote NuGet | Funcao |
|-----------|-------------|--------|
| MVVM Framework | `CommunityToolkit.Mvvm` | ObservableObject, source generators |
| DI + Lifecycle | `Microsoft.Extensions.Hosting` | IHost, IServiceProvider |
| UI Framework | `WPF-UI` (Wpf.Ui) | Fluent Design, NavigationView, Theming |
| Navegacao | Wpf.Ui.INavigationService | MVVM-friendly page navigation |
| Dialogs | Wpf.Ui.IContentDialogService | Substitui MessageBox |

---

## Quando usar

- Migrar um Form WinForms para WPF com MVVM
- Adicionar MVVM a projeto WPF que usa code-behind
- Criar nova tela/pagina WPF com ViewModel
- Configurar navegacao entre paginas com DI
- Substituir event handlers por Commands
- Configurar DI em App.xaml.cs

---

## Pre-requisitos

Antes de aplicar MVVM, o projeto deve ter:

1. **Services desacoplados** — logica de negocio em classes `*Service.cs`, nao em Forms/code-behind
2. **Sem MessageBox em services** — services retornam `Result<T>` ou lancam excecoes
3. **Target framework .NET 8+** — source generators exigem .NET moderno

Se o projeto nao atende esses requisitos, use a skill `dotnet-desktop-setup` primeiro para
desacoplar e configurar. O MVVM funciona melhor quando os services ja existem — o ViewModel
simplesmente orquestra chamadas aos services e expoe dados para a View.

---

## Workflow: 6 Passos

Execute os passos em ordem. Cada passo verifica o estado atual antes de agir.

### Passo 1: Diagnostico do Estado Atual

Avalie o projeto para entender o ponto de partida:

```bash
# Verificar framework UI
grep -r "UseWPF\|UseWindowsForms" *.csproj

# Verificar se CommunityToolkit.Mvvm ja esta instalado
grep -r "CommunityToolkit.Mvvm" *.csproj

# Contar event handlers no code-behind (quanto trabalho tem pela frente)
grep -rn "_Click\|_Changed\|_Loaded\|_SelectionChanged" *.xaml.cs *.cs

# Verificar services existentes
find . -name "*Service.cs" -type f

# Verificar se tem MessageBox em services (anti-padrao)
grep -rn "MessageBox" --include="*Service.cs"
```

Apresente o relatorio ao usuario:
- "Projeto X: WPF com WPF-UI, **sem MVVM**. 5 event handlers para migrar. 2 services existentes."
- "Pre-requisitos: OK" ou "Pre-requisitos: MessageBox encontrado em LicenseService.cs — desacoplar primeiro"

### Passo 2: Instalar Pacotes

Adicione os pacotes necessarios via `dotnet add`:

```bash
dotnet add <projeto>.csproj package CommunityToolkit.Mvvm
dotnet add <projeto>.csproj package Microsoft.Extensions.Hosting
```

Se WPF-UI nao estiver instalado:
```bash
dotnet add <projeto>.csproj package WPF-UI
```

Verifique que o `.csproj` tem:
```xml
<UseWPF>true</UseWPF>
```

### Passo 3: Configurar App.xaml.cs como Composition Root

Leia `references/wpfui-integration.md` para o template completo de App.xaml.cs.

O App.xaml.cs deve:
1. Criar `IHost` com `Host.CreateDefaultBuilder()`
2. Registrar **todos** os services no DI container
3. Registrar **todos** os ViewModels (Transient)
4. Registrar **todas** as Pages/Windows (Transient)
5. Registrar services WPF-UI: INavigationService, IContentDialogService, IThemeService
6. Iniciar o host em `OnStartup`, parar em `OnExit`

Padrao de registro:
```csharp
// Services de negocio
services.AddSingleton<ILicenseService, LicenseService>();

// ViewModels
services.AddTransient<MainWindowViewModel>();

// Windows/Pages
services.AddTransient<MainWindow>();
```

Para apps simples (1 janela, sem navegacao entre paginas), o registro minimo e:
- MainWindow + MainWindowViewModel
- Services de negocio
- Nao precisa de INavigationService/IPageService

### Passo 4: Criar ViewModels

Leia `references/communitytoolkit-patterns.md` para patterns detalhados.

Para cada tela, crie um ViewModel seguindo este template:

```csharp
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace MeuProjeto.ViewModels;

public partial class MainWindowViewModel : ObservableObject
{
    private readonly IMyService _service;

    // Propriedades observaveis — o source generator cria a propriedade publica
    [ObservableProperty]
    private string _titulo;

    [ObservableProperty]
    private bool _isProcessando;

    // Injecao de dependencia via construtor
    public MainWindowViewModel(IMyService service)
    {
        _service = service;
    }

    // Commands — o source generator cria TituloCommand (IRelayCommand)
    [RelayCommand]
    private async Task CarregarDadosAsync()
    {
        IsProcessando = true;
        try
        {
            var dados = await _service.ObterDadosAsync();
            Titulo = dados.Nome;
        }
        finally
        {
            IsProcessando = false;
        }
    }
}
```

**Regras criticas:**
- A classe DEVE ser `partial` — source generators precisam disso
- Campos `[ObservableProperty]` DEVEM ser `private` — `_name` gera propriedade `Name`
- Metodos `[RelayCommand]` geram propriedade com sufixo `Command` — `Salvar()` gera `SalvarCommand`
- Metodos async geram `IAsyncRelayCommand` com cancelamento automatico

### Passo 5: Refatorar Views (XAML)

Substitua event handlers por bindings e commands:

**Antes (code-behind):**
```xml
<Button Content="Carregar" Click="BtnCarregar_Click" />
<TextBox x:Name="txtNome" />
```
```csharp
private void BtnCarregar_Click(object sender, RoutedEventArgs e)
{
    txtNome.Text = _service.Carregar();
}
```

**Depois (MVVM):**
```xml
<Button Content="Carregar" Command="{Binding CarregarDadosCommand}" />
<TextBox Text="{Binding Titulo, UpdateSourceTrigger=PropertyChanged}" />
```
```csharp
// Code-behind fica so com DI wiring
public MainWindow(MainWindowViewModel viewModel)
{
    InitializeComponent();
    DataContext = viewModel;
}
```

**Mapeamento rapido de controles:**

| WinForms / Code-behind | WPF MVVM |
|------------------------|----------|
| `button.Click += handler` | `Command="{Binding XCommand}"` |
| `textBox.Text = valor` | `Text="{Binding Propriedade}"` |
| `listBox.Items.Add(x)` | `ItemsSource="{Binding Lista}"` + `ObservableCollection<T>` |
| `checkBox.Checked += handler` | `IsChecked="{Binding Flag}"` |
| `comboBox.SelectedItem` | `SelectedItem="{Binding ItemSelecionado}"` |
| `label.Content = texto` | `Content="{Binding Texto}"` |
| `progressBar.Value` | `Value="{Binding Progresso}"` |
| `control.Enabled = false` | `IsEnabled="{Binding PodeExecutar}"` ou `CanExecute` no Command |

**Dialogs MVVM-friendly:**
```csharp
// Em vez de: MessageBox.Show("Erro")
// Use Microsoft.Win32 para file dialogs:
var dialog = new Microsoft.Win32.OpenFileDialog { Filter = "HID files|*.hid" };
if (dialog.ShowDialog() == true)
{
    CaminhoArquivo = dialog.FileName;
}
```

Para dialogs mais complexos, use `IContentDialogService` do WPF-UI
(veja `references/wpfui-integration.md`).

### Passo 6: Verificacao

Apos aplicar MVVM, verifique:

1. **Build:** `dotnet build` deve compilar sem erros nem warnings de source generators
2. **Testes:** `dotnet test` — todos os testes existentes devem passar (MVVM nao muda services)
3. **Code-behind limpo:** Cada `.xaml.cs` deve ter apenas:
   - `InitializeComponent()`
   - `DataContext = viewModel` (ou atribuicao via DI)
   - Event handlers de UI-only (ex: Window closing, drag behavior)
4. **Atualizar CLAUDE.md:** Atualizar descricao do stack e arquitetura do projeto
5. **Funcionalidade:** Testar manualmente que a UI funciona como antes
6. **Testes de ViewModel:** Criar testes xUnit para o novo ViewModel (ver secao abaixo)

---

## Testes de ViewModel (Recomendacao)

Cada migracao MVVM deve incluir testes de ViewModel. Eles sao a melhor forma de blindar
o projeto contra regressoes durante refatoracoes — testam toda a logica de apresentacao
sem abrir janelas, sao rapidos e confiaveis no CI.

### O que testar

| Aspecto | Exemplo |
|---------|---------|
| Estado inicial | Propriedades iniciam com valores default corretos |
| Commands executam | `CarregarCommand.Execute()` popula propriedades |
| CanExecute | Botao desabilitado quando pre-condicao nao e atendida |
| Validacao | Dados invalidos mostram erro, nao executam acao |

### Padrao para Commands com Dialogs

Commands que abrem `OpenFileDialog` nao sao testaveis unitariamente. Extraia a logica
para um metodo publico testavel:

```csharp
// No ViewModel — o Command chama o dialog e depois o metodo testavel
[RelayCommand]
private void CarregarHardwareId()
{
    var dialog = new Microsoft.Win32.OpenFileDialog { Filter = "*.hid" };
    if (dialog.ShowDialog() == true)
        PopularCampos(_service.RecuperarDeArquivo(dialog.FileName));
}

// Metodo publico testavel (sem dialog)
public void PopularCampos(HardwareInfo hwInfo)
{
    CompanyName = hwInfo.CompanyName;
    ProcessorId = hwInfo.ProcessorID;
    // ...
    IsSaveEnabled = true;
}
```

```csharp
// No teste
[Fact]
public void PopularCampos_AtualizaPropriedadesEHabilitaSave()
{
    var vm = new MainWindowViewModel(service);
    vm.PopularCampos(new HardwareInfo { CompanyName = "JRC" });

    Assert.Equal("JRC", vm.CompanyName);
    Assert.True(vm.IsSaveEnabled);
}
```

### Testes E2E (para projetos maiores)

Para smoke tests visuais em projetos com muitas telas, considere FlaUI
(framework de automacao UI para WPF). Veja `TODO_SPECS/SPEC-Automated-UI-Testing.md`
para o plano completo.

---

## Cenarios Comuns

### Projeto WPF com code-behind (sem MVVM)

Este e o cenario mais comum — o projeto ja e WPF mas usa event handlers diretamente.
Execute todos os 6 passos. O Passo 4 e o mais trabalhoso: extrair logica dos event handlers
para ViewModels.

### Projeto WinForms (migrar para WPF + MVVM)

Leia `references/migration-winforms-to-wpf.md` antes de comecar.
A migracao acontece em duas fases:
1. **Fase A:** Converter Form para Window/Page (XAML equivalente ao layout do Form)
2. **Fase B:** Aplicar MVVM (Passos 3-6 deste workflow)

Migre form-a-form usando Strangler Fig pattern. Nao migre tudo de uma vez.

### Novo projeto WPF do zero

Leia `references/project-structure.md` para a estrutura de pastas recomendada.
Crie a estrutura Models/Views/ViewModels/Services antes de comecar a codar.
Comece pelo Passo 2 (pacotes), pule para Passo 3 (DI), depois crie ViewModels e Views.

### Adicionar navegacao entre paginas

Leia `references/wpfui-integration.md` secao sobre NavigationView.
Use `INavigationService` + `IPageService` do WPF-UI para navegacao DI-friendly.

---

## Detalhes Criticos

1. **Classes DEVEM ser `partial`** — source generators do CommunityToolkit exigem `partial class`.
   Sem `partial`, `[ObservableProperty]` e `[RelayCommand]` nao geram codigo e o build falha.

2. **Campos `[ObservableProperty]` devem ser `private`** — o generator cria a propriedade publica
   a partir do nome do campo: `_nomeDoNavio` gera `NomeDoNavio`. Se o campo for publico, conflita.

3. **Nao misturar dialogs WinForms e WPF** — em projetos WPF, usar `Microsoft.Win32.OpenFileDialog`
   e `Microsoft.Win32.SaveFileDialog`, nao os equivalentes de System.Windows.Forms.

4. **`ObservableCollection<T>` nao precisa de `[ObservableProperty]`** — declare como propriedade
   publica simples: `public ObservableCollection<Item> Items { get; } = new();`. A collection ja
   implementa `INotifyCollectionChanged` internamente.

5. **Atualizar CLAUDE.md apos migrar** — referencias a Form*.cs ficam desatualizadas apos migracao.
   Atualizar descricao do stack, nomes de arquivos UI, e tabela de projetos.

6. **CanExecute com `[RelayCommand]`** — para habilitar/desabilitar botoes automaticamente,
   use `[RelayCommand(CanExecute = nameof(PodeSalvar))]` e chame
   `SalvarCommand.NotifyCanExecuteChanged()` quando a condicao mudar.

7. **Async commands cancelam automaticamente** — se o metodo retorna `Task`, o `[RelayCommand]`
   gera `IAsyncRelayCommand` que desabilita o botao durante execucao e suporta cancelamento.

8. **Inicializar campos string com `= string.Empty`** — campos `[ObservableProperty]` do tipo
   string devem ser inicializados: `private string _nome = string.Empty;`. Sem isso, bindings
   podem receber null e causar warnings ou comportamento inesperado.

9. **StatusMessage como alternativa a MessageBox** — para apps simples (1-2 telas), substituir
   `MessageBox.Show()` por atualizar uma propriedade `StatusMessage` no ViewModel e exibi-la
   na barra de status e mais simples e testavel que criar `IDialogService`. Reservar
   `IContentDialogService` do WPF-UI para apps com multiplas telas ou dialogs complexos.

10. **Icone da aplicacao em FluentWindow** — nao usar `Icon=` no XAML nem `BitmapImage` no
    code-behind (ambos carregam o menor frame do .ico e ficam pixelados). Usar `BitmapDecoder`
    para selecionar o frame de maior resolucao. Declarar o .ico como `<ApplicationIcon>` E
    `<Resource>` no .csproj. Veja `references/wpfui-integration.md` secao "Icone da Aplicacao".

11. **`ui:Page` NAO existe no WPF-UI 4.2.0** — usar `<Page>` padrao do WPF
    (namespace `System.Windows.Controls`). Code-behind herda `Page`, NAO `INavigableView<T>`.

12. **`INavigationViewPageProvider` esta em `Wpf.Ui.Abstractions`** — NAO em `Wpf.Ui` nem
    `Wpf.Ui.Controls`. Metodo: `GetPage(Type pageType)` retorna `object?`.

13. **`MessageBoxButton` conflita com WPF-UI** — quando ambos namespaces sao usados, adicionar
    alias: `using MessageBoxButton = System.Windows.MessageBoxButton;` e
    `using MessageBoxImage = System.Windows.MessageBoxImage;`.

14. **NAO importar `Wpf.Ui.Controls` globalmente** — causa conflitos com `MessageBoxButton`,
    `Page`, etc. Qualificar tipos WPF-UI individualmente:
    `public partial class MainWindow : Wpf.Ui.Controls.FluentWindow`.

15. **PageService deve ser criado manualmente** — WPF-UI nao fornece implementacao built-in de
    `INavigationViewPageProvider`. Criar classe `PageService(IServiceProvider sp)` com
    `GetPage(Type) => sp.GetService(pageType)`. Setup:
    `RootNavigation.SetPageProviderService(pageProvider)` (NAO `SetPageService()`).

16. **NavigationView action items: usar `PreviewMouseLeftButtonUp`** — no WPF-UI 4.2.0,
    nem `ItemInvoked` nem `SelectionChanged` disparam para NavigationViewItems sem
    `TargetPageType` (items de acao como Browse/Upload). Usar `PreviewMouseLeftButtonUp`
    diretamente no NavigationViewItem com `e.Handled = true`.

17. **DataGrid: usar `AutoGenerateColumns="False"`** — definir colunas explicitamente em XAML
    para controlar visibilidade, headers e formatacao. Colunas que nao devem aparecer simplesmente
    nao sao declaradas (mais limpo que `Visibility="Collapsed"` em cada coluna).

18. **NavigationView quebra virtualizacao** — o NavigationView do WPF-UI internamente usa layout
    que da **altura infinita** as paginas. Qualquer ListBox/DataGrid/ListView dentro de uma Page
    recebe ActualHeight infinito e renderiza TODOS os items (virtualizacao desabilitada).
    **Fix obrigatorio**: usar `MaxHeight` fixo + `Page_SizeChanged` para ajustar dinamicamente:
    ```csharp
    private void Page_SizeChanged(object sender, SizeChangedEventArgs e)
    {
        if (dgvLog != null && e.NewSize.Height > 100)
            dgvLog.MaxHeight = e.NewSize.Height - 120;
    }
    ```

19. **Singleton para paginas pesadas** — Pages registradas como `Transient` sao recriadas a cada
    navegacao (visual tree, bindings, tudo reconstruido). Para paginas com dados grandes, registrar
    como `Singleton` no DI evita reconstrucao e mantem estado de scroll/filtro. Adicionar metodo
    `ReloadData()` para resetar quando novos dados sao carregados.

20. **WindowBackdropType="None" com WindowsFormsHost** — `Mica` habilita transparencia
    internamente, o que torna controles WinForms (via WindowsFormsHost) **invisiveis**. Bug
    documentado pela Microsoft. Usar `WindowBackdropType="None"` se WindowsFormsHost for necessario.

21. **Page.Resources ANTES do conteudo** — declarar `<Page.Resources>` com Styles/converters
    ANTES do conteudo XAML (DockPanel, Grid, etc). Se declarado depois, `StaticResource` falha
    com erro "StaticResourceExtension" em runtime.

22. **SolidColorBrush.Freeze()** — brushes estaticos devem ser frozen para thread-safety:
    ```csharp
    private static SolidColorBrush CreateFrozenBrush(byte r, byte g, byte b)
    {
        var brush = new SolidColorBrush(Color.FromRgb(r, g, b));
        brush.Freeze();
        return brush;
    }
    ```

23. **LINQ filter em POCOs em vez de DataView.RowFilter** — para listas grandes (100K+),
    converter DataTable para `List<T>` tipado em background e filtrar com LINQ e mais rapido
    e thread-safe que DataView.RowFilter (que usa reflexao e nao e thread-safe).

24. **Debounce para filtros** — em TextBoxes de filtro, usar debounce de 300ms com
    `CancellationTokenSource` para filtrar enquanto o usuario digita sem travar a UI:
    ```csharp
    _filterCts?.Cancel();
    _filterCts?.Dispose();
    _filterCts = new CancellationTokenSource();
    _ = Task.Delay(300, _filterCts.Token).ContinueWith(t => {
        if (!t.IsCanceled) Dispatcher.Invoke(ApplyFilter);
    });
    ```

25. **Lazy property caching com ??=** — para propriedades formatadas chamadas repetidamente
    pelo binding (ex: DateTimeFormatted), usar lazy initialization para evitar ToString() em
    cada frame de renderizacao:
    ```csharp
    private string? _formatted;
    public string Formatted => _formatted ??= DateTime.ToString("dd/MM/yyyy HH:mm:ss");
    ```

26. **IReadOnlyList para caches** — expor caches estaticos como `IReadOnlyList<T>` em vez de
    `List<T>` para prevenir modificacao acidental por consumidores.

---

## Anti-padroes desta Skill

- **ViewModel referenciando UI** — ViewModel NUNCA deve importar `System.Windows` ou acessar
  controles da View. Use bindings e Messenger para tudo.
- **Logica de negocio no ViewModel** — ViewModel orquestra, Service executa. Se o ViewModel
  esta fazendo IO, parsing ou calculo complexo, mova para um Service.
- **`new ViewModel()` no XAML** — funciona, mas impede DI. Prefira injetar via construtor.
- **Ignorar UpdateSourceTrigger** — `TextBox` default e `LostFocus`. Use
  `UpdateSourceTrigger=PropertyChanged` para validacao em tempo real.
- **`List<T>` em vez de `ObservableCollection<T>`** — `List` nao notifica a View quando
  itens sao adicionados/removidos. Sempre use `ObservableCollection` para listas bindadas.
- **DataGrid/ListView para listas grandes (>5K items)** — WPF DataGrid e ListView travam
  dentro de NavigationView mesmo com virtualizacao. Usar ListBox com paginacao (500 items/pagina)
  ou registrar a Page como Singleton. Nunca confiar apenas na virtualizacao sem testar.
- **DataView.RowFilter em background thread** — DataView NAO e thread-safe. Usar LINQ em
  `List<T>` tipado ou copiar o DataTable antes de filtrar. `DefaultView` compartilhado entre
  consumidores causa race conditions.
- **SymbolIcons inexistentes** — nem todos os icones listados na documentacao do WPF-UI existem
  na versao 4.2.0. Exemplos que NAO existem: `SignalStrength24`, `PlugConnected24`. Testar
  em runtime antes de commitar.
- **`async void` em metodos que nao sao event handlers** — metodos `async void` fora de
  handlers UI (Click, Loaded) causam excecoes nao-observadas que podem crashar a aplicacao.
  Sempre usar `async Task` e `await` no chamador. `[RelayCommand]` gera `IAsyncRelayCommand`
  que ja usa `async Task` internamente — nunca converter para `async void`.
- **`using Wpf.Ui.Controls;` global** — conflita com `System.Windows.Controls` (TextBox,
  ComboBox, Page, Button). Usar type aliases: `using ControlAppearance = Wpf.Ui.Controls.ControlAppearance;`
- **ContentDialogPresenter no XAML** — o elemento correto e `<ui:ContentDialogHost>`, nao
  `<ui:ContentPresenter>` ou `<ui:ContentDialogPresenter>`. Erro comum que causa crash.
- **ShowSimpleDialogAsync sem using** — `ShowSimpleDialogAsync` e extension method em
  `Wpf.Ui.Extensions`. Requer `using Wpf.Ui.Extensions;` no arquivo.

---

## Guias de Referencia (progressive disclosure level 3)

Leia estes arquivos **somente quando necessario** no passo correspondente:

| Arquivo | Leia quando... |
|---------|----------------|
| `references/mvvm-fundamentals.md` | Usuario e novo em MVVM ou quer entender conceitos |
| `references/communitytoolkit-patterns.md` | Passo 4 — criando ViewModels com source generators |
| `references/wpfui-integration.md` | Passo 3 — configurando DI, navegacao e theming com WPF-UI |
| `references/migration-winforms-to-wpf.md` | Projeto e WinForms e precisa migrar para WPF |
| `references/project-structure.md` | Criando projeto do zero ou reorganizando pastas |
