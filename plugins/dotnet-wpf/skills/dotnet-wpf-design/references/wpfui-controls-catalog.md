# Catalogo de Controles WPF-UI

Referencia completa dos controles WPF-UI (Wpf.Ui 4.2.0) relevantes para design de formularios
e paginas desktop. Organizados por categoria com exemplos XAML prontos para uso.

Leia quando quiser saber quais controles do WPF-UI estao disponiveis para uma situacao especifica.

---

## 1. Input Controls

### ui:TextBox — TextBox com PlaceholderText e Icon

```xml
<ui:TextBox PlaceholderText="Digite aqui..." />
<ui:TextBox PlaceholderText="Buscar..." ClearButtonEnabled="True"
            Icon="{ui:SymbolIcon Search24}" IconPlacement="Left" />
<ui:TextBox PlaceholderText="Comentarios..." TextWrapping="Wrap"
            AcceptsReturn="True" MinHeight="80" />
```

**Propriedades extras vs TextBox padrao:** `PlaceholderText`, `Icon`, `IconPlacement`,
`ClearButtonEnabled`.

### ui:NumberBox — Input numerico com validacao

```xml
<!-- Basico -->
<ui:NumberBox Value="{Binding Quantidade}" Minimum="0" Maximum="100"
              SmallChange="1" LargeChange="10" PlaceholderText="Qtd" />

<!-- Decimal -->
<ui:NumberBox Value="{Binding Preco}" Maximum="9999.99"
              MaxDecimalPlaces="2" PlaceholderText="Preco" />

<!-- Sem spin buttons -->
<ui:NumberBox Value="{Binding Idade}" SpinButtonPlacementMode="Hidden" />

<!-- Aceita expressoes (ex: 10+5) -->
<ui:NumberBox Value="{Binding Calc}" AcceptsExpression="True" />
```

**Propriedades:** `Value`, `Minimum`, `Maximum`, `SmallChange`, `LargeChange`,
`MaxDecimalPlaces`, `SpinButtonPlacementMode` (Inline|Hidden), `AcceptsExpression`,
`PlaceholderText`, `ValidationMode`.

**Uso recomendado:** Campos de ano, MMSI, gross tonnage, serial numbers.

### ui:PasswordBox — Input de senha

```xml
<ui:PasswordBox PlaceholderText="Senha..." RevealButtonEnabled="True" />
```

### ui:AutoSuggestBox — Busca com sugestoes

```xml
<ui:AutoSuggestBox PlaceholderText="Buscar navio..."
                   OriginalItemsSource="{Binding Navios}"
                   Text="{Binding BuscaTexto, Mode=TwoWay}"
                   UpdateTextOnSelect="True"
                   QuerySubmitted="OnQuery"
                   SuggestionChosen="OnChosen">
    <ui:AutoSuggestBox.Icon>
        <ui:SymbolIcon Symbol="Search24" />
    </ui:AutoSuggestBox.Icon>
</ui:AutoSuggestBox>
```

**Filtro no code-behind:**
```csharp
private void OnTextChanged(AutoSuggestBox sender, AutoSuggestBoxTextChangedEventArgs args)
{
    if (args.Reason == AutoSuggestionBoxTextChangeReason.UserInput)
    {
        sender.ItemsSource = _todosNavios
            .Where(n => n.Contains(args.Text, StringComparison.OrdinalIgnoreCase))
            .Take(10).ToList();
    }
}
```

### ui:ToggleSwitch — Toggle On/Off

```xml
<ui:ToggleSwitch OnContent="Ativado" OffContent="Desativado" />
<ui:ToggleSwitch Content="Modo CoC" LabelPosition="Left" />
```

**Propriedades:** `OnContent`, `OffContent`, `Content`, `LabelPosition` (Left|Right).

---

## 2. Button Variants

### ui:Button — Com ControlAppearance

```xml
<ui:Button Content="Salvar" Appearance="Primary" Icon="{ui:SymbolIcon Save24}" />
<ui:Button Content="Excluir" Appearance="Danger" Icon="{ui:SymbolIcon Delete24}" />
<ui:Button Content="Sucesso" Appearance="Success" />
<ui:Button Content="Atencao" Appearance="Caution" />
<ui:Button Content="Cancelar" Appearance="Secondary" />
<ui:Button Icon="{ui:SymbolIcon Settings24}" ToolTip="Config" />  <!-- Icon-only -->
```

### ControlAppearance Enum

| Valor | Cor | Uso |
|-------|-----|-----|
| Primary | Accent do sistema | Acao principal (Export PDF, Save) |
| Secondary | Neutro | Acoes secundarias |
| Info | Azul | Informacao |
| Danger | Vermelho | Exclusao, acoes destrutivas |
| Success | Verde | Confirmacao, status positivo |
| Caution | Laranja | Avisos, acoes com risco |
| Dark | Escuro | — |
| Light | Claro | — |
| Transparent | Sem fundo | Botoes inline, icones |

