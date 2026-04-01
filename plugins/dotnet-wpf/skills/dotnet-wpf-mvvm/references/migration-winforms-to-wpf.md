# Migracao WinForms para WPF com MVVM

Guia passo-a-passo para migrar projetos WinForms para WPF + MVVM.
Leia quando o projeto ainda e WinForms.

---

## Estrategia: Strangler Fig Pattern

NAO reescreva tudo de uma vez. Migre form-a-form, mantendo o app funcional a cada passo:

```
[Fase 0] Desacoplar services do Form atual (pre-requisito)
[Fase 1] Criar projeto WPF ou converter .csproj
[Fase 2] Converter UI do Form para XAML equivalente
[Fase 3] Criar ViewModel e configurar DI
[Fase 4] Adicionar bindings e commands
[Fase 5] Testar e atualizar docs
```

Se o projeto nao tem services desacoplados (logica de negocio esta no code-behind do Form),
use a skill `dotnet-desktop-setup` primeiro para extrair services.

---

## Fase 0: Pre-requisitos

Antes de migrar qualquer Form, verifique:

- [ ] Logica de negocio esta em classes `*Service.cs`, nao no Form
- [ ] Nao ha `MessageBox.Show()` em services
- [ ] Services retornam dados ou `Result<T>`, nao void com side effects de UI
- [ ] Testes cobrem a logica de negocio (independente da UI)

Se algum pre-requisito nao e atendido, desacople primeiro. A migracao para WPF
e muito mais facil quando os services ja existem — basta criar ViewModels que
chamam os mesmos services.

---

## Fase 1: Converter .csproj

### Opcao A: Converter projeto existente

No `.csproj`, substituir:
```xml
<!-- Antes (WinForms) -->
<UseWindowsForms>true</UseWindowsForms>

<!-- Depois (WPF) -->
<UseWPF>true</UseWPF>
```

Remover referencias a:
- `System.Windows.Forms`
- Pacotes WinForms-only (MaterialSkin, FontAwesome.Sharp para WinForms, etc.)

Adicionar pacotes WPF:
```bash
dotnet add package WPF-UI
dotnet add package CommunityToolkit.Mvvm
dotnet add package Microsoft.Extensions.Hosting
```

### Opcao B: Criar novo projeto WPF

Se o projeto WinForms e grande, pode ser melhor criar um novo projeto WPF e migrar
form-a-form, mantendo ambos projetos na solution durante a transicao.

---

## Fase 2: Mapeamento WinForms → WPF

### Controles

| WinForms | WPF | WPF-UI |
|----------|-----|--------|
| `Form` | `Window` | `FluentWindow` |
| `UserControl` | `UserControl` / `Page` | `Page` (com NavigationView) |
| `Button` | `Button` | `ui:Button` |
| `TextBox` | `TextBox` | `ui:TextBox` |
| `Label` | `TextBlock` | `TextBlock` |
| `ComboBox` | `ComboBox` | `ui:ComboBox` |
| `CheckBox` | `CheckBox` | `ui:CheckBox` |
| `ListBox` | `ListBox` / `ListView` | `ui:ListView` |
| `DataGridView` | `DataGrid` | `DataGrid` |
| `DateTimePicker` | `DatePicker` | `ui:DatePicker` / `CalendarDatePicker` |
| `ProgressBar` | `ProgressBar` | `ui:ProgressBar` |
| `MenuStrip` | `Menu` | `ui:NavigationView` (menu lateral) |
| `StatusStrip` | `StatusBar` | `ui:StatusBar` |
| `GroupBox` | `GroupBox` | `ui:CardExpander` / `ui:Card` |
| `TabControl` | `TabControl` | `ui:TabView` |

### Layouts

| WinForms | WPF Equivalente |
|----------|----------------|
| `FlowLayoutPanel` | `WrapPanel` |
| `TableLayoutPanel` | `Grid` com RowDefinitions/ColumnDefinitions |
| `Panel` | `StackPanel`, `Grid`, `DockPanel` |
| `SplitContainer` | `Grid` com `GridSplitter` |
| Anchoring (Dock, Anchor) | `HorizontalAlignment`, `VerticalAlignment`, `Margin` |

### Dialogs

