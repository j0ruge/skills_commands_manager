# Integracao WPF-UI com MVVM

Guia para configurar WPF-UI (Fluent Design) com CommunityToolkit.Mvvm e DI.
Leia durante o Passo 3 (configurar App.xaml.cs).

---

## App.xaml — Configuracao de Tema

```xml
<Application x:Class="MeuProjeto.App"
             xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
             xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
             xmlns:ui="http://schemas.lepo.co/wpfui/2022/xaml">
    <Application.Resources>
        <ResourceDictionary>
            <ResourceDictionary.MergedDictionaries>
                <ui:ThemesDictionary Theme="Dark" />
                <ui:ControlsDictionary />
            </ResourceDictionary.MergedDictionaries>
        </ResourceDictionary>
    </Application.Resources>
</Application>
```

Remova `StartupUri` do App.xaml — a janela sera criada pelo DI no code-behind.

---

## App.xaml.cs — Composition Root Completo

Este e o template padrao para projetos WPF-UI com MVVM e DI:

```csharp
using System.Windows;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Wpf.Ui;

namespace MeuProjeto;

public partial class App : Application
{
    private static IHost? _host;

    public static IServiceProvider Services => _host!.Services;

    protected override async void OnStartup(StartupEventArgs e)
    {
        _host = Host.CreateDefaultBuilder()
            .ConfigureServices((context, services) =>
            {
                // === Services de negocio ===
                services.AddSingleton<ILicenseService, LicenseService>();
                // Adicionar outros services aqui...

                // === Services WPF-UI ===
                services.AddSingleton<INavigationService, NavigationService>();
                services.AddSingleton<IContentDialogService, ContentDialogService>();
                services.AddSingleton<ISnackbarService, SnackbarService>();

                // === Windows ===
                services.AddSingleton<MainWindow>();
                services.AddSingleton<MainWindowViewModel>();

                // === Pages (se usar navegacao) ===
                // services.AddTransient<DashboardPage>();
                // services.AddTransient<DashboardViewModel>();
                // services.AddTransient<SettingsPage>();
                // services.AddTransient<SettingsViewModel>();
            })
            .Build();

        await _host.StartAsync();

        var mainWindow = Services.GetRequiredService<MainWindow>();
        mainWindow.Show();

        base.OnStartup(e);
    }

    protected override async void OnExit(ExitEventArgs e)
    {
        if (_host != null)
        {
            await _host.StopAsync();
            _host.Dispose();
        }

        base.OnExit(e);
    }
}
```

### App simples (1 janela, sem navegacao)

Para projetos como LicenceManager que tem apenas uma janela:

```csharp
.ConfigureServices((context, services) =>
{
    // Services
    services.AddSingleton<LicenseService>();

    // Window + ViewModel
    services.AddSingleton<MainWindow>();
    services.AddSingleton<MainWindowViewModel>();
})
```

Nao precisa de INavigationService nem IPageService.

---

## FluentWindow

WPF-UI substitui `Window` por `FluentWindow` para visual moderno:

```xml
<ui:FluentWindow x:Class="MeuProjeto.MainWindow"
    xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
    xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
    xmlns:ui="http://schemas.lepo.co/wpfui/2022/xaml"
    Title="Meu App"
    Width="800" Height="600"
    ExtendsContentIntoTitleBar="True"
    WindowBackdropType="Mica">

    <Grid>
        <Grid.RowDefinitions>
            <RowDefinition Height="Auto" />
            <RowDefinition Height="*" />
        </Grid.RowDefinitions>

        <ui:TitleBar Grid.Row="0" Title="Meu App" />

        <!-- Conteudo da janela -->
        <Grid Grid.Row="1" Margin="16">
            <!-- Seus controles aqui, com bindings -->
        </Grid>
    </Grid>
</ui:FluentWindow>
```

Code-behind:
```csharp
using Wpf.Ui.Controls;

namespace MeuProjeto;

public partial class MainWindow : FluentWindow
{
    public MainWindow(MainWindowViewModel viewModel)
    {
        InitializeComponent();
        DataContext = viewModel;
    }
}
```

---

## NavigationView (Apps Multi-Pagina)

Para apps com menu lateral e navegacao entre paginas:

