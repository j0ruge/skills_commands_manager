---
name: dotnet-wpf-design
description: >
  Guia de design profissional para WPF/XAML com Fluent Design (WPF-UI). Catalogo de solucoes
  documentadas para problemas de layout, espacamento, tipografia, sizing de controles e dark
  theme. Use quando o usuario quiser: corrigir layout de formulario WPF; ajustar espacamento
  entre campos; resolver toolbar/header que rola junto com conteudo; aumentar tamanho de
  controles pequenos ou com texto cortado; melhorar respiro visual entre secoes; aplicar
  tipografia Fluent Design; usar cores corretas de dark theme; diagnosticar problemas de
  ScrollViewer aninhado; alinhar labels com campos; auditar qualidade visual de uma pagina
  XAML. Tambem use quando o usuario mencionar "design WPF", "layout XAML", "campos pequenos",
  "texto cortado", "espacamento", "respiro", "controle apertado", "formulario feio",
  "dark theme cores", "Fluent Design tokens", "ScrollViewer problema", ou "toolbar rola".
  NAO use para: setup inicial de projeto (use dotnet-desktop-setup), MVVM/ViewModel (use
  dotnet-wpf-mvvm), testes E2E (use dotnet-wpf-e2e-testing), logica de negocio, APIs, deploy.
---

# dotnet-wpf-design

Skill para diagnosticar e corrigir problemas de design em interfaces WPF/XAML, aplicando
boas praticas do Microsoft Fluent Design System e WPF-UI.

Usa **progressive disclosure** — este arquivo contem o workflow, cookbook de solucoes e
tabela de tokens essenciais. Guias detalhados com exemplos completos ficam em `references/`
e sao lidos sob demanda.

---

## Versao e Changelog

**v1.4.0** (2026-04-09)
- FORM-004 novo: separador sutil entre grupos de campos em Grid. Usa `Border` com `BorderThickness="0,0,0,1"` e `DividerStrokeColorDefaultBrush` em row dedicada. Anti-padrao documentado: nunca compartilhar row do separador com conteudo (causa sobreposicao).
- Anti-padrao #11 novo: Border separador na mesma row que conteudo causa sobreposicao visual.

**v1.3.0** (2026-04-08)
- FORM-002 corrigido: exemplo do UserControl com `Height="32"` e ComboBox FontSize=13 causava clipping vertical do texto ("Mar.", "Feb." cortados). MinHeight nos filhos nao resolve.
- FORM-003 novo (chamada curta no SKILL.md, recipe completo em `references/form-design.md`): estilos implicitos em `<StackPanel.Resources>` tem blast radius indesejado em paginas com layouts mistos (form vertical + StackPanel horizontal). Quebra alinhamento de controles fora do form.
- Anti-padrao #8 reescrito: o pai UserControl com Height fixo limita o espaco total, MinHeight nos filhos nao recupera. Prefira `MinHeight` no proprio UserControl ou auto-tamanho.
- Detalhe Critico #9 novo: texto clipado em controle Fluent quase sempre e altura, nao largura. Antes de aumentar Width, checar Height do pai e do controle.
- Passo 3 (Verificar): nota sobre process restart para mudancas em UserControl que vive em DLL referenciada — `dotnet build` nao basta.

**v1.2.0** (2026-04-06)
- LAYOUT-001 expandido: variante para paginas com DataGrid (sem ScrollViewer explicito)
- CTRL-003 novo: SymbolIcon sharing bug em DataGrid — icons em Style.Setter.Value sao compartilhados entre linhas
- DataGrid RowHeight recomendado atualizado: 30px para legibilidade confortavel
- Anti-padrao #9: SymbolIcon em Setter.Value dentro de DataGridTemplateColumn

**v1.1.0** (2026-04-01)
- Deep dive no WPF-UI: catalogo completo de 90+ controles em `references/wpfui-controls-catalog.md`
- ControlAppearance enum (Primary, Danger, Success, Caution) para semantica de cores
- Accent color system (brushes de accent do sistema)
- DI services: IContentDialogService, ISnackbarService pattern
- Controles novos documentados: NumberBox, AutoSuggestBox, ToggleSwitch, ContentDialog, Snackbar, Flyout, CalendarDatePicker, PassiveScrollViewer
- FontTypography completado: TitleLarge (40px), Display (68px)
- SystemThemeWatcher e Window backdrop types
- 6 URLs novas em sources.md (API reference, Gallery app, source code)

**v1.0.0** (2026-04-01)
- Criacao inicial da skill
- Cookbook: toolbar fixa com NavigationView, Grid vs StackPanel, espacamento Fluent, sizing de controles
- Fluent Design tokens: spacing ramp, type ramp, dark theme colors, WCAG
- 6 referencias detalhadas (layout, form, tipografia, controls, wpfui, sources)

---

## Quando usar

