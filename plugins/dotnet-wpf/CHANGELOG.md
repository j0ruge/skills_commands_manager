# Changelog — dotnet-wpf

Formato: [Semantic Versioning](https://semver.org/)

## [1.5.0] - 2026-04-09

### Added

- `dotnet-wpf-design` FORM-004: separador sutil entre grupos de campos em Grid. Border com `BorderThickness="0,0,0,1"` e `DividerStrokeColorDefaultBrush` em row dedicada (`Margin="0,8"`). Inclui anti-padrao documentado: nunca compartilhar row do separador com conteudo (causa sobreposicao visual).
- Anti-pattern #11: Border separador na mesma Grid.Row que conteudo causa sobreposicao — usar row dedicada.

### Changed

- Plugin version bumped to 1.5.0.

## [1.4.0] - 2026-04-08

### Added

- `dotnet-wpf-design` FORM-003: estilos implicitos em `<StackPanel.Resources>` tem blast radius indesejado em layouts mistos. Recipe completo em `references/form-design.md`.
- Anti-pattern #10: estilos implicitos para Margin de inputs quebra toolbars e StackPanels horizontais.
- Detalhe Critico #9: texto clipado em controle Fluent quase sempre e altura, nao largura.
- Detalhe Critico #10: mudancas em XAML de UserControl em DLL referenciada precisam de process restart.

### Fixed

- `dotnet-wpf-design` FORM-002: exemplo com `Height="32"` no UserControl e ComboBox FontSize=13 causava clipping. Corrigido para auto-tamanho.

## [1.3.0] - 2026-04-07

### Added

- `dotnet-wpf-design` WPF-UI deep dive: catalogo completo de 90+ controles em `references/wpfui-controls-catalog.md`.
- ControlAppearance enum (Primary, Danger, Success, Caution) para semantica de cores.
- DI services: IContentDialogService, ISnackbarService pattern.
- Controles novos: NumberBox, AutoSuggestBox, ToggleSwitch, ContentDialog, Snackbar, Flyout, CalendarDatePicker, PassiveScrollViewer.
- FontTypography completado: TitleLarge (40px), Display (68px).

## [1.2.0] - 2026-04-06

### Added

- `dotnet-wpf-design` CTRL-003: SymbolIcon sharing bug in DataGrid — icons in Style.Setter.Value are shared across rows, only last row shows icon. Documented correct pattern using DataTemplate.Triggers with Visibility.
- `dotnet-wpf-design` LAYOUT-001 variant: toolbar fixa em paginas com DataGrid (sem ScrollViewer explicito). CanContentScroll="False" desabilita DynamicScrollViewer e DataGrid usa scroll interno.
- `dotnet-wpf-design` DataGrid RowHeight recommendation: 30px as sweet spot for readability. Updated controls-sizing.md with comparison table and ListBox equivalent.
- `dotnet-wpf-design` audit checklist: DataGrid RowHeight >= 30px + SymbolIcon Visibility pattern check.
- Anti-pattern #9: UIElements in Style Setter.Value inside DataTemplate.

## [1.0.0] - 2026-04-01

### Added

- `dotnet-desktop-setup` skill — configures and audits C#/.NET desktop projects for Claude Code (WinForms, WPF, Avalonia). Includes environment audit script, CLAUDE.md templates, .editorconfig template, scoped rules, and decoupling/testing guides.
- `dotnet-wpf-design` skill — professional WPF/XAML Fluent Design guide with WPF-UI. 90+ controls catalog, layout patterns, typography/colors, form design, and controls sizing references.
- `dotnet-wpf-e2e-testing` skill — FlaUI + xUnit E2E testing guide for WPF. AutomationId patterns, Page Objects, CI/CD setup for UI tests.
- `dotnet-wpf-mvvm` skill — WinForms-to-WPF migration with MVVM using CommunityToolkit.Mvvm and WPF-UI. ViewModels, DataBinding, Commands, navigation, and DI configuration.
