# Changelog — dotnet-wpf-design

Historico completo de versoes. A versao atual + anterior ficam no SKILL.md; versoes
antigas sao arquivadas aqui para manter o SKILL.md compacto.

## v1.6.0 (2026-04-16)

- **CTRL-008** novo: padrao "guard before mutate" para `ContentDialog`. Acoes
  destrutivas (Load Last Export, Reset Form, Discard Changes) confirmam **antes**
  de qualquer leitura de I/O ou mutacao do view-model. O handler chama o dialogo
  como primeira linha e faz early-return em `confirm != ContentDialogResult.Primary`.
  Cancelar => o estado anterior fica 100% intacto, sem snackbar de "sucesso"
  enganoso.
- **Decisao "sempre confirmar vs. so quando dirty"** documentada em CTRL-008:
  dirty-tracking exige snapshot + comparacao confiavel (alto custo, alto risco
  de false-negatives que recriam o bug). Quando o estado raramente esta vazio
  (form auto-preenchido, lista populada por API), sempre confirmar e o trade-off
  vencedor — 1 clique extra contra trabalho perdido.
- **Regras de UX para o dialogo** (em CTRL-008): texto do Primary descreve a
  acao ("Replace data", "Delete report") em vez de "OK"; `Appearance="Danger"`
  apenas quando irreversivel; dialog mora em `*Page.xaml.cs`, nao no ViewModel
  (regras de UI decoupling).
- **Detalhe Critico #7** expandido com lista explicita de aliases comuns para
  resolver conflito `Wpf.Ui.Controls` ↔ `System.Windows.Controls`. Inclui
  `ContentDialogResult` — facil de esquecer porque so aparece quando o handler
  evolui de "single OK" para "Primary + Close" (CTRL-008).

## v1.5.0 (2026-04-14)

- **BRAND-001** novo: customizar cor de botoes `Appearance="Primary"` via override de
  `AccentButtonBackground*` / `AccentButtonForeground*` globalmente em `App.xaml`. Garante
  transicoes hover/pressed sem delay (o template do `ui:Button` usa DynamicResource nos
  triggers internos, nao TemplateBinding de Background). Solucao *"faca funcionar o sistema
  de aparencias em vez de fighta-lo"*.
- **CTRL-004** novo: forcar cor de texto branco em `ToggleButton` `IsChecked=True` via
  override local de `ToggleButtonForegroundChecked` no `UserControl.Resources`. Setar
  `button.Foreground = Brushes.White` via code-behind **nao funciona** porque o template
  aplica `TextElement.Foreground` no ContentPresenter interno via DynamicResource (vence
  property inheritance).
- **CTRL-005** novo: customizar CheckBox checked glyph + fundo via
  `CheckBoxCheckBackgroundFillChecked` (+ `PointerOver`, `Pressed`) e
  `CheckBoxCheckGlyphForeground` (resource **singular**, sem variacoes por estado — WPF-UI
  4.2.0 so tem um). Nomes errados (`CheckBoxCheckGlyphForegroundChecked`) sao silenciosamente
  ignorados.
- **CTRL-006** novo: `ClearButtonEnabled="False"` em `ui:TextBox` para remover o "X" em
  campos de poucos digitos (dd, yyyy, HH, mm) onde a acao do X atrapalha a visualizacao.
- **CTRL-007** novo: ProgressRing colorido via `ProgressRingForegroundThemeBrush` (unico
  resource util + `ProgressRingBackgroundThemeBrush`). Extensivel para qualquer brand color
  via override global.
- **DRY-001** novo: eliminar blocos `<ui:Button.Style>` inline duplicados em abas/toolbars
  usando um Style compartilhado em `App.xaml` + `Tag="{Binding IsXxxVisible}"`. DataTrigger
  no Self.Tag reduz 7+ blocos de 9 linhas a 1 Style + 1 atributo por botao.
- **RES-001** novo: descobrir nomes exatos dos resources do WPF-UI via
  `strings Wpf.Ui.dll | grep -oE 'CheckBox[A-Za-z]+'` (ou PowerShell: `Select-String`).
  Evita chutar nomes que nao existem — convencao do WPF-UI 4.2.0 nem sempre segue o padrao
  WinUI/FluentUI.
- **Anti-padrao #12** novo: `<Style TargetType="ui:Button">` sem
  `BasedOn="{StaticResource {x:Type ui:Button}}"` substitui o template padrao e perde todo
  o visual Fluent.
