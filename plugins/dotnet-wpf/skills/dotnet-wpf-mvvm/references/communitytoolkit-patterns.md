# Patterns do CommunityToolkit.Mvvm

Guia pratico dos source generators e classes base do CommunityToolkit.Mvvm.
Leia durante o Passo 4 (criacao de ViewModels).

---

## ObservableObject (Base Class)

Toda ViewModel deve herdar de `ObservableObject`. Ele implementa `INotifyPropertyChanged`
e fornece `SetProperty()` para notificacao automatica.

```csharp
using CommunityToolkit.Mvvm.ComponentModel;

namespace MeuProjeto.ViewModels;

public partial class MeuViewModel : ObservableObject
{
    // Tudo aqui...
}
```

A classe DEVE ser `partial` para os source generators funcionarem.

---

## [ObservableProperty]

Transforma um campo privado em propriedade publica com notificacao automatica.

```csharp
[ObservableProperty]
private string _nomeDoNavio;

// O source generator cria:
// public string NomeDoNavio
// {
//     get => _nomeDoNavio;
//     set => SetProperty(ref _nomeDoNavio, value);
// }
```

### Regras de naming
- Campo `_nomeDoNavio` → propriedade `NomeDoNavio`
- Campo `_nome` → propriedade `Nome`
- O campo DEVE ser `private`

### Partial methods para hooks

O generator cria dois metodos parciais que voce pode implementar:

```csharp
[ObservableProperty]
private string _email;

// Executado ANTES da mudanca (permite cancelar? nao, mas permite agir antes)
partial void OnEmailChanging(string value)
{
    // value e o novo valor que esta chegando
}

// Executado APOS a mudanca
partial void OnEmailChanged(string value)
{
    // Validar, recalcular, notificar outro CanExecute, etc.
    SalvarCommand.NotifyCanExecuteChanged();
}
```

### Notificar outras propriedades

Se uma propriedade depende de outra (ex: `NomeCompleto` depende de `Nome` e `Sobrenome`):

```csharp
[ObservableProperty]
[NotifyPropertyChangedFor(nameof(NomeCompleto))]
private string _nome;

[ObservableProperty]
[NotifyPropertyChangedFor(nameof(NomeCompleto))]
private string _sobrenome;

public string NomeCompleto => $"{Nome} {Sobrenome}";
```

### Notificar CanExecute de commands

Quando uma propriedade muda e um command precisa reavaliar se pode executar:

```csharp
[ObservableProperty]
[NotifyCanExecuteChangedFor(nameof(SalvarCommand))]
private string _nome = string.Empty;

[RelayCommand(CanExecute = nameof(PodeSalvar))]
private void Salvar() { /* ... */ }

private bool PodeSalvar() => !string.IsNullOrEmpty(Nome);
```

**Alternativa com propriedade bool (mais simples para toggle on/off):**

Quando o CanExecute depende de um estado binario (carregou/nao carregou), use uma
propriedade bool diretamente em vez de um metodo:

```csharp
[ObservableProperty]
[NotifyCanExecuteChangedFor(nameof(SalvarLicencaCommand))]
private bool _isSaveEnabled;

[RelayCommand(CanExecute = nameof(IsSaveEnabled))]
private void SalvarLicenca() { /* ... */ }

// Em algum metodo:
IsSaveEnabled = true; // O botao habilita automaticamente
```

Este padrao e mais direto que criar um metodo `PodeSalvar()` quando a condicao
e simplesmente "algo foi carregado". O `[NotifyCanExecuteChangedFor]` garante que
o command reavalia o CanExecute toda vez que `IsSaveEnabled` muda.

---

## [RelayCommand]

Transforma um metodo em propriedade `IRelayCommand`.

### Comando simples (sem parametro)
```csharp
[RelayCommand]
private void LimparFormulario()
{
    Nome = string.Empty;
    Email = string.Empty;
}
// Gera: public IRelayCommand LimparFormularioCommand { get; }
```

### Comando com parametro tipado
```csharp
[RelayCommand]
private void Excluir(NavioModel navio)
{
    Navios.Remove(navio);
}
// Gera: public IRelayCommand<NavioModel> ExcluirCommand { get; }
```

