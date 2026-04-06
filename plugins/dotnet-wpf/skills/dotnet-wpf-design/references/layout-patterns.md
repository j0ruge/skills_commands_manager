# Layout Patterns — WPF/XAML

Guia detalhado de padroes de layout para WPF com WPF-UI.
Leia quando houver problemas de ScrollViewer, toolbar fixa, ou duvida sobre Grid vs StackPanel.

---

## Toolbar Fixa com WPF-UI NavigationView

### O Problema

WPF-UI `NavigationView` usa `NavigationViewContentPresenter` (que estende `Frame`) para
hospedar paginas. Internamente, envolve o conteudo em um `DynamicScrollViewer` via
propriedade `IsDynamicScrollViewerEnabled` (default: `true`).

Quando uma pagina tem Grid com Row 0 (toolbar) + Row 1 (ScrollViewer), o
`DynamicScrollViewer` externo rola tudo — incluindo a toolbar.

### A Solucao

Adicionar `ScrollViewer.CanContentScroll="False"` no `<Page>`:

```xml
<Page
    ScrollViewer.CanContentScroll="False"
    Loaded="Page_Loaded">

    <Grid>
        <Grid.RowDefinitions>
            <RowDefinition Height="Auto" />  <!-- Toolbar fixa -->
            <RowDefinition Height="*" />     <!-- Conteudo rola -->
        </Grid.RowDefinitions>

        <!-- Toolbar -->
        <StackPanel Grid.Row="0" Orientation="Horizontal" Margin="16,8,16,0">
            <ui:Button Content="Action" Icon="{ui:SymbolIcon Save24}" />
        </StackPanel>

        <!-- Conteudo scrollavel -->
        <ScrollViewer Grid.Row="1" VerticalScrollBarVisibility="Auto" Margin="16,8">
            <StackPanel>
                <!-- campos do formulario -->
            </StackPanel>
        </ScrollViewer>
    </Grid>
</Page>
```

### Como Funciona Internamente

1. `NavigationViewContentPresenter` navega para a pagina
2. Le `ScrollViewer.GetCanContentScroll(page)`
3. Se retorna `false`, seta `IsDynamicScrollViewerEnabled = false`
4. O template remove o wrapper `DynamicScrollViewer`
5. A pagina recebe o espaco real disponivel
6. Grid Row 0 (Auto) = toolbar fixa, Row 1 (*) = ScrollViewer com viewport

### O que NAO funciona

- `ScrollViewer.VerticalScrollBarVisibility="Disabled"` no Page — ignorado
- Setar `IsDynamicScrollViewerEnabled` diretamente — setter e `protected`
- `ScrollViewer.CanContentScroll="True"` — e o default, nao muda nada

### Efeito colateral conhecido

Um usuario reportou que `ScrollViewer.CanContentScroll="False"` pode ocasionalmente
"quebrar cores de font do tema" se a pagina afetada for visitada e depois o usuario
navegar para outras paginas. Edge case raro — monitorar mas nao deve ser problema.

### Variante: Paginas com DataGrid (sem ScrollViewer explicito)

Paginas com DataGrid nao precisam de ScrollViewer explicito — o DataGrid tem scroll interno.
Com `CanContentScroll="False"` no Page, o DynamicScrollViewer e desabilitado e o DataGrid
recebe altura finita, ativando seu scroll automaticamente:

```xml
<Page
    ScrollViewer.CanContentScroll="False">

    <Grid Margin="16,8">
        <Grid.RowDefinitions>
            <RowDefinition Height="Auto" />
            <RowDefinition Height="*" />
        </Grid.RowDefinitions>

        <StackPanel Grid.Row="0" Orientation="Horizontal" Margin="0,0,0,8">
            <ui:Button Content="Channels" />
        </StackPanel>

        <DataGrid Grid.Row="1"
                  ItemsSource="{Binding Data}"
                  RowHeight="30" />
    </Grid>
</Page>
```

Funciona tambem com ListBox virtualizado — `CanContentScroll="False"` na Page afeta
apenas o DynamicScrollViewer externo. ListBox com `CanContentScroll="True"` continua
virtualizando.

**Referencia:** WPF-UI GitHub Issue #1041, PR #1504

---

## Grid — Container Principal de Formularios

### Quando Usar

