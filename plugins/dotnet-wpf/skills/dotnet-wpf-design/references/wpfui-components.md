# WPF-UI Components — Card, InfoBar, Theme Brushes

Guia de componentes WPF-UI para design de formularios e paginas.
Leia quando quiser usar componentes Fluent nativos do WPF-UI.

---

## Card e CardExpander

### ui:Card — Container de conteudo

```xml
<ui:Card Margin="0,8">
    <ui:Card.Header>
        <TextBlock Text="Ship's Details"
                   FontTypography="BodyStrong" />
    </ui:Card.Header>
    <Grid>
        <!-- campos do formulario -->
    </Grid>
    <ui:Card.Footer>
        <TextBlock Text="Informacao adicional"
                   FontTypography="Caption" />
    </ui:Card.Footer>
</ui:Card>
```

### ui:CardExpander — Secao expansivel

Para secoes que podem ser colapsadas:

```xml
<ui:CardExpander Margin="0,8"
                 Header="7. Overall Condition of Equipment"
                 Icon="{ui:SymbolIcon Wrench24}">
    <StackPanel Margin="16">
        <!-- conteudo da secao -->
    </StackPanel>
</ui:CardExpander>
```

**Spacing:** Conteudo interno deve ter `Margin="16"` (indent de 48px recomendado
pelo Fluent Design para conteudo dentro de expander).

### Quando usar Card vs Border

| Cenario | Usar |
|---------|------|
| Secao de formulario simples | Border com Style |
| Secao com header + footer | ui:Card |
| Secao colapsavel | ui:CardExpander |
| Secao com acao (clicavel) | ui:CardControl |

---

## InfoBar — Mensagens Contextuais

Para feedback, avisos ou erros no formulario:

```xml
<ui:InfoBar
    Title="Campos obrigatorios"
    Message="Preencha todos os campos marcados antes de exportar."
    Severity="Warning"
    IsOpen="True"
    IsClosable="True" />
```

**Severidades:**
- `Informational` — azul, informacao geral
- `Success` — verde, operacao concluida
- `Warning` — amarelo, atencao necessaria
- `Error` — vermelho, erro que precisa correcao

---

## DynamicResource Brushes

### Por que DynamicResource e nao StaticResource

`DynamicResource` atualiza automaticamente quando o tema muda em runtime.
`StaticResource` resolve uma vez e nunca atualiza. Para cores de tema,
**sempre** usar `DynamicResource`.

### Brushes Mais Usados

**Texto:**
```xml
<!-- Texto principal (branco em dark) -->
<TextBlock Foreground="{DynamicResource TextFillColorPrimaryBrush}" />

<!-- Labels, texto secundario (~77% branco) -->
<TextBlock Foreground="{DynamicResource TextFillColorSecondaryBrush}" />

<!-- Hints, placeholders (~53% branco) -->
<TextBlock Foreground="{DynamicResource TextFillColorTertiaryBrush}" />

<!-- Desabilitado (~36% branco) -->
<TextBlock Foreground="{DynamicResource TextFillColorDisabledBrush}" />
```

**Bordas e Separadores:**
```xml
<!-- Borda de controle -->
<Border BorderBrush="{DynamicResource ControlStrokeColorDefaultBrush}" />

<!-- Separador/divider -->
<Border BorderBrush="{DynamicResource DividerStrokeColorDefaultBrush}" />

<!-- Borda de card -->
<Border BorderBrush="{DynamicResource CardStrokeColorDefaultBrush}" />
```

**Backgrounds:**
```xml
<!-- Background de card -->
<Border Background="{DynamicResource CardBackgroundFillColorDefaultBrush}" />

<!-- Background de controle -->
<Border Background="{DynamicResource ControlFillColorDefaultBrush}" />
```

---

## Theming Setup

### App.xaml

```xml
<Application.Resources>
    <ResourceDictionary>
        <ResourceDictionary.MergedDictionaries>
            <ui:ThemesDictionary Theme="Dark" />
            <ui:ControlsDictionary />
        </ResourceDictionary.MergedDictionaries>
    </ResourceDictionary>
</Application.Resources>
```

### Aplicar tema programaticamente

```csharp
ApplicationThemeManager.Apply(
    ApplicationTheme.Dark,
    WindowBackdropType.Mica,
    updateAccent: true);
```

---

## SymbolIcon — Icones Disponiveis

WPF-UI inclui Fluent System Icons. Uso:

```xml
<ui:Button Icon="{ui:SymbolIcon DocumentText24}" Content="VDR Form" />
<ui:Button Icon="{ui:SymbolIcon ArrowDownload24}" Content="Export" />
<ui:Button Icon="{ui:SymbolIcon ArrowSync24}" Content="Refresh" />
```

**Cuidado:** Nem todos os icones listados na documentacao existem na versao 4.2.0.
Testar em runtime antes de commitar. Icones que NAO existem incluem:
`SignalStrength24`, `PlugConnected24`.

---

## NavigationView — Configuracao de Header

O header do NavigationView (barra de informacoes do navio) fica fora do scroll:

```xml
<ui:NavigationView>
    <ui:NavigationView.Header>
        <Border Background="#2D2D30" CornerRadius="8" Padding="16,10">
            <!-- informacoes do navio -->
        </Border>
    </ui:NavigationView.Header>
    <!-- menu items -->
</ui:NavigationView>
```

Para que o conteudo da pagina NAO role com o header, adicione
`ScrollViewer.CanContentScroll="False"` na Page (ver `references/layout-patterns.md`).