- Campos de formulario muito pequenos ou com texto cortado
- Falta de espacamento/respiro entre campos, secoes ou controles
- Toolbar ou header que rola junto com o conteudo da pagina
- Labels desalinhados ou truncados
- Controles customizados (UserControl) com sizing inadequado
- Cores hardcoded em vez de theme brushes
- FontSize inconsistente entre controles
- Auditar qualidade visual de uma pagina XAML existente
- Planejar layout de nova pagina seguindo Fluent Design

---

## Fluent Design Quick Reference

Estes sao os valores mais usados. Para tabelas completas, leia `references/typography-colors.md`.

### Spacing Ramp (unidade base: 4px)

| Token | Valor | Uso comum |
|-------|-------|-----------|
| XS | 4px | Margem minima entre elementos inline |
| S | 8px | Entre botoes, controle e header |
| M | 12px | Entre controle e label, entre cards |
| L | 16px | Padding de superficie, margem de pagina |
| XL | 20px | Espacamento medio entre secoes |
| XXL | **24px** | **Entre campos de formulario** (padrao Fluent) |
| XXXL | 32px | Entre grupos de campos |

### Control Heights

| Controle | Altura padrao | Altura compacta |
|----------|---------------|-----------------|
| TextBox | 32px | 24px |
| ComboBox | 32-44px | 24px |
| Button | 32px | 24px |
| ToggleButton | 32px | 28px |
| Touch target minimo | 24x24 (WCAG AA) | — |
| Touch target recomendado | 40x40 | — |

### Type Ramp (Windows 11)

| Estilo | Tamanho | Peso | Uso |
|--------|---------|------|-----|
| Caption | 12px | Regular | Textos auxiliares, hints |
| Body | **14px** | Regular | **Labels, texto padrao** |
| Body Strong | 14px | SemiBold | Sub-headers de secao |
| Body Large | 18px | Regular | Subtitulos |
| Subtitle | 20px | SemiBold | Titulos de grupo |
| Title | 28px | SemiBold | Titulo de pagina |
| Title Large | 40px | SemiBold | Hero text, splash |
| Display | 68px | SemiBold | Numeros grandes, dashboards |

### Dark Theme — Cores Essenciais

| Elemento | Cor | Brush WPF-UI |
|----------|-----|-------------|
| Background app | `#202020` | `SolidBackgroundFillColorBase` |
| Card/secao | `#0DFFFFFF` | `CardBackgroundFillColorDefault` |
| Texto primario | `#FFFFFF` | `TextFillColorPrimaryBrush` |
| Texto secundario | `#C5FFFFFF` (~77%) | `TextFillColorSecondaryBrush` |
| Texto desabilitado | `#5DFFFFFF` (~36%) | `TextFillColorDisabledBrush` |
| Borda controle | `#12FFFFFF` | `ControlStrokeColorDefault` |
| Separador/divider | `#15FFFFFF` | `DividerStrokeColorDefault` |

---

## Workflow: 3 Passos

### Passo 1 — Auditar (diagnostico)

Leia o XAML da pagina e aplique este checklist:

**Layout:**
- [ ] Pagina com toolbar/header usa `ScrollViewer.CanContentScroll="False"`?
- [ ] ScrollViewer esta em Grid com `Height="*"`, nao dentro de StackPanel?
- [ ] Nenhum ScrollViewer aninhado desnecessario?
- [ ] Grid principal usa RowDefinitions adequadas (Auto + *)?

**Espacamento:**
- [ ] Rows de formulario tem Margin vertical >= 8px? (ideal: 24px Fluent)
- [ ] Secoes (Border/Card) tem Padding >= 16px?
- [ ] Separacao entre secoes >= 12px?
- [ ] Labels tem margem do campo >= 8px?

**Sizing:**
- [ ] TextBox/ComboBox tem MinHeight >= 32px (ou Height>=36 se FontSize=13)?
- [ ] ToggleButtons tem MinWidth >= 48px e MinHeight >= 28px?
- [ ] ComboBox tem Width suficiente para mostrar conteudo (minimo 80px para 4 chars)?
- [ ] Controles customizados (UserControl) NAO tem `Height` fixo restritivo? (preferir auto-tamanho ou `MinHeight`)
- [ ] DataGrid RowHeight >= 30px? (consistente entre paginas)
- [ ] Texto de ComboBox/TextBox visivel sem clip vertical em abreviacoes (Mar., Sep.) e descenders (g, p, q)?

**Estilos / escopo de Resources:**
- [ ] Nenhum estilo implicito (`<Style TargetType="...">` sem `x:Key`) em `Page.Resources`/`StackPanel.Resources` que afete inputs em layouts mistos? (use Margin cirurgico ou `x:Key` + `StaticResource` — veja FORM-003)

**DataGrid Icons:**
- [ ] SymbolIcon/Image em DataGridTemplateColumn usa DataTemplate.Triggers com Visibility?
      (NAO Style.Setter.Value — causa sharing bug, icone aparece so em 1 linha)

**Tipografia:**
- [ ] Body text usa FontSize >= 14px?
- [ ] Headers de secao usam FontSize >= 14px SemiBold?
- [ ] Labels usam Foreground com contraste >= 4.5:1 vs background?
- [ ] Nenhum FontSize < 12px (minimo legivel)?

