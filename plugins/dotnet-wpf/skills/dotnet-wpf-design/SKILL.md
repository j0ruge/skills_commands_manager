---
name: dotnet-wpf-design
description: Professional WPF/XAML design guide — Fluent Design (90+ controls, DataGrid icons, RowHeight), layout troubleshooting (ScrollViewer, toolbar, form spacing), control sizing, dark theme, branding. MVVM and E2E live in sibling skills. Triggers — WPF design, XAML layout, Fluent, DataGrid icon, form spacing, dark theme.
---

# dotnet-wpf-design

Skill para diagnosticar e corrigir problemas de design em interfaces WPF/XAML, aplicando
boas praticas do Microsoft Fluent Design System e WPF-UI.

Usa **progressive disclosure** — este arquivo contem o workflow, cookbook de solucoes e
tabela de tokens essenciais. Guias detalhados com exemplos completos ficam em `references/`
e sao lidos sob demanda.

---

## Versao e Changelog

Historico completo em `CHANGELOG.md` (ao lado deste arquivo). As duas versoes mais
recentes ficam aqui para contexto rapido.

**v1.6.0** (2026-04-16) — Confirmar antes de acoes destrutivas
- **CTRL-008** novo: padrao "guard before mutate" para ContentDialog. Botoes que
  sobrescrevem estado (Load Last Export, Reset, Restore, Discard) chamam o dialogo
  como **primeira linha** do handler e fazem early-return em
  `result != ContentDialogResult.Primary` — preserva o trabalho do usuario se ele
  cancelar. Inclui criterio "sempre confirmar vs. dirty-tracking" (sempre vence
  quando o estado raramente esta vazio) e regras de UX (texto do botao descreve a
  acao, `Appearance="Danger"` so quando irreversivel, dialog mora no code-behind).
- **Detalhe Critico #7** expandido: lista explicita de aliases comuns
  (`ControlAppearance`, `SymbolIcon`, `SymbolRegular`, `SimpleContentDialogCreateOptions`,
  `ContentDialogResult`). `ContentDialogResult` em particular e facil de esquecer
  porque so aparece quando voce troca "single OK" por "Primary + Close".

**v1.5.0** (2026-04-14) — Theming overrides e branding
- Cookbook: BRAND-001 (brand color em Primary sem delay), CTRL-004 (texto branco em
  ToggleButton checked), CTRL-005 (cor do CheckBox), CTRL-006 (ClearButtonEnabled=False),
  CTRL-007 (cor do ProgressRing), DRY-001 (Style compartilhado + Tag binding para abas),
  RES-001 (como descobrir nomes de resources do WPF-UI via `strings Wpf.Ui.dll`).
- Recipes detalhadas de BRAND-001/CTRL-004/5/6/7/RES-001 em
  `references/wpfui-theming-overrides.md` (stubs compactos neste SKILL.md).
- Anti-padroes: #12 (`Style` sem `BasedOn` quebra Fluent), #13 (`control.Foreground`
  via code-behind perde para template), #14 (chutar nome de DynamicResource).
- Detalhe Critico #11: regra canonica sobre precedencia de `ControlTemplate.Triggers`
  com `TargetName` sobre Style externo — override de DynamicResource e a unica forma
  confiavel de customizar estados de template.

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

### BRAND-001: Aplicar brand color em botoes Primary (sem delay no hover)

**Sintoma:** Botao `Appearance="Primary"` com brand color volta para cinza no hover e
retorna ao brand so quando o mouse sai — impressao de delay.