### ui:DropDownButton — Botao com menu

```xml
<ui:DropDownButton Content="Opcoes" Icon="{ui:SymbolIcon MoreHorizontal24}">
    <ui:DropDownButton.Flyout>
        <ContextMenu>
            <ui:MenuItem Header="Exportar JSON" Icon="{ui:SymbolIcon Code24}" />
            <ui:MenuItem Header="Exportar PDF" Icon="{ui:SymbolIcon DocumentPdf24}" />
        </ContextMenu>
    </ui:DropDownButton.Flyout>
</ui:DropDownButton>
```

### ui:SplitButton — Acao principal + alternativas

```xml
<ui:SplitButton Content="Export PDF" Icon="{ui:SymbolIcon ArrowDownload24}">
    <ui:SplitButton.Flyout>
        <ContextMenu>
            <ui:MenuItem Header="Export as PDF" />
            <ui:MenuItem Header="Export as JSON" />
        </ContextMenu>
    </ui:SplitButton.Flyout>
</ui:SplitButton>
```

### ui:HyperlinkButton — Link externo

```xml
<ui:HyperlinkButton Content="Documentacao" NavigateUri="https://wpfui.lepo.co/"
                     Icon="{ui:SymbolIcon Link24}" />
```

### ui:Anchor — Hyperlink simples

```xml
<ui:Anchor Content="GitHub" NavigateUri="https://github.com/lepoco/wpfui" />
```

---

## 3. Cards

### ui:Card — Container com header e footer

```xml
<ui:Card Margin="0,8">
    <ui:Card.Header>
        <ui:TextBlock FontTypography="BodyStrong" Text="Detalhes do Navio" />
    </ui:Card.Header>
    <!-- conteudo -->
    <ui:Card.Footer>
        <ui:TextBlock FontTypography="Caption" Text="Ultima atualizacao: hoje" />
    </ui:Card.Footer>
</ui:Card>
```

### ui:CardExpander — Secao colapsavel

```xml
<ui:CardExpander Header="Dados EPIRB" Icon="{ui:SymbolIcon Shield24}" Margin="0,8">
    <StackPanel Margin="16">
        <!-- campos EPIRB -->
    </StackPanel>
</ui:CardExpander>
```

### ui:CardControl — Card com controle lateral (settings pattern)

```xml
<ui:CardControl Icon="{ui:SymbolIcon DarkTheme24}" Margin="0,12,0,0">
    <ui:CardControl.Header>
        <StackPanel>
            <ui:TextBlock FontTypography="Body" Text="Tema escuro" />
            <ui:TextBlock FontTypography="Caption" Text="Selecione o tema da aplicacao"
                          Foreground="{DynamicResource TextFillColorSecondaryBrush}" />
        </StackPanel>
    </ui:CardControl.Header>
    <ui:ToggleSwitch IsChecked="{Binding IsDarkMode}" />
</ui:CardControl>
```

### ui:CardAction — Card clicavel

```xml
<ui:CardAction Icon="{ui:SymbolIcon Document24}" IsChevronVisible="True"
               Click="OnCardClick">
    <ui:TextBlock FontTypography="Body" Text="Ver relatorio" />
</ui:CardAction>
```

---

## 4. Dialogs e Notificacoes

### ContentDialog — Modal dentro do app

**Setup no MainWindow.xaml:**
```xml
<Grid>
    <ui:NavigationView ... />
    <ui:ContentDialogHost x:Name="RootContentDialogHost" Grid.Row="0" />
</Grid>
```

**Registro no DI:**
```csharp
services.AddSingleton<IContentDialogService, ContentDialogService>();
```

**Inicializacao no MainWindow.xaml.cs:**
```csharp
_contentDialogService.SetDialogHost(RootContentDialogHost);
```

**Uso:**
```csharp
var result = await _contentDialogService.ShowSimpleDialogAsync(
    new SimpleContentDialogCreateOptions
    {
        Title = "Confirmar exclusao",
        Content = "Tem certeza?",
        PrimaryButtonText = "Excluir",
        CloseButtonText = "Cancelar"
    });
```

### ui:MessageBox — Substitui System.Windows.MessageBox

```csharp
var msgBox = new Wpf.Ui.Controls.MessageBox
{
    Title = "Erro",
    Content = "Falha ao exportar PDF.",
    PrimaryButtonText = "Tentar novamente",
    CloseButtonText = "Cancelar",
    PrimaryButtonAppearance = ControlAppearance.Danger,
    PrimaryButtonIcon = new SymbolIcon(SymbolRegular.ArrowSync24),
};
var result = await msgBox.ShowDialogAsync();
```

### ui:Snackbar — Toast temporario

**Setup no MainWindow.xaml:**
```xml
<Grid>
    <ui:NavigationView ... />
    <ui:SnackbarPresenter x:Name="RootSnackbarPresenter" Grid.Row="0" />
</Grid>
```

**Registro no DI:**
```csharp
services.AddSingleton<ISnackbarService, SnackbarService>();
```