**Theme:**
- [ ] Cores usam DynamicResource brushes em vez de valores hardcoded?
- [ ] BorderBrush usa theme brush em vez de `#555`?
- [ ] Foreground de labels usa `TextFillColorSecondaryBrush` em vez de `#B0B0B0`?

### Passo 2 — Corrigir

Para cada problema encontrado, consulte o cookbook abaixo e aplique a solucao documentada.
Para detalhes e exemplos completos, leia o arquivo correspondente em `references/`.

### Passo 3 — Verificar

1. `dotnet build` — confirmar que compila sem erros
2. Teste visual — abrir a aplicacao e verificar:
   - Controles legiveis com texto completo visivel
   - Espacamento confortavel entre campos
   - Toolbar fixa ao rolar conteudo
   - Contraste adequado entre texto e fundo

> ⚠️ **Se voce alterou XAML de um UserControl que vive numa biblioteca referenciada**
> (ex.: `VDAControls.dll` consumida pelo executavel principal), o `dotnet build` atualiza
> o DLL no disco, mas o processo da app rodando ainda tem o DLL antigo carregado em
> memoria. **Instrua o usuario a fechar e reabrir a app** para ver as mudancas — o XAML do
> UserControl e compilado em BAML embutido no DLL e so e recarregado no startup do
> processo. Veja Detalhe Critico #10.

---

## Cookbook — Solucoes Documentadas

### LAYOUT-001: Toolbar fixa com WPF-UI NavigationView

**Problema:** Botoes de toolbar rolam junto com o conteudo da pagina quando hospedada
dentro de um `NavigationView` do WPF-UI.

**Causa raiz:** O `NavigationViewContentPresenter` do WPF-UI envolve o conteudo da pagina
em um `DynamicScrollViewer` interno (propriedade `IsDynamicScrollViewerEnabled = true`).
Isso faz com que o Grid inteiro da pagina (incluindo toolbar em Row 0) role.

**Solucao:** Adicionar `ScrollViewer.CanContentScroll="False"` no elemento `<Page>`:

```xml
<Page
    x:Class="MeuProjeto.Pages.MinhaPage"
    xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
    xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
    ScrollViewer.CanContentScroll="False"
    Loaded="Page_Loaded">

    <Grid>
        <Grid.RowDefinitions>
            <RowDefinition Height="Auto" />  <!-- Toolbar: fica fixa -->
            <RowDefinition Height="*" />     <!-- Conteudo: rola independente -->
        </Grid.RowDefinitions>

        <StackPanel Grid.Row="0" Orientation="Horizontal">
            <!-- botoes da toolbar -->
        </StackPanel>

        <ScrollViewer Grid.Row="1" VerticalScrollBarVisibility="Auto">
            <!-- conteudo scrollavel -->
        </ScrollViewer>
    </Grid>
</Page>
```

**Como funciona:** O `NavigationViewContentPresenter` le
`ScrollViewer.GetCanContentScroll(page)`. Quando retorna `false`, seta
`IsDynamicScrollViewerEnabled = false`, removendo o wrapper `DynamicScrollViewer`.

**Variante: Paginas com DataGrid (sem ScrollViewer explicito)**

Paginas que usam DataGrid nao precisam de `<ScrollViewer>` explicito em Row 1 — o DataGrid
tem ScrollViewer interno. Basta `ScrollViewer.CanContentScroll="False"` no `<Page>` para que
o DynamicScrollViewer seja desabilitado e o DataGrid receba altura finita, ativando seu
scroll interno automaticamente:

```xml
<Page
    ScrollViewer.CanContentScroll="False">

    <Grid Margin="16,8">
        <Grid.RowDefinitions>
            <RowDefinition Height="Auto" />  <!-- Toolbar fixa -->
            <RowDefinition Height="*" />     <!-- DataGrid com scroll interno -->
        </Grid.RowDefinitions>

        <StackPanel Grid.Row="0" Orientation="Horizontal" Margin="0,0,0,8">
            <ui:Button Content="Channels" Icon="{ui:SymbolIcon Grid24}" />
        </StackPanel>

        <DataGrid Grid.Row="1"
                  ItemsSource="{Binding Data}"
                  AutoGenerateColumns="False"
                  IsReadOnly="True"
                  RowHeight="30" />
    </Grid>
</Page>
```

Tambem funciona com ListBox virtualizado — o `CanContentScroll="False"` na Page afeta apenas
o DynamicScrollViewer externo. O ListBox interno com `ScrollViewer.CanContentScroll="True"`
continua virtualizando normalmente.

**Referencia:** WPF-UI GitHub Issue #1041, PR #1504

---

### LAYOUT-002: Grid vs StackPanel vs DockPanel

**Regra geral:**
- **Grid** — layout principal de formularios. Define linhas e colunas explicitas.
  Sempre use para alinhar labels com campos.
- **StackPanel** — apenas para listas curtas de elementos inline (botoes de toolbar,
  grupo de toggles). **Nunca** como container principal de formulario.