**Causa:** `ControlTemplate.Triggers` usa `DynamicResource AccentButtonBackgroundPointerOver`
em elemento interno via `TargetName`. Style externo no Background da Button nao vence
(veja Detalhe Critico #11).

**Fix:** Override dos 7 resources `AccentButton*` em `App.xaml`. O template passa a
aplicar brand color em todas as transicoes sem delay.

Recipe completo com exemplo XAML, lista exata dos resources (Background, Foreground,
BorderBrushPressed) e o principio "override de resources >> override de properties" em
`references/wpfui-theming-overrides.md` secao BRAND-001.

---

### CTRL-004: ToggleButton com texto branco quando IsChecked=True

**Sintoma:** `btnYes.Foreground = Brushes.White` via code-behind nao funciona quando o
ToggleButton fica checked — texto continua escuro no fundo colorido.

**Causa:** Template aplica `TextElement.Foreground` no ContentPresenter via
`{DynamicResource ToggleButtonForegroundChecked}` (veja Detalhe Critico #11).

**Fix:** Override local no `UserControl.Resources`:
```xml
<UserControl.Resources>
    <SolidColorBrush x:Key="ToggleButtonForegroundChecked" Color="White" />
    <SolidColorBrush x:Key="ToggleButtonForegroundCheckedPointerOver" Color="White" />
    <SolidColorBrush x:Key="ToggleButtonForegroundCheckedPressed" Color="White" />
</UserControl.Resources>
```

Recipe completo (MultiTrigger do template, escopo de override, lookup dinamico) em
`references/wpfui-theming-overrides.md` secao CTRL-004.

---

### CTRL-005: CheckBox — customizar cor do checkmark e fundo

**Atencao aos nomes** — WPF-UI 4.2.0 tem convencao propria, diferente de WinUI 3.
Os resources que existem:

- `CheckBoxCheckBackgroundFillChecked` (+ `PointerOver`, `Pressed`) — fundo do quadrado
- `CheckBoxCheckGlyphForeground` — cor do ✓ (**singular**, SEM sufixo de estado!)

Nomes comuns que **nao existem** (serao silenciosamente ignorados — veja Anti-padrao #14):
`CheckBoxCheckGlyphForegroundChecked`, `CheckBoxCheckBackgroundStrokeChecked*`,
`CheckBoxCheckBackgroundFillCheckedDisabled`.

Recipe completo em `references/wpfui-theming-overrides.md` secao CTRL-005. Para descobrir
nomes de qualquer outro controle, veja RES-001 (mesmo arquivo).

---

### CTRL-006: `ClearButtonEnabled="False"` em campos curtos

Em `ui:TextBox` com `MaxLength=2-4` (dd, yyyy, HH, mm), o botao X da WPF-UI sobrepoe o
digito sem agregar valor (Backspace em 2-4 chars e trivial). Setar `ClearButtonEnabled="False"`.

```xml
<ui:TextBox x:Name="txtDay" Width="40" MaxLength="2"
            PlaceholderText="dd" ClearButtonEnabled="False" />
```

**Usar em:** campos de 1-5 chars. **NAO usar em:** campos longos (nome, comentarios, paths).

---

### CTRL-007: Cor customizada do ProgressRing

WPF-UI 4.2.0 expoe apenas 2 resources para ProgressRing:

```xml
<!-- App.xaml -->
<SolidColorBrush x:Key="ProgressRingForegroundThemeBrush" Color="#DF0024" />
<SolidColorBrush x:Key="ProgressRingBackgroundThemeBrush" Color="#333333" />
```

`Foreground` = arco animado; `Background` = circulo estatico. Override global afeta todos
os `<ui:ProgressRing />` do app.

---

### CTRL-008: ContentDialog para confirmar acoes destrutivas (guard before mutate)

**Problema:** Botoes que sobrescrevem o estado da UI (Load Last Export, Reset Form,
Restore Defaults, Discard Changes) executam direto. Um clique acidental apaga
trabalho do usuario sem chance de desfazer — snackbar de "sucesso" depois nao ajuda.

**Solucao:** Mostrar `ContentDialog` Fluent **antes** de qualquer leitura de I/O ou
mutacao do view-model. Se o usuario cancelar, retornar imediatamente — nada e
tocado, nada e lido. O custo e um clique extra; o ganho e que a acao vira reversivel
por padrao.

```csharp
private async void BtnLoadLastExport_Handler()
{
    // Guard antes de qualquer leitura/mutacao. Cancelar => preserva o trabalho atual.
    var confirm = await _contentDialogService.ShowSimpleDialogAsync(new SimpleContentDialogCreateOptions
    {
        Title = "Load Last Export",
        Content = "This will replace the current form data with the last exported report. "
                + "Any unsaved changes will be lost.\n\nDo you want to continue?",
        PrimaryButtonText = "Replace data",
        CloseButtonText = "Cancel"
    });
    if (confirm != ContentDialogResult.Primary) return;

    // ... so agora le do disco e chama _viewModel.SetSharedData(...) etc.
}
```

**Regras do padrao:**

1. **Confirmar antes de qualquer side-effect.** A chamada do diálogo é a primeira
   linha do handler. Não leia arquivo, nem chame service, nem mude flag — se o
   usuário cancelar, o estado anterior tem que estar 100% intacto.
2. **`ContentDialogResult.Primary` = confirmou; qualquer outro valor = cancelou.**
   `Close` (botão Cancel ou tecla Esc) e `None` (clique fora, se permitido) caem no
   mesmo `return`. Não tente diferenciar — o usuário não confirmou, ponto.
3. **Texto do botão Primary descreve a ação, não "OK".** "Replace data", "Discard
   changes", "Delete report" — o usuário precisa ler o botão e saber o que vai
   acontecer. Evite "Yes/No" genérico (Fluent guidance).
4. **Use `Appearance="Danger"` no Primary se a ação for irreversível** (delete,
   force-overwrite de arquivo). Para overwrite de UI in-memory (caso acima), o
   default já basta — não precisa pintar de vermelho.

**Sempre confirmar vs. so quando "dirty":** dirty-tracking parece a solucao limpa,
mas exige snapshot do estado original + comparacao confiavel a cada interacao —
escopo grande, alto risco de false-negatives (que recriam o bug original). Se o
estado raramente esta vazio (formulario auto-preenchido apos analise, lista
populada por API, etc.), **sempre confirmar** e o trade-off correto: 1 clique
extra contra trabalho perdido. Implementar dirty-tracking so se a confirmacao
realmente cria friccao mensuravel no fluxo principal.

**Onde mora:** code-behind da Page (`*Page.xaml.cs`), nao no ViewModel. Pelas
regras de UI decoupling, dialogs vivem na camada UI — o command do ViewModel
dispara um evento, o code-behind escuta, mostra o diálogo e só chama de volta o
`viewModel.DoTheThing()` se confirmado.

**`using` necessario:** o tipo `ContentDialogResult` mora em `Wpf.Ui.Controls` e
quase sempre conflita com `System.Windows.Controls`. Adicione um alias seguindo o
padrão dos outros tipos da WPF-UI no arquivo (veja Detalhe Critico #7):
```csharp
using ContentDialogResult = Wpf.Ui.Controls.ContentDialogResult;
```

---

### DRY-001: Estilo compartilhado para aba ativa (toolbars/tabs)

**Problema:** Paginas com toolbar de 3-5 botoes que destacam a aba ativa acabam
com `<ui:Button.Style>` inline duplicado. Cada botao tem 9 linhas de XAML identicas
variando so o Binding path. Com 7 abas em 2 paginas, sao 63 linhas redundantes.

```xml
<!-- ❌ ANTES: 9 linhas de Style inline por botao, repetido 7 vezes -->
<ui:Button Content="VDR Form" Command="{Binding ShowVDRFormCommand}">
    <ui:Button.Style>
        <Style TargetType="ui:Button" BasedOn="{StaticResource {x:Type ui:Button}}">
            <Setter Property="Appearance" Value="Secondary" />
            <Style.Triggers>
                <DataTrigger Binding="{Binding IsTestReportVisible}" Value="True">
                    <Setter Property="Appearance" Value="Primary" />
                </DataTrigger>
            </Style.Triggers>
        </Style>
    </ui:Button.Style>
</ui:Button>
```

**Solucao:** Um Style compartilhado em `App.xaml` + `Tag` binding:

```xml
<!-- App.xaml -->
<Style x:Key="ActiveTabButton" TargetType="ui:Button"
       BasedOn="{StaticResource {x:Type ui:Button}}">
    <Setter Property="Appearance" Value="Secondary" />
    <Style.Triggers>
        <DataTrigger Binding="{Binding RelativeSource={RelativeSource Self}, Path=Tag}"
                     Value="True">
            <Setter Property="Appearance" Value="Primary" />
        </DataTrigger>
    </Style.Triggers>
</Style>
```

Cada botao vira uma unica linha:

```xml
<!-- ✅ DEPOIS: 1 linha por botao -->
<ui:Button Content="VDR Form"
           Style="{StaticResource ActiveTabButton}"
           Tag="{Binding IsTestReportVisible}"
           Command="{Binding ShowVDRFormCommand}" />
```

**Por que `Tag` funciona:** `Tag` e uma `DependencyProperty` herdada de
`FrameworkElement` (tipo `object`). Bindar a uma prop bool a deixa boxed true/false.
O `DataTrigger` sobre `Self.Tag` converte "True"/"False" string ao tipo correto via
type coercion. Padrao WPF standard e estavel.

**Funciona em qualquer DRY com N botoes compartilhando logica** — nao so abas.

---

### RES-001: Descobrindo nomes exatos de DynamicResource do WPF-UI

Nomes errados de resources do WPF-UI sao **silenciosamente ignorados** (Anti-padrao #14).
Antes de usar qualquer `x:Key` em override, verifique que existe no `Wpf.Ui.dll`.

**Quick command (Git Bash / WSL):**
```bash
DLL="$HOME/.nuget/packages/wpf-ui/4.2.0/lib/net8.0-windows7.0/Wpf.Ui.dll"
grep -a "CheckBox" "$DLL" | tr '\0' '\n' | grep -oE "CheckBox[A-Za-z]+" | sort -u
```

PowerShell equivalente, localizacao exata do DLL, exemplos por controle e catalogo
parcial de resources descobertos em `references/wpfui-theming-overrides.md` secao RES-001.

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

12. **`<Style TargetType="ui:Button">` sem `BasedOn`** — definir um Style explicito
    para um controle WPF-UI sem `BasedOn="{StaticResource {x:Type ui:Button}}"`
    **substitui** o template padrao, perdendo todo o visual Fluent (padding, bordas
    arredondadas, hover suave, icones, etc.). Sintoma: o botao fica com a aparencia
    crua do `ButtonBase` do WPF (retangulo cinza sem estilo).
    **Fix:** sempre incluir `BasedOn` quando criar Style para controles do WPF-UI:
    ```xml
    <Style TargetType="ui:Button" BasedOn="{StaticResource {x:Type ui:Button}}">
        <Setter Property="Appearance" Value="Secondary" />
    </Style>
    ```

13. **Setar `control.Foreground`/`.Background` em controle WPF-UI com template trigger
    ativo** — atribuicao via code-behind ou Style externo nao vence quando o template
    tem `Setter TargetName="X"` aplicando um `DynamicResource` em elemento interno.
    Sintoma classico: hover/pressed/checked ignoram a cor setada.
    **Ver Detalhe Critico #11 para a regra geral e recipes por controle (BRAND-001,
    CTRL-004, CTRL-005).**

14. **Chutar nomes de DynamicResource do WPF-UI** — nomes tipo `ButtonBackgroundChecked`,
    `CheckBoxCheckGlyphForegroundChecked`, `AccentButtonBorderBrush` seguem convencao
    WinUI/WinRT mas **nao existem** no WPF-UI 4.2.0. Overrides com nomes errados sao
    silenciosamente ignorados (sem erro, sem warning) — voce perde tempo debugando
    algo que nunca foi aplicado.
    **Fix:** sempre verificar no DLL antes de usar. Veja RES-001 para o comando
    de extracao.

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
   WPF-UI:
   ```csharp
   using ControlAppearance = Wpf.Ui.Controls.ControlAppearance;
   using SymbolIcon = Wpf.Ui.Controls.SymbolIcon;
   using SymbolRegular = Wpf.Ui.Controls.SymbolRegular;
   using SimpleContentDialogCreateOptions = Wpf.Ui.SimpleContentDialogCreateOptions;
   using ContentDialogResult = Wpf.Ui.Controls.ContentDialogResult;
   ```
   `ContentDialogResult` em particular e facil de esquecer — voce so precisa dele
   quando troca um `ShowSimpleDialogAsync` "single OK" por um com
   `PrimaryButtonText`+`CloseButtonText` (CTRL-008). Sem o alias, o codigo compila
   mas resolve para o tipo errado ou da erro de ambiguidade dependendo dos outros
   usings do arquivo.

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

11. **Hierarquia de precedencia WPF para triggers do template** — para customizar
    aparencia de controles WPF-UI em estados (hover, pressed, checked), **sempre
    sobrescreva os `DynamicResource` que o template consulta, NUNCA as properties
    do controle via Style externo ou code-behind**. O `ControlTemplate.Triggers`
    com `Setter TargetName="X" Property="Y" Value="{DynamicResource Z}"` aplica o
    valor no elemento INTERNO do template — esse escreve tem precedencia sobre:
    - Setters de Style externo (mesmo com `BasedOn`)
    - Atribuicoes via code-behind (`button.Background = ...`)
    - TemplateBinding de outras properties

    **Regra pratica:** se voce tentar alterar cor e o controle "volta" no
    hover/pressed/checked, o problema nao e seu Style — e que existe um DynamicResource
    sendo aplicado em algum elemento interno via `TargetName`. Identifique o resource
    via RES-001 e sobrescreva no escopo apropriado (local = UserControl.Resources,
    global = App.xaml).

    Exemplos na sessao onde este padrao apareceu:
    - Botao Primary com brand color voltando para azul no hover → BRAND-001
    - ToggleButton checked com texto escuro sobre fundo colorido → CTRL-004
    - CheckBox glyph da cor errada → CTRL-005

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
| `references/wpfui-theming-overrides.md` | Recipes detalhadas de BRAND-001, CTRL-004/5/6/7, RES-001 — customizar brand color em Primary buttons, cor de ToggleButton checked, CheckBox, ProgressRing, e descobrir nomes de resources do WPF-UI |
| `references/sources.md` | URLs de documentacao oficial e fontes da pesquisa |
