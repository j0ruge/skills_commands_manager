# Changelog — dotnet-wpf

Formato: [Semantic Versioning](https://semver.org/)

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