- **DockPanel** — layout de shell (menu + conteudo + status bar).
  `LastChildFill="True"` para o conteudo principal.

**Por que nao usar StackPanel para formularios:** StackPanel oferece espaco infinito
na direcao de orientacao. Isso impede que controles com `Width="*"` se expandam e
que ScrollViewer calcule a viewport corretamente.

Detalhes em `references/layout-patterns.md`.

---

### LAYOUT-003: ScrollViewer — problemas comuns

**Problema 1: ScrollViewer dentro de StackPanel nao rola**
StackPanel da altura infinita ao ScrollViewer, que entao nao precisa rolar.
**Fix:** Colocar ScrollViewer em Grid com `Height="*"`.

**Problema 2: ScrollViewers aninhados**
Dois ScrollViewers competem pelo scroll do mouse.
**Fix:** Manter apenas um ScrollViewer por eixo. O interno rola conteudo, o externo
nao deve existir (ou ser desabilitado).

Detalhes em `references/layout-patterns.md`.

---

### FORM-001: Espacamento entre campos de formulario

**Problema:** Campos de formulario muito juntos, sem respiro visual.

**Solucao Fluent Design:**

| Contexto | Margin recomendado |
|----------|--------------------|
| Entre campos (row margin) | `Margin="0,12,0,0"` (compacto) ou `Margin="0,24,0,0"` (padrao) |
| Entre grupos/secoes | `Margin="0,32,0,0"` ou `Margin="0,48,0,0"` |
| Padding de secao (Border) | `Padding="16,12,16,16"` |
| Entre botoes | `Margin="0,0,8,0"` |
| Entre label e campo (vertical) | `Margin="0,0,0,8"` no label |

**Antes (apertado):**
```xml
<RowDefinition Height="Auto" />  <!-- Margin="0,4" = 4px, muito pouco -->
<TextBlock Margin="0,4" />
```

**Depois (confortavel):**
```xml
<RowDefinition Height="Auto" />  <!-- Margin="0,12" = 12px compacto -->
<TextBlock Margin="0,12,0,0" />  <!-- ou Margin="0,8" para 8px simetrico -->
```

Detalhes em `references/form-design.md`.

---

### FORM-002: Sizing minimo de controles

**Problema:** TextBox, ComboBox ou controles customizados muito pequenos,
texto cortado ou ilegivel.

**Valores minimos recomendados:**

| Controle | MinHeight | MinWidth | FontSize |
|----------|-----------|----------|----------|
| TextBox | 32px | — | 14px (Body) |
| ComboBox | 32px | 100px | 14px |
| ToggleButton | 28px | 48px | 12px (Caption) |
| UserControl (date/time) | 32px | — | 13-14px |
| ComboBox (mes abreviado) | 32px | 80px | 13px |
| TextBox (2 digitos) | 32px | 40px | 13px |
| TextBox (4 digitos) | 32px | 55px | 13px |

**Exemplo — controle de data (Day / Month / Year):**

```xml
<!-- ✅ Auto-tamanho: o UserControl cresce conforme o filho mais alto -->
<UserControl>
    <StackPanel Orientation="Horizontal" VerticalAlignment="Center">
        <TextBox  Width="40" FontSize="13" />
        <TextBlock Text="/" Margin="4,0" FontSize="13" />
        <!-- Height>=36 para FontSize=13 nao clipar texto Fluent verticalmente -->
        <ComboBox Width="80" FontSize="13" Height="36" />
        <TextBlock Text="/" Margin="4,0" FontSize="13" />
        <TextBox  Width="55" FontSize="13" />
    </StackPanel>
</UserControl>
```

⚠️ **Armadilha frequente:** colocar `Height="32"` no `<UserControl>` parece "padronizar" a
altura, mas a `FontSize="13"` o `ComboBox` Fluent (WPF-UI) precisa de **~36px** para
renderizar abreviacoes como "Jan."/"Feb."/"Mar." sem cortar o caractere final. Resultado:
o texto fica visualmente clipado e o instinto e aumentar `Width` — que NAO resolve, porque
o problema e altura, nao largura. Veja Anti-padrao #8 e Detalhe Critico #9.

Recomendado:
- **Nao** definir `Height` no `<UserControl>` (deixar auto-tamanho); ou
- Definir `MinHeight` (nao `Height`) no UserControl, e/ou
- Garantir que o filho problematico (geralmente o `ComboBox`) tenha `Height` explicito
  suficiente para o `FontSize` em uso.

Detalhes em `references/controls-sizing.md`.

---

### FORM-003: Espacamento entre linhas — evitar estilo implicito amplo

**Problema:** Linhas de formulario "coladas". O reflexo de adicionar
`<Style TargetType="{x:Type TextBox}">` em `<StackPanel.Resources>` ou `<Page.Resources>`
para padronizar `Margin` quebra qualquer layout horizontal da mesma pagina (toolbars,
StackPanel inline, UserControl horizontal) — porque estilos implicitos aplicam-se a TODOS
os elementos do tipo no escopo.