### MainWindow.xaml
```xml
<ui:FluentWindow x:Class="MeuProjeto.MainWindow"
    xmlns:ui="http://schemas.lepo.co/wpfui/2022/xaml"
    ExtendsContentIntoTitleBar="True"
    WindowBackdropType="Mica">

    <Grid>
        <ui:TitleBar Title="Meu App" />

        <ui:NavigationView
            x:Name="RootNavigation"
            PaneDisplayMode="Left"
            IsBackButtonVisible="Auto">

            <ui:NavigationView.MenuItems>
                <ui:NavigationViewItem Content="Dashboard"
                    Icon="{ui:SymbolIcon Home24}"
                    TargetPageType="{x:Type pages:DashboardPage}" />
                <ui:NavigationViewItem Content="Configuracoes"
                    Icon="{ui:SymbolIcon Settings24}"
                    TargetPageType="{x:Type pages:SettingsPage}" />
            </ui:NavigationView.MenuItems>
        </ui:NavigationView>
    </Grid>
</ui:FluentWindow>
```

### MainWindow.xaml.cs
```csharp
public partial class MainWindow : FluentWindow
{
    public MainWindow(
        MainWindowViewModel viewModel,
        INavigationService navigationService)
    {
        InitializeComponent();
        DataContext = viewModel;

        navigationService.SetNavigationControl(RootNavigation);
    }
}
```

### PageService — Implementacao Manual Obrigatoria

WPF-UI **NAO fornece** implementacao built-in de `INavigationViewPageProvider`. Criar:

```csharp
using Wpf.Ui.Abstractions; // NAO Wpf.Ui nem Wpf.Ui.Controls

namespace MeuProjeto.Services;

public class PageService(IServiceProvider serviceProvider) : INavigationViewPageProvider
{
    public object? GetPage(Type pageType) => serviceProvider.GetService(pageType);
}
```

### DI Registration para navegacao
```csharp
// No App.xaml.cs
services.AddSingleton<INavigationService, NavigationService>();
services.AddSingleton<INavigationViewPageProvider, PageService>();

// Cada pagina e seu ViewModel
services.AddTransient<DashboardPage>();
services.AddTransient<DashboardViewModel>();
services.AddTransient<SettingsPage>();
services.AddTransient<SettingsViewModel>();
```

### Setup no construtor da MainWindow
```csharp
public MainWindow(
    INavigationService navigationService,
    INavigationViewPageProvider pageProvider)
{
    InitializeComponent();
    // Metodo correto: SetPageProviderService (NAO SetPageService)
    RootNavigation.SetPageProviderService(pageProvider);
    navigationService.SetNavigationControl(RootNavigation);
}
```

### Page com ViewModel
```csharp
public partial class DashboardPage : Page  // Page padrao do WPF, NAO ui:Page
{
    public DashboardPage(DashboardViewModel viewModel)
    {
        InitializeComponent();
        DataContext = viewModel;
    }
}
```

### Navegar de um ViewModel
```csharp
public partial class DashboardViewModel : ObservableObject
{
    private readonly INavigationService _navigation;

    public DashboardViewModel(INavigationService navigationService)
    {
        _navigation = navigationService;
    }

    [RelayCommand]
    private void IrParaConfiguracoes()
    {
        _navigation.Navigate(typeof(SettingsPage));
    }
}
```

---

## Conflitos de Namespace (WPF-UI 4.2.0)

Quando `Wpf.Ui.Controls` e `System.Windows` sao usados no mesmo arquivo, varios tipos
conflitam. A solucao recomendada:

```csharp
// NAO fazer: using Wpf.Ui.Controls;

// Fazer: qualificar tipos WPF-UI individualmente
public partial class MainWindow : Wpf.Ui.Controls.FluentWindow { }

// Se precisar de MessageBox do System.Windows, adicionar alias:
using MessageBoxButton = System.Windows.MessageBoxButton;
using MessageBoxImage = System.Windows.MessageBoxImage;
```

**Tipos que conflitam**: `MessageBoxButton`, `MessageBoxResult`, `Page`, `Button`, `TextBox`.

---

## NavigationView: Items de Acao vs Paginas

NavigationView suporta dois tipos de items:

### Items que navegam para Page (automatico)
```xml
<ui:NavigationViewItem Content="Channels"
    Icon="{ui:SymbolIcon Channel24}"
    TargetPageType="{x:Type pages:ChannelsPage}" />
```

### Items de acao (tratados no evento)
```xml
<ui:NavigationViewItem Content="Browse"
    Icon="{ui:SymbolIcon FolderOpen24}"
    Tag="browse" />
```

**IMPORTANTE**: Usar `PreviewMouseLeftButtonUp` diretamente no NavigationViewItem.
No WPF-UI 4.2.0, nem `ItemInvoked` nem `SelectionChanged` disparam de forma confiavel
para items sem `TargetPageType`. `PreviewMouseLeftButtonUp` e um evento WPF nativo que
**sempre** dispara.

```xml
<ui:NavigationViewItem Content="Browse"
    Icon="{ui:SymbolIcon FolderOpen24}"
    Tag="browse"
    PreviewMouseLeftButtonUp="Browse_Click" />
```

```csharp
private void Browse_Click(object sender, MouseButtonEventArgs e)
{
    Browse();
    e.Handled = true; // Impede propagacao
}
```

### Esconder items ate dados serem carregados
```xml
<ui:NavigationViewItem x:Name="NavChannels"
    Content="Channels"
    TargetPageType="{x:Type pages:ChannelsPage}"
    Visibility="Collapsed" />
```
```csharp
// Apos carregar dados:
NavChannels.Visibility = Visibility.Visible;
```

---

## IContentDialogService (Dialogs MVVM-Friendly)

Substitui `MessageBox.Show()` com dialogs estilizados do Fluent Design:

### Registro
```csharp
services.AddSingleton<IContentDialogService, ContentDialogService>();
```

### Inicializacao na MainWindow

**IMPORTANTE:** O elemento XAML correto e `ContentDialogHost` (nao `ContentPresenter`
ou `ContentDialogPresenter`). A ordem de inicializacao deve ser: services primeiro,
DataContext depois.

```csharp
public MainWindow(
    MainWindowViewModel vm,
    IContentDialogService dialogService,
    ISnackbarService snackbarService)
{
    InitializeComponent();

    // Inicializar services ANTES do DataContext
    dialogService.SetDialogHost(RootContentDialogHost);
    snackbarService.SetSnackbarPresenter(RootSnackbarPresenter);

    DataContext = vm;
}
```

No XAML, adicione os presenters no mesmo Grid Row que o NavigationView:
```xml
<Grid>
    <!-- Seu conteudo (NavigationView, etc.) -->
    <ui:ContentDialogHost x:Name="RootContentDialogHost" Grid.Row="0" />
    <ui:SnackbarPresenter x:Name="RootSnackbarPresenter" Grid.Row="0" />
</Grid>
```

**Namespace necessario:** `ShowSimpleDialogAsync` e um extension method — requer
`using Wpf.Ui.Extensions;` no arquivo que o chama.

**Conflito de namespace:** `using Wpf.Ui.Controls;` conflita com
`System.Windows.Controls` (TextBox, ComboBox, Page, Button). Use type aliases:
```csharp
using ControlAppearance = Wpf.Ui.Controls.ControlAppearance;
using SymbolIcon = Wpf.Ui.Controls.SymbolIcon;
using SymbolRegular = Wpf.Ui.Controls.SymbolRegular;
```

### Uso no ViewModel
```csharp
private readonly IContentDialogService _dialogService;

[RelayCommand]
private async Task ExcluirAsync()
{
    var result = await _dialogService.ShowSimpleDialogAsync(
        new SimpleContentDialogCreateOptions
        {
            Title = "Confirmar exclusao",
            Content = "Deseja realmente excluir este item?",
            PrimaryButtonText = "Excluir",
            CloseButtonText = "Cancelar"
        });

    if (result == ContentDialogResult.Primary)
    {
        _service.Excluir(ItemSelecionado);
    }
}
```

---

## Troca de Tema em Runtime