- **Sempre** para formularios com labels + campos
- Layout de pagina principal (toolbar + conteudo + status bar)
- Qualquer layout que precise de alinhamento entre colunas

### Padrao Label + Campo (2 colunas)

```xml
<Grid>
    <Grid.ColumnDefinitions>
        <ColumnDefinition Width="200" />   <!-- Label fixo -->
        <ColumnDefinition Width="*" />     <!-- Campo expandivel -->
    </Grid.ColumnDefinitions>
    <Grid.RowDefinitions>
        <RowDefinition Height="Auto" />
        <RowDefinition Height="Auto" />
    </Grid.RowDefinitions>

    <TextBlock Grid.Row="0" Grid.Column="0" Text="Ship Name"
               VerticalAlignment="Center" Margin="0,8" />
    <TextBox Grid.Row="0" Grid.Column="1" MinHeight="32" />

    <TextBlock Grid.Row="1" Grid.Column="0" Text="Flag"
               VerticalAlignment="Center" Margin="0,8" />
    <TextBox Grid.Row="1" Grid.Column="1" MinHeight="32" />
</Grid>
```

### Padrao Label + Campo + CheckBox (3 colunas)

```xml
<Grid>
    <Grid.ColumnDefinitions>
        <ColumnDefinition Width="200" />   <!-- Label -->
        <ColumnDefinition Width="*" />     <!-- Campo -->
        <ColumnDefinition Width="Auto" />  <!-- CheckBox/Option -->
    </Grid.ColumnDefinitions>
</Grid>
```

### Grid com RowDefinitions Condensadas (forma inline)

Para formularios longos, RowDefinitions inline sao aceitaveis:

```xml
<Grid.RowDefinitions>
    <RowDefinition Height="Auto" />
    <RowDefinition Height="Auto" />
    <RowDefinition Height="Auto" />
</Grid.RowDefinitions>
```

---

## StackPanel — Apenas para Inline Elements

### Quando Usar

- Toolbar (botoes horizontais)
- Grupo de ToggleButtons (Yes/No/N-A)
- Lista vertical de secoes/cards (dentro de ScrollViewer)

### Quando NAO Usar

- Container principal de formulario — use Grid
- Wrapper de ScrollViewer — use Grid com `Height="*"`
- Layout que precisa de controles `Width="*"` expandiveis

### O Problema do Espaco Infinito

StackPanel da espaco infinito na direcao de orientacao:
- `Orientation="Vertical"` → altura infinita → ScrollViewer nao rola
- `Orientation="Horizontal"` → largura infinita → `Width="*"` nao funciona

```xml
<!-- ERRADO: ScrollViewer nunca rola -->
<StackPanel>
    <StackPanel><!-- toolbar --></StackPanel>
    <ScrollViewer><!-- conteudo --></ScrollViewer>
</StackPanel>

<!-- CORRETO: ScrollViewer rola normalmente -->
<Grid>
    <Grid.RowDefinitions>
        <RowDefinition Height="Auto" />
        <RowDefinition Height="*" />
    </Grid.RowDefinitions>
    <StackPanel Grid.Row="0"><!-- toolbar --></StackPanel>
    <ScrollViewer Grid.Row="1"><!-- conteudo --></ScrollViewer>
</Grid>
```

---

## DockPanel — Layout de Shell

### Quando Usar

- Layout de janela principal (menu + conteudo + status bar)
- Paineis laterais fixos com conteudo central expansivel

```xml
<DockPanel LastChildFill="True">
    <Menu DockPanel.Dock="Top" />
    <StatusBar DockPanel.Dock="Bottom" />
    <NavigationView />  <!-- LastChild: preenche espaco restante -->
</DockPanel>
```

---

## ScrollViewer — Regras de Ouro

1. **Um ScrollViewer por eixo** — nunca aninhar dois ScrollViewers verticais
2. **Sempre em Grid com Height="*"** — nunca dentro de StackPanel
3. **VerticalScrollBarVisibility="Auto"** — mostra barra apenas quando necessario
4. **Conteudo em StackPanel com Width fixo** — para formularios centralizados:

```xml
<ScrollViewer Grid.Row="1" VerticalScrollBarVisibility="Auto" Margin="16,8">
    <StackPanel Width="900">
        <!-- secoes do formulario -->
    </StackPanel>
</ScrollViewer>
```