**Regra:** aplique `Margin` cirurgicamente nos inputs do formulario, ou use `Style` com
`x:Key` + `StaticResource` explicito. Estilos implicitos so quando o escopo de Resources
contem APENAS controles de form vertical (raro em paginas reais).

**Onde colocar a margem:** no proprio input, nao no `RowDefinition`. Com `Height="Auto"` a
altura da linha vira `max(label+margem, input)`, e se o input e mais alto que o label, a
margem do label nao cria espaco entre linhas — os inputs vizinhos encostam.

Recipe completo (errado / correto / alternativa com `x:Key`, exemplos XAML, e justificativa
de por que `Margin` no input vence `Margin` no `RowDefinition`) em
`references/form-design.md` na secao "Margin Cirurgico vs Estilo Implicito (FORM-003)".

---

### THEME-001: DynamicResource brushes vs cores hardcoded

**Problema:** Cores como `#B0B0B0`, `#555`, `#444` hardcoded no XAML nao acompanham
mudancas de tema e podem ter contraste inadequado.

**Solucao:** Usar DynamicResource com brushes do WPF-UI:

```xml
<!-- Antes (hardcoded) -->
<TextBlock Foreground="#B0B0B0" />
<Border BorderBrush="#555" />

<!-- Depois (theme-aware) -->
<TextBlock Foreground="{DynamicResource TextFillColorSecondaryBrush}" />
<Border BorderBrush="{DynamicResource ControlStrokeColorDefaultBrush}" />
```

**Mapeamento de cores comuns:**

| Hardcoded | DynamicResource equivalente |
|-----------|-----------------------------|
| `#B0B0B0` (label) | `TextFillColorSecondaryBrush` |
| `#555` (borda) | `ControlStrokeColorDefaultBrush` |
| `#444` (separador) | `DividerStrokeColorDefaultBrush` |
| `White` (texto) | `TextFillColorPrimaryBrush` |
| `#2D2D30` (card bg) | `CardBackgroundFillColorDefaultBrush` |

Detalhes em `references/wpfui-components.md`.

---

### TYPO-001: Tipografia consistente com Type Ramp

**Problema:** FontSize inconsistente entre controles, headers, labels.

**Solucao:** Seguir o type ramp do Windows 11:

```xml
<!-- Titulo da pagina -->
<TextBlock FontSize="28" FontWeight="SemiBold" />  <!-- Title -->

<!-- Header de secao -->
<TextBlock FontSize="14" FontWeight="SemiBold" />  <!-- Body Strong -->

<!-- Label de campo -->
<TextBlock FontSize="14" />  <!-- Body -->

<!-- Texto auxiliar / hint -->
<TextBlock FontSize="12" />  <!-- Caption -->
```

**Com WPF-UI (preferivel):**
```xml
<ui:TextBlock FontTypography="Title" Text="Titulo" />
<ui:TextBlock FontTypography="BodyStrong" Text="Secao" />
<ui:TextBlock FontTypography="Body" Text="Label" />
<ui:TextBlock FontTypography="Caption" Text="Hint" />
```

Detalhes em `references/typography-colors.md`.

---

### CTRL-001: Catalogo de controles WPF-UI

**Problema:** O projeto usa controles WPF padrao (TextBox, ComboBox) quando existem
equivalentes WPF-UI com funcionalidades extras (PlaceholderText, Icon, ClearButton).

**Controles mais uteis para formularios:**

| Controle WPF-UI | Substitui | Vantagem |
|------------------|-----------|----------|
| `ui:TextBox` | TextBox | PlaceholderText, Icon, ClearButtonEnabled |
| `ui:NumberBox` | TextBox (numerico) | Validacao, Min/Max, SpinButtons, MaxDecimalPlaces |
| `ui:AutoSuggestBox` | TextBox + filtro | Dropdown de sugestoes, busca integrada |
| `ui:ToggleSwitch` | CheckBox/ToggleButton | On/Off semantico, OnContent/OffContent |
| `ui:CalendarDatePicker` | UserControl custom | Calendario popup nativo |
| `ui:ContentDialog` | MessageBox.Show() | Modal async, DI-friendly, Fluent styled |
| `ui:Snackbar` | — | Toast temporario para feedback (sucesso/erro) |

Catalogo completo com exemplos XAML em `references/wpfui-controls-catalog.md`.

---

### CTRL-002: ControlAppearance — semantica de cores em botoes

**Problema:** Botoes importantes (Export PDF, Delete) nao se distinguem visualmente.

**Solucao:** Usar `Appearance` nos `ui:Button`:

```xml
<ui:Button Content="Export PDF" Appearance="Primary" />   <!-- Accent color -->
<ui:Button Content="Delete" Appearance="Danger" />        <!-- Vermelho -->
<ui:Button Content="Save" Appearance="Success" />         <!-- Verde -->
<ui:Button Content="Warning" Appearance="Caution" />      <!-- Laranja -->
<ui:Button Content="Cancel" Appearance="Secondary" />     <!-- Neutro -->
```

Valores disponiveis: Primary, Secondary, Info, Dark, Light, Danger, Success, Caution, Transparent.