No XAML:
```xml
<Button Command="{Binding ExcluirCommand}"
        CommandParameter="{Binding SelectedItem, ElementName=listaNavios}" />
```

### Comando async
```csharp
[RelayCommand]
private async Task CarregarNaviosAsync()
{
    IsCarregando = true;
    try
    {
        var navios = await _service.ObterNaviosAsync();
        foreach (var n in navios)
            Navios.Add(n);
    }
    finally
    {
        IsCarregando = false;
    }
}
// Gera: public IAsyncRelayCommand CarregarNaviosCommand { get; }
// O botao desabilita automaticamente durante execucao
```

### Comando com CanExecute
```csharp
[RelayCommand(CanExecute = nameof(PodeSalvar))]
private void Salvar()
{
    _service.Salvar(Nome, Email);
}

private bool PodeSalvar() => !string.IsNullOrEmpty(Nome) && !string.IsNullOrEmpty(Email);
```

O botao no XAML habilita/desabilita automaticamente baseado no retorno de `PodeSalvar()`.
Para reavaliar, chame `SalvarCommand.NotifyCanExecuteChanged()` — tipicamente no
`OnPropertyChanged` de `Nome` ou `Email`.

---

## ObservableValidator (Validacao)

Para ViewModels com formularios que precisam validar input:

```csharp
using System.ComponentModel.DataAnnotations;

public partial class CadastroViewModel : ObservableValidator
{
    [ObservableProperty]
    [Required(ErrorMessage = "MMSI e obrigatorio")]
    [StringLength(9, MinimumLength = 9, ErrorMessage = "MMSI deve ter 9 digitos")]
    private string _mmsi;

    [RelayCommand]
    private void Salvar()
    {
        ValidateAllProperties();

        if (HasErrors)
            return;

        _service.Salvar(Mmsi);
    }
}
```

No XAML, erros aparecem automaticamente com `ValidatesOnDataErrors`:
```xml
<TextBox Text="{Binding Mmsi, ValidatesOnDataErrors=True, UpdateSourceTrigger=PropertyChanged}" />
```

---

## Exemplo Completo: LicenceManager ViewModel

Baseado no LicenceManager real do projeto VDRDataAnalyzer:

```csharp
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace LicenceManager.ViewModels;

public partial class MainWindowViewModel : ObservableObject
{
    private readonly LicenseService _licenseService;

    [ObservableProperty]
    private string _caminhoArquivoHid;

    [ObservableProperty]
    private string _processorId;

    [ObservableProperty]
    private string _motherboardSerial;

    [ObservableProperty]
    private DateTime _dataExpiracao = DateTime.Today.AddYears(1);

    [ObservableProperty]
    private string _statusMessage;

    public MainWindowViewModel(LicenseService licenseService)
    {
        _licenseService = licenseService;
    }

    [RelayCommand]
    private void CarregarHardwareId()
    {
        var dialog = new Microsoft.Win32.OpenFileDialog
        {
            Filter = "Hardware ID|*.hid",
            Title = "Selecionar arquivo de Hardware ID"
        };

        if (dialog.ShowDialog() == true)
        {
            CaminhoArquivoHid = dialog.FileName;
            var hwInfo = _licenseService.RecuperarDeArquivo(dialog.FileName);
            ProcessorId = hwInfo.ProcessorID;
            MotherboardSerial = hwInfo.MotherBoardSerialNumber;
            StatusMessage = "Hardware ID carregado com sucesso";
        }
    }

    [RelayCommand(CanExecute = nameof(PodeSalvarLicenca))]
    private void SalvarLicenca()
    {
        var dialog = new Microsoft.Win32.SaveFileDialog
        {
            Filter = "License|*.lic",
            Title = "Salvar arquivo de licenca"
        };

        if (dialog.ShowDialog() == true)
        {
            var licenseInfo = new LicenseInfo
            {
                ExpiryDate = DataExpiracao
            };
            _licenseService.SalvarParaArquivo(dialog.FileName, licenseInfo);
            StatusMessage = "Licenca salva com sucesso";
        }
    }

    private bool PodeSalvarLicenca() =>
        !string.IsNullOrEmpty(ProcessorId) && !string.IsNullOrEmpty(MotherboardSerial);
}
```
