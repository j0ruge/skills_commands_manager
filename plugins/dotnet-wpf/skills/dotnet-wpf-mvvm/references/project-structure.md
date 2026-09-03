# Estrutura de Projeto WPF MVVM

Guia de organizacao de pastas, naming e registro de DI para projetos WPF novos
ou reorganizacao de projetos existentes.

---

## Estrutura de Pastas Recomendada

```
MeuProjeto/
├── Models/                    Dados e regras de negocio puras
│   ├── Navio.cs
│   └── LicenseInfo.cs
├── ViewModels/                Intermediarios View↔Model
│   ├── MainWindowViewModel.cs
│   ├── DashboardViewModel.cs
│   └── SettingsViewModel.cs
├── Views/                     Telas XAML
│   ├── Pages/
│   │   ├── DashboardPage.xaml
│   │   └── SettingsPage.xaml
│   └── Dialogs/
│       └── ConfirmacaoDialog.xaml
├── Services/                  Logica de negocio e acesso a dados
│   ├── ILicenseService.cs
│   ├── LicenseService.cs
│   └── INavigationHelper.cs
├── Messages/                  Mensagens do Messenger (records)
│   └── DadosSalvosMessage.cs
├── Converters/                IValueConverter para bindings
│   └── BoolToVisibilityConverter.cs
├── Resources/                 Assets visuais
│   ├── Styles/
│   └── Images/
├── App.xaml                   Tema e recursos globais
├── App.xaml.cs                Composition root (DI)
├── MainWindow.xaml            Janela principal
└── MainWindow.xaml.cs         Code-behind minimo
```

### Projetos pequenos (1-3 telas)

Nao precisa de todas as pastas. O minimo e:

```
MeuProjeto/
├── ViewModels/
│   └── MainWindowViewModel.cs
├── Services/
│   └── MeuService.cs
├── App.xaml / App.xaml.cs
├── MainWindow.xaml / MainWindow.xaml.cs
```

Adicione pastas conforme o projeto cresce.

---

## Naming Conventions

| Tipo | Naming | Exemplo |
|------|--------|---------|
| ViewModel | `*ViewModel` | `MainWindowViewModel`, `DashboardViewModel` |
| Page | `*Page` | `DashboardPage`, `SettingsPage` |
| Window | `*Window` | `MainWindow`, `LoginWindow` |
| Service interface | `I*Service` | `ILicenseService`, `INavigationHelper` |
| Service impl | `*Service` | `LicenseService` |
| Message | `*Message` | `DadosSalvosMessage`, `NavioSelecionadoMessage` |
| Converter | `*Converter` | `BoolToVisibilityConverter` |
| Model | Nome do dominio | `Navio`, `LicenseInfo`, `Alert` |

### Correspondencia View ↔ ViewModel

Cada View deve ter um ViewModel correspondente com nome similar:

| View | ViewModel |
|------|-----------|
| `MainWindow.xaml` | `MainWindowViewModel.cs` |
| `DashboardPage.xaml` | `DashboardViewModel.cs` |
| `AlertsPage.xaml` | `AlertsViewModel.cs` |

---

## Namespace Mapping no XAML

Para referenciar ViewModels e Views no XAML, declare os namespaces:

```xml
<Window x:Class="MeuProjeto.MainWindow"
        xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        xmlns:ui="http://schemas.lepo.co/wpfui/2022/xaml"
        xmlns:vm="clr-namespace:MeuProjeto.ViewModels"
        xmlns:views="clr-namespace:MeuProjeto.Views.Pages">
```

Para DataTemplates (navegacao via ContentControl):
```xml
<Window.Resources>
    <DataTemplate DataType="{x:Type vm:DashboardViewModel}">
        <views:DashboardPage />
    </DataTemplate>
</Window.Resources>
```

---

## Padrao de Registro no DI

### Ciclos de vida

| Ciclo | Quando usar | Exemplo |
|-------|-------------|---------|
| **Singleton** | Estado compartilhado, services stateless, ViewModels (ver SKILL.md, Detalhe #27) | `INavigationService`, `AppState`, `*ViewModel` |
| **Transient** | Nova instancia a cada pedido | Pages de navegacao |
| **Scoped** | Per-request (raro em desktop) | Quase nunca em WPF |

### Template de registro

```csharp
services.ConfigureServices((context, services) =>
{
    // Services de negocio (Singleton — stateless ou estado compartilhado)
    services.AddSingleton<ILicenseService, LicenseService>();
    services.AddSingleton<IVdrService, VdrService>();

    // Services WPF-UI (Singleton — controlam estado de navegacao)
    services.AddSingleton<INavigationService, NavigationService>();
    services.AddSingleton<IContentDialogService, ContentDialogService>();
    services.AddSingleton<INavigationViewPageProvider, PageService>();

    // Window principal (Singleton — so existe uma)
    services.AddSingleton<MainWindow>();
    services.AddSingleton<MainWindowViewModel>();

    // Pages (Transient — criadas sob demanda pela navegacao)
    services.AddTransient<DashboardPage>();
    services.AddTransient<SettingsPage>();
    services.AddTransient<AlertsPage>();

    // ViewModels de pagina (Singleton — Transient + assinatura de servico Singleton
    // vaza memoria a cada navegacao; ver SKILL.md, Detalhe #27)
    services.AddSingleton<DashboardViewModel>();
    services.AddSingleton<SettingsViewModel>();
    services.AddSingleton<AlertsViewModel>();
});
```

### Regra geral
- **1 Window, 1 ViewModel** para a janela principal → Singleton
- **N Pages** de navegacao → Transient; **seus ViewModels** → Singleton (Transient +
  assinatura de servico Singleton = memory leak; ver SKILL.md, Detalhe #27)
- **Services de negocio** → Singleton (a menos que mantenham estado per-operacao)