| WinForms | WPF |
|----------|-----|
| `MessageBox.Show()` | `IContentDialogService` (WPF-UI) |
| `OpenFileDialog` (System.Windows.Forms) | `Microsoft.Win32.OpenFileDialog` |
| `SaveFileDialog` (System.Windows.Forms) | `Microsoft.Win32.SaveFileDialog` |
| `FolderBrowserDialog` | `Microsoft.Win32.OpenFolderDialog` (.NET 8+) |
| `ColorDialog` | Nao existe nativo — usar lib ou custom |

### Threading

| WinForms | WPF |
|----------|-----|
| `Control.Invoke()` | `Dispatcher.Invoke()` |
| `Control.BeginInvoke()` | `Dispatcher.BeginInvoke()` |
| `BackgroundWorker` | `async/await` + `Task.Run()` |
| `Control.InvokeRequired` | Nao necessario com async/await |

A melhor pratica em WPF moderno e usar `async/await` — o retorno automatico
ao thread de UI elimina a necessidade de `Invoke()` na maioria dos casos.

---

## Fase 3-4: Criar ViewModel e Bindings

Siga os Passos 3-5 do workflow principal na SKILL.md.

---

## 10 Pitfalls Comuns na Migracao

1. **Tentar migrar tudo de uma vez** — migre form-a-form. Apps WinForms podem
   hospedar WPF via `ElementHost`, e apps WPF podem hospedar WinForms via
   `WindowsFormsHost` durante a transicao.

2. **Logica no code-behind** — em WinForms, `button1_Click` handlers sao normais.
   Em WPF MVVM, commands e bindings substituem event handlers. Code-behind deve
   ficar quase vazio.

3. **Acessar controles por nome no ViewModel** — nunca use `txtNome.Text` no ViewModel.
   Use bindings: `Text="{Binding Nome}"`.

4. **Usar `System.Windows.Forms.MessageBox`** — usar `Microsoft.Win32` dialogs ou
   `IContentDialogService` do WPF-UI.

5. **Usar `List<T>` para listas na UI** — usar `ObservableCollection<T>` para que
   a ListView/DataGrid atualize automaticamente.

6. **Esquecer `UpdateSourceTrigger=PropertyChanged`** — TextBox default so atualiza
   o binding no LostFocus. Para validacao em tempo real, setar PropertyChanged.

7. **Converter layout pixel-a-pixel** — WPF usa layout responsivo (Grid, StackPanel).
   Nao tente replicar coordenadas absolutas do WinForms.

8. **Ignorar DataContext** — se os bindings nao funcionam, verifique se o DataContext
   esta configurado corretamente na Window/Page.

9. **Thread marshaling** — WinForms usa `Control.Invoke()`. Em WPF, use `async/await`.
   Se precisar do Dispatcher: `Application.Current.Dispatcher.Invoke()`.

10. **Nao atualizar CLAUDE.md** — apos migrar, atualizar descricao do stack,
    referencias a arquivos UI, e arquitetura no CLAUDE.md do projeto.

---

## Coexistencia durante Migracao

### WPF dentro de WinForms (ElementHost)

Para adicionar controles WPF a um Form existente:
```csharp
var wpfControl = new MeuControleWpf();
var host = new ElementHost
{
    Dock = DockStyle.Fill,
    Child = wpfControl
};
panel1.Controls.Add(host);
```

### WinForms dentro de WPF (WindowsFormsHost)

Para manter um controle WinForms em uma janela WPF:
```xml
<WindowsFormsHost>
    <wf:DataGridView x:Name="gridLegado" />
</WindowsFormsHost>
```

Ambos requerem referencia ao assembly de interop. Use apenas como solucao temporaria
durante a migracao — o objetivo final e ter tudo em WPF.

---

## Coexistencia WinForms + WPF (.NET 8+)

.NET 8+ suporta ambos `UseWindowsForms` e `UseWPF` no mesmo .csproj. Isto e essencial
para o Strangler Fig pattern — permite migrar form-a-form sem quebrar a aplicacao.

```xml
<PropertyGroup>
    <UseWPF>true</UseWPF>
    <UseWindowsForms>true</UseWindowsForms> <!-- manter durante migracao -->
</PropertyGroup>
```

**Vantagens da coexistencia:**
- Usar `System.Windows.Forms.FolderBrowserDialog` enquanto nao migra para
  `Microsoft.Win32.OpenFolderDialog` (disponivel no .NET 8+)
- Manter Forms antigos compilando enquanto as WPF Pages sao criadas
- Remover `UseWindowsForms` apenas quando TODOS os forms forem convertidos

---