```csharp
using Wpf.Ui.Appearance;

// No ViewModel ou service
[RelayCommand]
private void AlternarTema()
{
    var currentTheme = ApplicationThemeManager.GetAppTheme();
    ApplicationThemeManager.Apply(
        currentTheme == ApplicationTheme.Dark
            ? ApplicationTheme.Light
            : ApplicationTheme.Dark);
}
```

---

## Icone da Aplicacao

Definir o icone de uma app WPF/WPF-UI tem armadilhas que nao sao obvias.
Aqui estao as licoes aprendidas para evitar dor de cabeca:

### .csproj — Duas declaracoes necessarias

O icone precisa ser declarado de **duas formas** no .csproj:

```xml
<PropertyGroup>
    <!-- Define o icone do executavel (Explorer, atalhos) -->
    <ApplicationIcon>Resources\meu_icone.ico</ApplicationIcon>
</PropertyGroup>

<ItemGroup>
    <!-- Permite que o WPF encontre o icone via pack URI em runtime -->
    <Resource Include="Resources\meu_icone.ico" />
</ItemGroup>
```

Sem `<ApplicationIcon>`, o .exe nao tem icone no Explorer.
Sem `<Resource>`, o WPF nao encontra o arquivo via `pack://application:,,,/` e lanca
`IOException: Nao e possivel localizar o recurso`.

### Carregar icone no FluentWindow — Usar BitmapDecoder

`BitmapImage` carrega apenas o **menor frame** de um .ico, resultando em um icone
pixelado na taskbar. Use `BitmapDecoder` para selecionar o frame de maior resolucao:

```csharp
// NO code-behind da MainWindow (nao no XAML!)
public MainWindow(MainWindowViewModel viewModel)
{
    InitializeComponent();
    DataContext = viewModel;

    // Carregar icone selecionando o frame de maior resolucao
    var iconUri = new Uri("pack://application:,,,/Resources/meu_icone.ico");
    var decoder = BitmapDecoder.Create(iconUri, BitmapCreateOptions.None, BitmapCacheOption.OnLoad);

    BitmapFrame best = decoder.Frames[0];
    foreach (var frame in decoder.Frames)
    {
        if (frame.PixelWidth > best.PixelWidth)
            best = frame;
    }
    Icon = best;
}
```

Nao defina `Icon=` diretamente no XAML da FluentWindow — a conversao de tipo do XAML
nao funciona bem com .ico e pode lancar `XamlParseException`.

### Tamanhos recomendados no .ico

Para que o icone apareca nitido em todos os contextos do Windows:

| Tamanho | Onde aparece |
|---------|-------------|
| 16x16 | Title bar da janela, menus |
| 24x24 | Taskbar (tamanho pequeno) |
| 32x32 | Taskbar (tamanho normal), Alt+Tab |
| 48x48 | Explorer (visualizacao media) |
| 64x64 | Explorer (tiles) |
| 128x128 | Explorer (icones grandes) |
| 256x256 | Explorer (icones extra grandes) |

Inclua pelo menos 16, 32, 48 e 256. O Windows redimensiona a partir do frame
mais proximo, entao mais tamanhos = melhor qualidade.

### Gerando icones — Cuidado com fontes

Se voce precisa gerar um .ico programaticamente (ex: usando um glyph de icone):

- `Segoe Fluent Icons` (usada pelo WPF-UI internamente) **nao esta disponivel**
  via GDI+ (`System.Drawing`) no Windows 10. Ela existe apenas via DirectWrite/WPF.
  O GDI+ faz fallback silencioso para `Microsoft Sans Serif`, renderizando um quadrado.
- `Segoe MDL2 Assets` esta disponivel no Win10 via GDI+ e tem glyphs de escudo,
  cadeado, etc. — mas sao outline, nao filled como os do Fluent Icons.
- Para icones com design especifico, prefira desenhar com GDI+ (`GraphicsPath`,
  `FillPolygon`, bezier curves) em vez de depender de fontes de icone.

### Cache de icones do Windows

O Windows cacheia icones agressivamente. Se voce trocou o .ico e o icone nao muda:

1. Fechar a aplicacao
2. Limpar bin/obj: `rm -rf bin obj`
3. Rebuild: `dotnet build`
4. Se ainda nao mudar, reiniciar o Explorer:
   `taskkill /f /im explorer.exe && start explorer.exe`
