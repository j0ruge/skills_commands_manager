# CI/CD para Testes E2E com FlaUI

## Índice
1. [Requisito Fundamental](#requisito-fundamental)
2. [GitHub Actions](#github-actions)
3. [Azure DevOps](#azure-devops)
4. [Separação de Testes](#separação-de-testes)
5. [Screenshots em CI](#screenshots-em-ci)
6. [Troubleshooting](#troubleshooting)

---

## Requisito Fundamental

Testes FlaUI usam a **UI Automation API do Windows**, que requer uma **sessão de desktop interativa** com um usuário logado. Isso significa:

- **NÃO funciona** em containers Linux
- **NÃO funciona** em runners GitHub Actions hospedados pela Microsoft (são headless)
- **NÃO funciona** em Windows Services sem desktop
- **Funciona** em runners self-hosted com sessão interativa
- **Funciona** em VMs Azure com auto-logon configurado

---

## GitHub Actions

### Estratégia: Runner self-hosted com desktop interativo

1. **Instalar runner como processo interativo** (não como service):
   ```powershell
   # Ao instalar o runner, quando perguntar "Run as service?", responda N
   .\config.cmd --url https://github.com/org/repo --token TOKEN
   .\run.cmd  # Rodar como processo interativo, NÃO como service
   ```

2. **Configurar auto-logon** para o usuário do runner:
   ```powershell
   # Registry (requer admin)
   Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon" `
       -Name "AutoAdminLogon" -Value "1"
   Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon" `
       -Name "DefaultUserName" -Value "runner-user"
   Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon" `
       -Name "DefaultPassword" -Value "senha"
   ```

3. **Preservar sessão ao desconectar RDP**:
   ```batch
   REM Ao desconectar RDP, usar tscon para manter a sessão
   for /f "skip=1 tokens=3" %%s in ('query user %USERNAME%') do (
       %windir%\System32\tscon.exe %%s /dest:console
   )
   ```

### Workflow exemplo

```yaml
name: Tests

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: windows-latest  # Runner hospedado — só testes unitários
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-dotnet@v4
        with:
          dotnet-version: '10.0.x'
      - run: dotnet build -v q --no-restore
      - run: dotnet test --filter "Category!=E2E" --no-build

  e2e-tests:
    runs-on: [self-hosted, windows, desktop]  # Runner self-hosted com desktop
    needs: unit-tests  # Rodar após testes unitários passarem
    steps:
      - uses: actions/checkout@v4
      - run: dotnet build -v q -c Release
      - run: dotnet test MyApp.E2ETests --filter "Category=E2E" --no-build -c Release
        timeout-minutes: 10
      - name: Upload screenshots on failure
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: e2e-screenshots
          path: '**/screenshots/**/*.png'
          retention-days: 7
```

### Labels para self-hosted runner
- `self-hosted` — identifica como runner próprio
- `windows` — sistema operacional
- `desktop` — indica que tem sessão interativa (label custom)

---

## Azure DevOps

### Opção 1: Agent pool com UI interativa

```yaml
trigger:
  - main

stages:
  - stage: UnitTests
    jobs:
      - job: Test
        pool:
          vmImage: 'windows-latest'
        steps:
          - task: DotNetCoreCLI@2
            inputs:
              command: 'test'
              arguments: '--filter "Category!=E2E"'

  - stage: E2ETests
    dependsOn: UnitTests
    jobs:
      - job: E2E
        pool:
          name: 'SelfHostedDesktop'  # Pool com agentes interativos
        steps:
          - task: ScreenResolutionUtility@1
            inputs:
              displaySettings: specific
              width: 1920
              height: 1080
          - task: DotNetCoreCLI@2
            inputs:
              command: 'test'
              arguments: '--filter "Category=E2E"'
            timeoutInMinutes: 10
```

### Opção 2: Azure DevTest Labs

Azure DevTest Labs pode criar VMs com o agente configurado para testes de UI automaticamente. Consulte a [documentação da Microsoft](https://learn.microsoft.com/en-us/azure/devops/pipelines/test/ui-testing-considerations).

---

## Separação de Testes

### Marcar testes E2E com Trait
```csharp
[Trait("Category", "E2E")]
public class MainWindowTests : FlaUITestBase
{
    [Fact]
    public void JanelaPrincipal_DeveAbrir() { /* ... */ }
}
```

### Comandos de execução
```bash
# Todos os testes
dotnet test

# Apenas unitários (exclui E2E)
dotnet test --filter "Category!=E2E"

# Apenas E2E
dotnet test --filter "Category=E2E"

# E2E de uma tela específica
dotnet test --filter "FullyQualifiedName~MainWindowTests"
```

### .runsettings para E2E (opcional)
```xml
<?xml version="1.0" encoding="utf-8"?>
<RunSettings>
  <RunConfiguration>
    <!-- Timeout maior para E2E -->
    <TestSessionTimeout>300000</TestSessionTimeout>
    <!-- Não rodar em paralelo — FlaUI pode ter conflitos -->
    <MaxCpuCount>1</MaxCpuCount>
  </RunConfiguration>
</RunSettings>
```

Usar com: `dotnet test --settings e2e.runsettings`

---

## Screenshots em CI

### Captura automática em falha

Na classe `FlaUITestBase`, adicione captura de screenshot no Dispose quando o teste falha:

```csharp
public abstract class FlaUITestBase : IDisposable
{
    private bool _testFailed;

    protected void MarkFailed() => _testFailed = true;

    public void Dispose()
    {
        if (_testFailed)
        {
            try
            {
                var screenshotDir = Environment.GetEnvironmentVariable("E2E_SCREENSHOT_DIR")
                    ?? Path.Combine(AppContext.BaseDirectory, "screenshots");
                Directory.CreateDirectory(screenshotDir);

                var path = Path.Combine(screenshotDir,
                    $"failure_{DateTime.Now:yyyyMMdd_HHmmss}.png");
                FlaUI.Core.Capturing.Capture.Screen().ToFile(path);
            }
            catch
            {
                // Screenshot failure should not mask test failure
            }
        }

        App?.Close();
        Automation?.Dispose();
        GC.SuppressFinalize(this);
    }
}
```

### Upload como artifact no CI

No GitHub Actions:
```yaml
- uses: actions/upload-artifact@v4
  if: failure()
  with:
    name: e2e-failure-screenshots
    path: '**/screenshots/**/*.png'
    retention-days: 7
```

No Azure DevOps:
```yaml
- task: PublishBuildArtifacts@1
  condition: failed()
  inputs:
    pathtoPublish: '$(Build.SourcesDirectory)/**/screenshots'
    artifactName: 'e2e-screenshots'
```

---

## Troubleshooting

### "Element not found" ou "null reference"

1. **AutomationId não definido no XAML** — mais comum. Verificar com FlaUInspect.
2. **Elemento ainda não renderizou** — usar `Retry.WhileNull` com timeout adequado.
3. **Runner sem desktop** — verificar se o runner tem sessão interativa.

### "The RPC server is unavailable"

- O processo do app crashou ou não iniciou.
- Verificar se o caminho do executável está correto em `TestConstants`.
- Verificar se o app precisa de dependências (runtime, DLLs).

### Testes passam local mas falham no CI

1. **Resolução de tela** — CI pode ter resolução menor. Configurar 1920x1080.
2. **Timing** — CI é mais lento. Aumentar timeouts:
   ```csharp
   // Em TestConstants ou via env var
   public static int WindowTimeoutSeconds =>
       int.Parse(Environment.GetEnvironmentVariable("E2E_TIMEOUT") ?? "15");
   ```
3. **DPI scaling** — Desabilitar DPI scaling no runner ou usar coordenadas relativas.
4. **Focus issues** — Outra janela pode roubar foco. Usar `window.SetForeground()`.

### Testes intermitentes (flaky)

1. **Preferir `Retry.WhileNull` ou `Retry.WhileTrue`** sobre `Thread.Sleep()` para esperar elementos da UI. **Exceção:** automação de file dialogs Win32, onde `Thread.Sleep()` é necessário entre operações de teclado e para aguardar rendering do dialog (o dialog aparece na árvore de automação antes dos controles internos estarem prontos).
2. **Isolar testes** — cada teste deve abrir e fechar o app (ou usar `IClassFixture`).
3. **Desabilitar animações** em testes:
   ```csharp
   // No setup do teste
   System.Windows.Media.Animation.Timeline.DesiredFrameRateProperty
       .OverrideMetadata(typeof(Timeline),
           new FrameworkPropertyMetadata { DefaultValue = 0 });
   ```
4. **Não rodar em paralelo** — usar `MaxCpuCount=1` no `.runsettings`.