## Migracao de DataGridView para WPF DataGrid

### Mapeamento de Propriedades

| WinForms (DataGridView) | WPF (DataGrid) |
|--------------------------|----------------|
| `DataSource = list` | `ItemsSource = list` |
| `AutoGenerateColumns = false` | `AutoGenerateColumns="False"` |
| `ReadOnly = true` | `IsReadOnly="True"` |
| `AllowUserToAddRows = false` | `CanUserAddRows="False"` |
| `RowTemplate.Height = 18` | `RowHeight="18"` |
| `Columns["X"].Visible = false` | Nao declarar a coluna (com AutoGenerateColumns=False) |
| `Columns["X"].HeaderText = "Y"` | `Header="Y"` na coluna |
| `AutoSizeMode.Fill` | `Width="*"` |
| `FillWeight = 5` | `Width="5*"` (relativo) |
| `MinimumWidth = 150` | `MinWidth="150"` |
| `DefaultCellStyle.Alignment = MiddleCenter` | ElementStyle com TextAlignment="Center" |
| `DefaultCellStyle.Format = "###,###,##0"` | `StringFormat='###,###,##0'` no Binding |
| `DataGridViewImageColumn` | `DataGridTemplateColumn` com SymbolIcon |

### Coluna com Alinhamento Centralizado

```xml
<DataGridTextColumn Header="Channel" Binding="{Binding Channel}">
    <DataGridTextColumn.ElementStyle>
        <Style TargetType="TextBlock">
            <Setter Property="TextAlignment" Value="Center" />
            <Setter Property="VerticalAlignment" Value="Center" />
        </Style>
    </DataGridTextColumn.ElementStyle>
</DataGridTextColumn>
```

### Coluna com Icone via DataTrigger

Para substituir `DataGridViewImageColumn` com icones por enum:

```xml
<DataGridTemplateColumn Header="Level" Width="70">
    <DataGridTemplateColumn.CellTemplate>
        <DataTemplate>
            <ContentControl HorizontalAlignment="Center">
                <ContentControl.Style>
                    <Style TargetType="ContentControl">
                        <Style.Triggers>
                            <DataTrigger Binding="{Binding Type}"
                                Value="{x:Static local:Alerts+Level.Warning}">
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

**Nota**: Para enums aninhados no XAML, usar `+` separador: `{x:Static local:Alerts+Level.Warning}`.

### Filtro: BindingSource → DataView.RowFilter

`DataView.RowFilter` usa a mesma sintaxe de expressao que `BindingSource.Filter` (ambos
operam sobre DataTable). A migracao e direta:

```csharp
// WinForms
BindingSource bs = new() { DataSource = dataTable };
bs.Filter = $"{campo} like '*{texto}*'";

// WPF — porta direta
DataView view = dataTable.DefaultView;
view.Sort = "DateTime desc";
dataGrid.ItemsSource = view;
view.RowFilter = $"{campo} like '*{texto}*'";
```

### Toggle de Multiplos DataGrids

Para telas com varios DataGrids (ex: Channels vs DSC), empilhar no mesmo Grid cell
e alternar visibilidade:

```xml
<DataGrid x:Name="dgv1" Grid.Row="1" Visibility="Visible" ... />
<DataGrid x:Name="dgv2" Grid.Row="1" Visibility="Collapsed" ... />
<DataGrid x:Name="dgv3" Grid.Row="1" Visibility="Collapsed" ... />
```

```csharp
private void ShowGrid(DataGrid gridToShow)
{
    dgv1.Visibility = Visibility.Collapsed;
    dgv2.Visibility = Visibility.Collapsed;
    dgv3.Visibility = Visibility.Collapsed;
    gridToShow.Visibility = Visibility.Visible;
}
```

---

## Checklist Pos-Migracao

Apos completar a migracao de cada Form:

1. [ ] CLAUDE.md — atualizar descricao do stack e UI framework
2. [ ] CLAUDE.md — atualizar referencias a arquivos UI (Form*.cs → *.xaml)
3. [ ] .csproj — confirmar UseWPF=true, remover UseWindowsForms se nao usado
4. [ ] .gitignore — adicionar exclusoes para runtimes WPF se necessario
5. [ ] Testes — verificar que todos passam (services nao mudaram)
6. [ ] Code-behind — verificar que tem apenas InitializeComponent + DI
7. [ ] Remover arquivos WinForms deletados do controle de versao
