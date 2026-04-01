# Fundamentos MVVM para WPF

Este guia explica os conceitos centrais do MVVM para quem esta comecando ou precisa
relembrar. Leia quando o usuario for novo em MVVM.

---

## O Padrao MVVM

MVVM (Model-View-ViewModel) separa o aplicativo em tres camadas:

- **Model** — dados e regras de negocio puras em C#. Nao sabe que a UI existe.
- **View** — telas XAML que apresentam dados e recebem interacoes do usuario.
  Deve ser o mais "burra" possivel — minimo de codigo no `.xaml.cs`.
- **ViewModel** — o intermediario. Pega dados do Model, formata para a View,
  e recebe acoes do usuario para encaminhar ao Model/Service.

A **View nao conhece o Model** — toda comunicacao passa pelo ViewModel.
O **ViewModel nao conhece a View** — ele expoe propriedades e commands, a View se liga via binding.

---

## Data Binding

Data Binding e a conexao automatica entre View e ViewModel. No XAML:

```xml
<TextBlock Text="{Binding NomeDoNavio}" />
```

A View mostra o valor da propriedade `NomeDoNavio` do ViewModel. Para isso funcionar:

1. **DataContext** — a View precisa saber qual ViewModel esta usando:
   ```csharp
   // No construtor da Window/Page
   public MainWindow(MainWindowViewModel viewModel)
   {
       InitializeComponent();
       DataContext = viewModel;
   }
   ```

2. **INotifyPropertyChanged** — quando o ViewModel muda um valor, precisa avisar a View:
   ```csharp
   public event PropertyChangedEventHandler PropertyChanged;

   private string _nome;
   public string Nome
   {
       get => _nome;
       set
       {
           _nome = value;
           PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(nameof(Nome)));
       }
   }
   ```

   Com CommunityToolkit.Mvvm, isso se reduz a:
   ```csharp
   [ObservableProperty]
   private string _nome;  // Gera propriedade Nome com notificacao automatica
   ```

### Modos de Binding

| Modo | Direcao | Uso |
|------|---------|-----|
| `OneWay` | ViewModel → View | Labels, textos somente-leitura |
| `TwoWay` | ViewModel ↔ View | TextBox, CheckBox, inputs |
| `OneTime` | ViewModel → View (1x) | Dados que nao mudam |
| `OneWayToSource` | View → ViewModel | Raro, captura de input sem exibicao |

Para `TextBox`, o binding default atualiza apenas no `LostFocus`. Para atualizar
a cada tecla digitada:
```xml
<TextBox Text="{Binding Nome, UpdateSourceTrigger=PropertyChanged}" />
```

---

## Commands (Acoes)

No MVVM, botoes nao usam o evento `Click` no code-behind. Em vez disso, usam **Commands**:

```xml
<Button Content="Salvar" Command="{Binding SalvarCommand}" />
```

Um Command implementa `ICommand` com dois metodos:
- **Execute** — o que fazer quando clicado
- **CanExecute** — o botao pode ser clicado? (WPF habilita/desabilita automaticamente)

Com CommunityToolkit.Mvvm:
```csharp
[RelayCommand]
private void Salvar()
{
    _service.SalvarDados();
}
// Gera: public IRelayCommand SalvarCommand { get; }
```

Com CanExecute:
```csharp
[RelayCommand(CanExecute = nameof(PodeSalvar))]
private void Salvar() { /* ... */ }

private bool PodeSalvar() => !string.IsNullOrEmpty(Nome);
```

### CommandParameter

Para passar dados do XAML para o ViewModel:
```xml
<Button Content="Excluir"
        Command="{Binding ExcluirCommand}"
        CommandParameter="{Binding SelectedItem}" />
```

```csharp
[RelayCommand]
private void Excluir(ItemModel item)
{
    Items.Remove(item);
}
// O source generator cria RelayCommand<ItemModel>
```

---

## ObservableCollection

`List<T>` nao notifica a View quando itens sao adicionados/removidos.
`ObservableCollection<T>` sim — ela dispara eventos automaticamente.

```csharp
// NO ViewModel
public ObservableCollection<Navio> Navios { get; } = new();

[RelayCommand]
private void AdicionarNavio()
{
    Navios.Add(new Navio("Novo Navio", "123456789"));
    // A View atualiza sozinha — sem precisar tocar na ListView
}
```

```xml
<!-- Na View -->
<ListView ItemsSource="{Binding Navios}">
    <ListView.ItemTemplate>
        <DataTemplate>
            <TextBlock Text="{Binding Nome}" />
        </DataTemplate>
    </ListView.ItemTemplate>
</ListView>
```

Nao use `[ObservableProperty]` na collection — declare como propriedade publica simples.

---

## Messenger (Comunicacao entre ViewModels)

Quando um ViewModel precisa avisar outro sobre algo (ex: usuario logou, dados mudaram),
use o `WeakReferenceMessenger` do CommunityToolkit:

### 1. Defina a mensagem
```csharp
public record DadosSalvosMessage(string NomeArquivo);
```

### 2. Envie de um ViewModel
```csharp
WeakReferenceMessenger.Default.Send(new DadosSalvosMessage("dados.json"));
```

### 3. Escute em outro ViewModel
```csharp
public partial class OutroViewModel : ObservableObject, IRecipient<DadosSalvosMessage>
{
    public OutroViewModel()
    {
        WeakReferenceMessenger.Default.Register(this);
    }

    public void Receive(DadosSalvosMessage message)
    {
        Status = $"Arquivo salvo: {message.NomeArquivo}";
    }
}
```

---

## Navegacao via ContentControl

Para trocar de "tela" sem abrir novas janelas, use `ContentControl` + `DataTemplates`:

```csharp
// MainViewModel controla qual ViewModel esta ativo
[ObservableProperty]
private ObservableObject _paginaAtual;

[RelayCommand]
private void IrParaConfiguracoes()
{
    PaginaAtual = new ConfiguracoesViewModel();
}
```

```xml
<Window.Resources>
    <DataTemplate DataType="{x:Type vm:DashboardViewModel}">
        <views:DashboardView />
    </DataTemplate>
    <DataTemplate DataType="{x:Type vm:ConfiguracoesViewModel}">
        <views:ConfiguracoesView />
    </DataTemplate>
</Window.Resources>

<ContentControl Content="{Binding PaginaAtual}" />
```

O WPF automaticamente renderiza a View correta baseado no tipo do ViewModel.

Para apps mais complexas, use `INavigationService` do WPF-UI
(veja `references/wpfui-integration.md`).