---

### CTRL-003: SymbolIcon sharing bug em DataGrid

**Problema:** Em um `DataGridTemplateColumn`, usar `SymbolIcon` dentro de `Style.Setter.Value`
com `DataTrigger` faz o icone aparecer em apenas UMA linha (a ultima renderizada). As demais
linhas ficam vazias.

**Causa raiz:** WPF cria uma unica instancia de `SymbolIcon` no `Setter.Value`. Como um
UIElement so pode ter um pai visual, cada nova linha "rouba" o icone da anterior.

**Errado (icone compartilhado):**
```xml
<DataGridTemplateColumn Header="Level">
    <DataGridTemplateColumn.CellTemplate>
        <DataTemplate>
            <ContentControl>
                <ContentControl.Style>
                    <Style TargetType="ContentControl">
                        <Setter Property="Content">
                            <Setter.Value>
                                <!-- UMA instancia para TODAS as linhas! -->
                                <ui:SymbolIcon Symbol="Info24" Foreground="#3B82F6" />
                            </Setter.Value>
                        </Setter>
                        <Style.Triggers>
                            <DataTrigger Binding="{Binding Type}" Value="Warning">
                                <Setter Property="Content">
                                    <Setter.Value>
                                        <ui:SymbolIcon Symbol="Warning24" Foreground="#F59E0B" />
                                    </Setter.Value>
                                </Setter>
                            </DataTrigger>
                        </Style.Triggers>
                    </Style>
                </ContentControl.Style>
            </ContentControl>
        </DataTemplate>
    </DataGridTemplateColumn.CellTemplate>
</DataGridTemplateColumn>
```

**Correto (icones por linha com Visibility):**
```xml
<DataGridTemplateColumn Header="Level" Width="70">
    <DataGridTemplateColumn.CellTemplate>
        <DataTemplate>
            <Grid HorizontalAlignment="Center" VerticalAlignment="Center">
                <ui:SymbolIcon x:Name="InfoIcon" Symbol="Info24"
                               FontSize="16" Foreground="#3B82F6" Visibility="Visible" />
                <ui:SymbolIcon x:Name="WarningIcon" Symbol="Warning24"
                               FontSize="16" Foreground="#F59E0B" Visibility="Collapsed" />
                <ui:SymbolIcon x:Name="SevereIcon" Symbol="ErrorCircle24"
                               FontSize="16" Foreground="#EF4444" Visibility="Collapsed" />
            </Grid>
            <DataTemplate.Triggers>
                <DataTrigger Binding="{Binding Type}" Value="Warning">
                    <Setter TargetName="InfoIcon" Property="Visibility" Value="Collapsed" />
                    <Setter TargetName="WarningIcon" Property="Visibility" Value="Visible" />
                </DataTrigger>
                <DataTrigger Binding="{Binding Type}" Value="Severe">
                    <Setter TargetName="InfoIcon" Property="Visibility" Value="Collapsed" />
                    <Setter TargetName="SevereIcon" Property="Visibility" Value="Visible" />
                </DataTrigger>
            </DataTemplate.Triggers>
        </DataTemplate>
    </DataGridTemplateColumn.CellTemplate>
</DataGridTemplateColumn>
```

**Por que funciona:** Cada linha recebe sua propria instancia do DataTemplate. Os 3 icones
sao criados por linha, empilhados em Grid, e `DataTemplate.Triggers` alterna `Visibility`.
Sem compartilhamento de UIElement.

**Regra geral:** Nunca coloque UIElements (SymbolIcon, Image, Border, etc.) em `Setter.Value`
de um Style dentro de DataTemplate. Use `DataTemplate.Triggers` com `Visibility` ou
`ContentTemplate` (que cria instancias por uso).

---

### FORM-004: Separador sutil entre grupos de campos em Grid

**Problema:** Em formularios densos com muitos campos dentro de um unico `SectionBorder`,
grupos logicos de campos (ex: dados de identificacao vs datas de validade) ficam colados
sem distincao visual. Usar um `Border` com `BorderThickness="1"` e `CornerRadius="4"`
(estilo "box") envolve o grupo inteiro e destoa do design flat/clean do resto do formulario.

**Solucao:** Usar um `Border` fino em sua **propria RowDefinition dedicada** dentro do Grid,
com apenas a borda bottom (`BorderThickness="0,0,0,1"`) e `Margin="0,8"` para respiro
simetrico. Isso cria uma linha horizontal sutil que separa grupos sem "encaixotar".

```xml
<Grid>
    <Grid.RowDefinitions>
        <RowDefinition Height="Auto" />  <!-- Row N: ultimo campo do grupo A -->
        <RowDefinition Height="Auto" />  <!-- Row N+1: SEPARADOR (row dedicada) -->
        <RowDefinition Height="Auto" />  <!-- Row N+2: primeiro campo do grupo B -->
    </Grid.RowDefinitions>

    <!-- ... campos do grupo A ... -->

    <!-- Row N+1: Separador sutil -->
    <Border Grid.Row="N+1" Grid.Column="0" Grid.ColumnSpan="3"
            BorderBrush="{DynamicResource DividerStrokeColorDefaultBrush}"
            BorderThickness="0,0,0,1" Margin="0,8" />

    <!-- ... campos do grupo B ... -->
</Grid>
```