- **Anti-padrao #13** novo: tentar setar `button.Foreground`/`.Background` via code-behind
  em ToggleButton/Button WPF-UI quando `IsChecked=True` ou quando hover ativo — o template
  tem precedencia via TargetName/DynamicResource. Fix: override do DynamicResource.
- **Anti-padrao #14** novo: chutar nome de DynamicResource do WPF-UI. Verifique antes via
  inspecao do DLL.
- **Detalhe Critico #11** novo: `ControlTemplate.Triggers` com `Setter TargetName="X"`
  vencem Style.Setter externos porque escrevem no elemento interno. Para alterar
  comportamento de hover/pressed/checked em controles WPF-UI, SEMPRE override o
  DynamicResource, nao o property do controle.
- **Reorganizacao:** BRAND-001, CTRL-004 a CTRL-007 e RES-001 ficam como stubs compactos
  no SKILL.md; recipes completos em `references/wpfui-theming-overrides.md`. Reduz SKILL.md
  ~400 linhas para ficar alinhado com principio de progressive disclosure.
- **Description expandida** no frontmatter para cobrir keywords de branding/theming/resource
  discovery.

## v1.4.0 (2026-04-09)

- FORM-004 novo: separador sutil entre grupos de campos em Grid. Usa `Border` com
  `BorderThickness="0,0,0,1"` e `DividerStrokeColorDefaultBrush` em row dedicada.
  Anti-padrao documentado: nunca compartilhar row do separador com conteudo (causa
  sobreposicao).
- Anti-padrao #11 novo: Border separador na mesma row que conteudo causa sobreposicao
  visual.

## v1.3.0 (2026-04-08)

- FORM-002 corrigido: exemplo do UserControl com `Height="32"` e ComboBox FontSize=13
  causava clipping vertical do texto ("Mar.", "Feb." cortados). MinHeight nos filhos nao
  resolve.
- FORM-003 novo (chamada curta no SKILL.md, recipe completo em `references/form-design.md`):
  estilos implicitos em `<StackPanel.Resources>` tem blast radius indesejado em paginas com
  layouts mistos (form vertical + StackPanel horizontal). Quebra alinhamento de controles
  fora do form.
- Anti-padrao #8 reescrito: o pai UserControl com Height fixo limita o espaco total,
  MinHeight nos filhos nao recupera. Prefira `MinHeight` no proprio UserControl ou
  auto-tamanho.
- Detalhe Critico #9 novo: texto clipado em controle Fluent quase sempre e altura, nao
  largura. Antes de aumentar Width, checar Height do pai e do controle.
- Passo 3 (Verificar): nota sobre process restart para mudancas em UserControl que vive em
  DLL referenciada — `dotnet build` nao basta.

## v1.2.0 (2026-04-06)

- LAYOUT-001 expandido: variante para paginas com DataGrid (sem ScrollViewer explicito)
- CTRL-003 novo: SymbolIcon sharing bug em DataGrid — icons em Style.Setter.Value sao
  compartilhados entre linhas
- DataGrid RowHeight recomendado atualizado: 30px para legibilidade confortavel
- Anti-padrao #9: SymbolIcon em Setter.Value dentro de DataGridTemplateColumn

## v1.1.0 (2026-04-01)

- Deep dive no WPF-UI: catalogo completo de 90+ controles em
  `references/wpfui-controls-catalog.md`
- ControlAppearance enum (Primary, Danger, Success, Caution) para semantica de cores
- Accent color system (brushes de accent do sistema)
- DI services: IContentDialogService, ISnackbarService pattern
- Controles novos documentados: NumberBox, AutoSuggestBox, ToggleSwitch, ContentDialog,
  Snackbar, Flyout, CalendarDatePicker, PassiveScrollViewer
- FontTypography completado: TitleLarge (40px), Display (68px)
- SystemThemeWatcher e Window backdrop types
- 6 URLs novas em sources.md (API reference, Gallery app, source code)

## v1.0.0 (2026-04-01)

- Criacao inicial da skill
- Cookbook: toolbar fixa com NavigationView, Grid vs StackPanel, espacamento Fluent, sizing
  de controles
- Fluent Design tokens: spacing ramp, type ramp, dark theme colors, WCAG
- 6 referencias detalhadas (layout, form, tipografia, controls, wpfui, sources)