**Uso:**
```csharp
_snackbarService.Show("PDF Exportado", "Arquivo salvo com sucesso.",
    ControlAppearance.Success,
    new SymbolIcon(SymbolRegular.Checkmark24),
    TimeSpan.FromSeconds(3));
```

### ui:Flyout — Popup ancorado

```xml
<ui:Button Content="Info">
    <ui:Button.Flyout>
        <ui:Flyout Placement="Bottom">
            <TextBlock Text="Informacao adicional" />
        </ui:Flyout>
    </ui:Button.Flyout>
</ui:Button>
```

### ui:InfoBar — Barra de status contextual

```xml
<ui:InfoBar Title="Campos obrigatorios" Severity="Warning"
            Message="Preencha todos os campos antes de exportar."
            IsOpen="True" IsClosable="True" />
```

Severidades: `Informational` (azul), `Success` (verde), `Warning` (amarelo), `Error` (vermelho).

### ui:InfoBadge — Indicador em nav items

```xml
<ui:NavigationViewItem Content="Alertas">
    <ui:NavigationViewItem.InfoBadge>
        <ui:InfoBadge Severity="Critical" Value="3" />
    </ui:NavigationViewItem.InfoBadge>
</ui:NavigationViewItem>
```

---

## 5. Date & Time

### ui:CalendarDatePicker — Alternativa a custom DatePicker

```xml
<ui:CalendarDatePicker Content="Selecionar data"
                       Date="{Binding DataInspecao}"
                       IsTodayHighlighted="True" />
```

**Nota:** Pode substituir o custom AptDateWPF em specs futuras. Oferece calendario
popup nativo com estilo Fluent. Porem, nao suporta formato dia/mes separado como
o controle custom atual.

### TimePicker

```xml
<TimePicker SelectedTime="{Binding Hora}" />
```

---

## 6. Progress & Loading

### ui:ProgressRing — Indicador de carregamento

```xml
<ui:ProgressRing IsIndeterminate="True" />           <!-- Indeterminado -->
<ui:ProgressRing Value="75" IsIndeterminate="False" /> <!-- Determinado -->
```

### ui:LoadingScreen — Tela de carregamento

```xml
<ui:LoadingScreen IsShown="True" />
```

---

## 7. Scroll Controls

### ui:PassiveScrollViewer — Para areas scrollaveis aninhadas

```xml
<ui:PassiveScrollViewer IsScrollSpillEnabled="True">
    <!-- Conteudo que pode estar dentro de outro scroll -->
</ui:PassiveScrollViewer>
```

`IsScrollSpillEnabled` propaga eventos de scroll bloqueados para o pai, resolvendo
problemas de scroll aninhado.

### ui:DynamicScrollViewer — ScrollViewer com auto-hide

Usado internamente pelo NavigationView. Scrollbars aparecem ao rolar e desaparecem
apos timeout. Propriedades: `IsScrollingHorizontally`, `IsScrollingVertically`, `Timeout`.

---

## 8. Window & Theme

### SystemThemeWatcher — Seguir tema do Windows

```csharp
// Em App.xaml.cs ou MainWindow constructor
SystemThemeWatcher.Watch(this);
```

Detecta mudancas de tema via WM_WININICHANGE e atualiza automaticamente.

### WindowBackdropType — Efeitos de fundo

```csharp
ApplicationThemeManager.Apply(ApplicationTheme.Dark, WindowBackdropType.Mica);
```

Valores: `None`, `Auto`, `Mica`, `Acrylic`, `Tabbed`.

### Accent Colors

```csharp
// Usar accent do sistema Windows
ApplicationAccentColorManager.ApplySystemAccent();

// Accent customizado
ApplicationAccentColorManager.Apply(Color.FromArgb(255, 0, 120, 215));
```

**Brushes de accent disponiveis:**
- `AccentFillColorDefaultBrush` — cor accent preenchida
- `AccentTextFillColorPrimaryBrush` — texto na cor accent
- `TextOnAccentFillColorPrimary` — texto sobre fundo accent

---

## Gotchas Conhecidos (WPF-UI 4.2.0)

1. **DataGrid nao totalmente estilizado** — WPF-UI nao fornece tema completo para DataGrid
   (Issue #10). Funciona mas pode ter inconsistencias visuais.
2. **NumberBox delayed value** — em alguns cenarios, `Value` pode nao atualizar imediatamente
   (Issue #945). Usar `ValueChanged` event.
3. **Icones Segoe Fluent Icons** — alguns icones requerem a fonte "Segoe Fluent Icons" que
   pode nao estar instalada no Windows 10. Testar em Win10 se necessario.
4. **NavigationViewItem sem TargetPageType** — para action items (Browse, Upload), usar
   `PreviewMouseLeftButtonUp` handler. `ItemInvoked` e `SelectionChanged` NAO funcionam
   para items sem TargetPageType no WPF-UI 4.2.0.