**Regras:**
- **Sempre use row dedicada** para o separador — nunca compartilhe a row com conteudo.
  Compartilhar causa sobreposicao porque o `Margin` do Border compete com o conteudo da
  mesma row.
- `Margin="0,8"` da 8px acima e abaixo da linha — respiro confortavel sem exagero.
  Aumente para `Margin="0,12"` se precisar de mais respiro.
- Use `DividerStrokeColorDefaultBrush` (nao `ControlStrokeColorDefaultBrush`) — e mais
  sutil, projetado para separadores.
- `ColumnSpan` deve cobrir todas as colunas do Grid.

**Anti-padrao: Border na mesma row que conteudo**

```xml
<!-- ❌ ERRADO: Border na mesma row que o TextBlock — sobrepoe o texto -->
<TextBlock Grid.Row="6" Grid.Column="1" Text="Descricao..." />
<Border Grid.Row="6" Grid.Column="0" Grid.ColumnSpan="3"
        BorderThickness="0,0,0,1" Margin="0,16,0,16" />
<!-- O Margin do Border expande a row e o texto fica atras da linha -->

<!-- ✅ CORRETO: Border em row propria -->
<TextBlock Grid.Row="6" Grid.Column="1" Text="Descricao..." />
<Border Grid.Row="7" Grid.Column="0" Grid.ColumnSpan="3"
        BorderThickness="0,0,0,1" Margin="0,8" />
<TextBlock Grid.Row="8" Grid.Column="0" Text="Proximo campo..." />
```

---

## Anti-padroes desta Skill

1. **StackPanel como container de formulario** — StackPanel da espaco infinito e impede
   controles `Width="*"` de expandir. Use Grid com ColumnDefinitions.

2. **ScrollViewer dentro de StackPanel** — o ScrollViewer recebe altura infinita e nunca
   rola. Sempre coloque ScrollViewer em Grid com `RowDefinition Height="*"`.

3. **Cores hardcoded (#B0B0B0, #555)** — nao acompanham mudanca de tema. Use
   `DynamicResource` com brushes do WPF-UI.

4. **FontSize < 12px** — ilegivel. Minimo absoluto e 12px (Caption). Body text deve
   ser 14px.

5. **Controles sem MinHeight** — TextBox e ComboBox ficam microscopicos quando o conteudo
   e vazio. Sempre defina MinHeight >= 32px.

6. **Margin="0,4" entre campos** — 4px e muito pouco respiro. Minimo recomendado: 8px.
   Padrao Fluent: 24px.

7. **Width fixo em ComboBox muito estreito** — ComboBox com Width=65 nao mostra "Jun."
   completo com padding. Minimo: 80px para meses abreviados.

8. **`Height` fixo em UserControl que envolve controles Fluent** — o atributo `Height` no
   `<UserControl>` limita o espaco total disponivel para os filhos. Definir `MinHeight`
   nos filhos NAO recupera o espaco — o pai ja capou. Pior: a uma `FontSize="13"` o
   `ComboBox`/`TextBox` Fluent (WPF-UI) precisa de ~36px para renderizar texto com
   descenders/pontos sem clipar verticalmente, e `Height="32"` parece "padrao" mas
   visivelmente corta caracteres como "g", "p", ".", produzindo o sintoma classico de
   "texto cortado" — que o desenvolvedor erroneamente tenta resolver aumentando `Width`.
   **Fix:** prefira deixar o UserControl auto-dimensionar (sem `Height`), ou use
   `MinHeight` no proprio UserControl, ou de `Height` explicito ao filho problematico.

9. **SymbolIcon/Image em Style Setter.Value dentro de DataTemplate** — UIElements em
   Setter.Value sao instanciados uma unica vez e compartilhados entre todas as linhas.
   Resultado: so a ultima linha renderizada mostra o icone. Use `DataTemplate.Triggers`
   com Visibility em vez de `Style.Triggers` com Content.

10. **Estilos implicitos em `<StackPanel.Resources>` / `<Page.Resources>` para padronizar
    Margin de inputs** — quando uma pagina mistura grids de formulario (vertical) com
    qualquer `StackPanel Orientation="Horizontal"` (toolbar, grupo de campos inline,
    UserControl horizontal), um estilo implicito como
    `<Style TargetType="{x:Type TextBox}"><Setter Property="Margin" Value="0,4"/></Style>`
    afeta TODOS os TextBoxes filhos — incluindo os horizontais, onde a margem vertical
    extra desalinha a linha. Veja FORM-003 para o recipe correto: aplicar Margin
    cirurgicamente nos inputs do formulario, ou usar `Style` com `x:Key` + `StaticResource`
    explicito.

11. **Border separador na mesma row que conteudo** — colocar um `Border` divisor
    (ex: `BorderThickness="0,0,0,1"`) na mesma `Grid.Row` de um TextBlock ou controle
    causa sobreposicao: o Margin do Border expande a row e o texto fica atras da linha.
    **Fix:** sempre usar uma `RowDefinition Height="Auto"` dedicada para o separador,
    sem nenhum outro elemento nessa row. Veja FORM-004.

---

## Detalhes Criticos (aprendidos nos testes)

1. **ScrollViewer.CanContentScroll="False" e a unica forma confiavel** de desabilitar o
   DynamicScrollViewer do NavigationView no WPF-UI 4.2.0. `ScrollViewer.VerticalScrollBarVisibility="Disabled"` no Page NAO funciona — o NavigationViewContentPresenter ignora essa propriedade.

2. **WPF-UI herda do Frame** — o `NavigationViewContentPresenter` estende `Frame`, nao
   `ContentPresenter`. Isso significa que a pagina nao recebe constraints de tamanho
   automaticamente como em ContentPresenter.

3. **DynamicResource vs StaticResource** — para cores de tema, SEMPRE use `DynamicResource`.
   `StaticResource` nao atualiza quando o tema muda em runtime.

4. **ComboBox items com espacos iniciais** — se os ComboBoxItems usam `Content="   Good"`
   com espacos para padding, considere usar `Padding` em vez de espacos. Espacos podem
   causar problemas ao comparar valores.

5. **ContentDialogHost e o elemento XAML correto** — nao usar `ContentPresenter` ou
   `ContentDialogPresenter`. O elemento correto do WPF-UI 4.2.0 e `<ui:ContentDialogHost>`.

6. **`using Wpf.Ui.Extensions;` necessario para ShowSimpleDialogAsync** — este e um
   extension method, nao um metodo da interface. Sem o using, o codigo compila mas
   o metodo nao e encontrado.

7. **`using Wpf.Ui.Controls;` conflita com System.Windows.Controls** — TextBox, ComboBox,
   Page, Button existem em ambos namespaces. Usar type aliases para tipos especificos do
   WPF-UI: `using ControlAppearance = Wpf.Ui.Controls.ControlAppearance;`

8. **`async void` so em event handlers UI** — metodos como SaveFormDataJSON, LoadFormDataJSON
   que usam `await _contentDialogService.ShowSimpleDialogAsync()` devem ser `async Task`,
   nao `async void`. Excecoes em `async void` nao sao observaveis e podem crashar a app.

9. **Texto clipado em controle Fluent quase sempre e altura, nao largura** — quando um
   `ComboBox`/`TextBox` da WPF-UI mostra "Mar." sem o ponto, "Sep." sem o "p.", ou textos
   com descender (`g`, `p`, `q`) cortados no rodape, o reflexo de aumentar `Width` esta
   errado. Antes de mexer em largura, verificar nesta ordem:
   1. `Height` fixo no `<UserControl>` pai (mais comum — `Height="32"` e classico).
   2. `Height` fixo no proprio controle.
   3. `RowDefinition Height="..."` muito apertado no `Grid` pai.
   4. `MinHeight` < altura natural a essa `FontSize`.

   **Regra pratica:** a `FontSize="13"` o `ComboBox` Fluent precisa de **~36px** de
   altura para renderizar abreviacoes com ponto sem clip. A `FontSize="14"` (Body) precisa
   de **~38-40px**. A `FontSize="12"` (Caption) suporta `Height="32"` na maioria dos casos.

10. **Mudancas em XAML de UserControl em DLL referenciada precisam de process restart** —
    se voce edita `MyControl.xaml` que vive em `VDAControls.csproj` (DLL referenciada por
    `VDRDataAnalyzer.exe`), o XAML e compilado em BAML e embutido no `VDAControls.dll`. O
    processo `VDRDataAnalyzer.exe` carregou esse DLL na memoria no startup e nao recarrega
    automaticamente. `dotnet build` atualiza o DLL no disco mas nao afeta o processo
    rodando. **Sempre instruir o usuario:** "feche e reabra a app para ver as mudancas".

---

## Guias de Referencia (progressive disclosure level 3)

Leia estes arquivos **somente quando necessario** no passo correspondente:

| Arquivo | Leia quando... |
|---------|----------------|
| `references/layout-patterns.md` | Problemas de ScrollViewer, toolbar fixa, Grid vs StackPanel |
| `references/form-design.md` | Espacamento entre campos, label alignment, respiro, FORM-003 (Margin cirurgico vs estilo implicito) |
| `references/typography-colors.md` | FontSize, type ramp, cores dark theme, contraste WCAG |
| `references/controls-sizing.md` | MinHeight/MinWidth, ComboBox, TextBox, touch targets |
| `references/wpfui-components.md` | Card, CardExpander, InfoBar, DynamicResource brushes, ControlAppearance, DI services |
| `references/wpfui-controls-catalog.md` | Catalogo completo de 90+ controles WPF-UI com exemplos XAML |
| `references/sources.md` | URLs de documentacao oficial e fontes da pesquisa |
