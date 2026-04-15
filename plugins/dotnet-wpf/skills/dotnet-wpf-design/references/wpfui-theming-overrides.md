# WPF-UI Theming Overrides — Customizando cores e aparencia de controles

Guia detalhado para customizar a aparencia de controles do WPF-UI 4.2.0 via override
de `DynamicResource`. Leia este arquivo quando:

- Aplicar identidade visual/brand color em botoes Primary
- Customizar cor de texto em `ToggleButton` quando `IsChecked=True`
- Mudar cor accent de `CheckBox`, `ProgressRing`, ou outros controles
- Descobrir nomes exatos de resources do WPF-UI

**Principio geral:** Para customizar estados de template (hover, pressed, checked), sempre
sobrescreva os `DynamicResource` que o template consulta. Override de resources >> override
de properties. Veja Detalhe Critico #11 no SKILL.md para a teoria por tras disso.

---

## Table of Contents

- [BRAND-001: Brand color em botoes Primary (sem delay no hover)](#brand-001-brand-color-em-botoes-primary-sem-delay-no-hover)
- [CTRL-004: ToggleButton com texto branco quando IsChecked=True](#ctrl-004-togglebutton-com-texto-branco-quando-ischeckedtrue)
- [CTRL-005: CheckBox — cor do checkmark e fundo](#ctrl-005-checkbox--cor-do-checkmark-e-fundo)
- [CTRL-006: ClearButtonEnabled="False" em campos curtos](#ctrl-006-clearbuttonenabledfalse-em-campos-curtos)
- [CTRL-007: Cor customizada do ProgressRing](#ctrl-007-cor-customizada-do-progressring)
- [RES-001: Descobrindo nomes exatos de DynamicResource do WPF-UI](#res-001-descobrindo-nomes-exatos-de-dynamicresource-do-wpf-ui)

---

## BRAND-001: Brand color em botoes Primary (sem delay no hover)

**Problema:** O usuario pede para aplicar uma cor de marca (ex: vermelho `#DF0024`) em
todos os botoes `Appearance="Primary"`. O reflexo e criar um Style com
`Setter Property="Background"` + triggers para hover/pressed. Resultado: o botao fica
na cor da marca no estado normal mas **flasha de volta para cinza no hover**, so voltando
ao brand quando o mouse sai — impressao de delay grotesca.

**Causa raiz:** O `ControlTemplate` do `ui:Button` para `Appearance="Primary"` contem
Triggers internos que fazem:

```xml
<Setter TargetName="ContentBorder"
        Property="Background"
        Value="{DynamicResource AccentButtonBackgroundPointerOver}" />
```

O `TargetName` aponta para um elemento INTERNO do template — setter externo no Background
da propria Button nao vence, porque o template pinta um Border interno com uma cor
especifica de recurso.

**Solucao:** Sobrescrever os DynamicResource globalmente em `App.xaml`. O proprio template
passa a usar o brand color em TODAS as transicoes (default/hover/pressed), sem delay.

```xml
<!-- App.xaml Resources -->
<SolidColorBrush x:Key="AccentButtonBackground" Color="#DF0024" />
<SolidColorBrush x:Key="AccentButtonBackgroundPointerOver" Color="#B30018" />
<SolidColorBrush x:Key="AccentButtonBackgroundPressed" Color="#8F0014" />
<SolidColorBrush x:Key="AccentButtonBorderBrushPressed" Color="#8F0014" />
<SolidColorBrush x:Key="AccentButtonForeground" Color="White" />
<SolidColorBrush x:Key="AccentButtonForegroundPointerOver" Color="White" />
<SolidColorBrush x:Key="AccentButtonForegroundPressed" Color="White" />
```

Agora qualquer `<ui:Button Appearance="Primary" />` usa brand color + transicoes corretas.

**Lista exata dos resources** da aparencia Primary (verificados no `Wpf.Ui.dll` — veja
RES-001):

- `AccentButtonBackground` / `AccentButtonBackgroundPointerOver` / `AccentButtonBackgroundPressed`
- `AccentButtonBorderBrushPressed`
- `AccentButtonForeground` / `AccentButtonForegroundPointerOver` / `AccentButtonForegroundPressed`

---

## CTRL-004: ToggleButton com texto branco quando IsChecked=True

**Problema:** Voce colore um `ToggleButton` (ex: botoes Yes/No/N/A) com Background
verde/vermelho quando selecionado via code-behind:

```csharp
btnYes.Background = Brushes.Green;
btnYes.Foreground = Brushes.White;  // ← ignorado!
```

Background funciona. **Foreground continua escuro**, texto ilegivel no fundo colorido.

**Causa raiz:** O template do `ToggleButton` no WPF-UI 4.2.0 tem um `MultiTrigger`:

```xml
<MultiTrigger>
    <MultiTrigger.Conditions>
        <Condition Property="IsEnabled" Value="True" />
        <Condition Property="IsChecked" Value="True" />
    </MultiTrigger.Conditions>
    <Setter TargetName="ContentPresenter"
            Property="TextElement.Foreground"
            Value="{DynamicResource ToggleButtonForegroundChecked}" />
</MultiTrigger>
```

Ele aplica `TextElement.Foreground` no `ContentPresenter` interno via DynamicResource.
`TextElement.Foreground` em ContentPresenter tem precedencia sobre property inheritance
— `button.Foreground = White` nunca chega no texto do conteudo.

**Solucao:** Override do recurso local no `UserControl.Resources` (escopo restrito, nao
afeta outros ToggleButtons do app):

```xml
<UserControl.Resources>
    <SolidColorBrush x:Key="ToggleButtonForegroundChecked" Color="White" />
    <SolidColorBrush x:Key="ToggleButtonForegroundCheckedPointerOver" Color="White" />
    <SolidColorBrush x:Key="ToggleButtonForegroundCheckedPressed" Color="White" />
</UserControl.Resources>
```

Como e `DynamicResource`, o lookup em runtime encontra esses 3 brushes no escopo do
UserControl antes de subir ao ThemeDictionary — apenas os ToggleButtons desse UserControl
sao afetados.

**Regra:** Texto em ToggleButton checked **sempre** via override do
`ToggleButtonForegroundChecked` (e variacoes de estado), nunca via `.Foreground` no
code-behind.

---

## CTRL-005: CheckBox — cor do checkmark e fundo

**Problema:** Precisa mudar a cor accent do CheckBox (ex: azul padrao → verde brand).
O reflexo e procurar resources com nome tipo `CheckBoxCheckGlyphForegroundChecked`
(seguindo convencao WinUI), mas o override e **silenciosamente ignorado** porque esse
nome nao existe no WPF-UI 4.2.0.

**Solucao:** Usar os nomes exatos que o template do WPF-UI realmente consome (verificados
via `strings Wpf.Ui.dll | grep` — veja RES-001):

```xml
<!-- App.xaml ou UserControl.Resources -->
<SolidColorBrush x:Key="CheckBoxCheckBackgroundFillChecked" Color="#16A34A" />
<SolidColorBrush x:Key="CheckBoxCheckBackgroundFillCheckedPointerOver" Color="#15803D" />
<SolidColorBrush x:Key="CheckBoxCheckBackgroundFillCheckedPressed" Color="#166534" />
<SolidColorBrush x:Key="CheckBoxCheckGlyphForeground" Color="White" />
```

**Atencao aos nomes** — WPF-UI 4.2.0 tem convencao propria, diferente de WinUI 3:

| Elemento | Resource correto |
|----------|------------------|
| Fundo do quadradinho quando checked | `CheckBoxCheckBackgroundFillChecked` |
| Fundo quando checked + hover | `CheckBoxCheckBackgroundFillCheckedPointerOver` |
| Fundo quando checked + pressed | `CheckBoxCheckBackgroundFillCheckedPressed` |
| Checkmark ✓ | **`CheckBoxCheckGlyphForeground`** (singular, SEM sufixo de estado!) |

Nomes tentados que **NAO existem** (sao ignorados sem erro):

- ~~`CheckBoxCheckGlyphForegroundChecked`~~
- ~~`CheckBoxCheckBackgroundStrokeChecked*`~~
- ~~`CheckBoxCheckBackgroundFillCheckedDisabled`~~

Veja RES-001 para descobrir os nomes reais antes de usar.

---

## CTRL-006: ClearButtonEnabled="False" em campos curtos

**Problema:** `ui:TextBox` com `MaxLength` pequeno (2 para dd, 4 para yyyy, HH, mm) exibe
um botao "X" ao digitar. Em campos tao curtos, o X atrapalha visualmente (sobrepoe o
digito) e nao agrega — apagar 2-4 caracteres com Backspace e trivial.

**Solucao:** Setar explicitamente `ClearButtonEnabled="False"`:

```xml
<ui:TextBox x:Name="txtDay"
            Width="40" MaxLength="2"
            PlaceholderText="dd"
            ClearButtonEnabled="False"
            PreviewTextInput="DigitsOnly_PreviewTextInput" />
```

**Quando usar:** Campos de 1-5 caracteres (dia, mes, ano, hora, minuto, MMSI parcial).

**Quando NAO usar:** Campos longos (nome de navio, comentarios, paths, URLs) — o X ajuda
a limpar o conteudo rapidamente.

---

## CTRL-007: Cor customizada do ProgressRing

**Problema:** `ui:ProgressRing` usa a cor accent padrao do tema (azul) para o arco
animado. Quer trocar por brand color.

**Solucao:** WPF-UI 4.2.0 expoe apenas 2 resources uteis para o ProgressRing:

```xml
<!-- App.xaml -->
<SolidColorBrush x:Key="ProgressRingForegroundThemeBrush" Color="#DF0024" />
<SolidColorBrush x:Key="ProgressRingBackgroundThemeBrush" Color="#333333" />
```

`Foreground` e o arco animado, `Background` e o circulo estatico atras. Todos os
`<ui:ProgressRing />` do app passam a usar brand color automaticamente, sem precisar
configurar por instancia.

---

## RES-001: Descobrindo nomes exatos de DynamicResource do WPF-UI

**Problema:** Quer customizar cor de algum estado de um controle WPF-UI, mas nao sabe o
nome exato do `DynamicResource` que o template usa. Chutar um nome
(`CheckBoxCheckGlyphForegroundChecked`, `ButtonBackgroundChecked`, etc.) costuma falhar
silenciosamente — o WPF-UI nao avisa quando um resource nao e encontrado.

**Solucao:** Extrair os nomes diretamente do `Wpf.Ui.dll` via busca binaria.

**Localizacao do DLL (nuget cache):**

```
%USERPROFILE%\.nuget\packages\wpf-ui\4.2.0\lib\net8.0-windows7.0\Wpf.Ui.dll
```

**Comando (Git Bash / WSL):**

```bash
DLL="$HOME/.nuget/packages/wpf-ui/4.2.0/lib/net8.0-windows7.0/Wpf.Ui.dll"

# Listar todos os resources de um controle:
grep -a "CheckBox" "$DLL" | tr '\0' '\n' | grep -oE "CheckBox[A-Za-z]+" | sort -u
grep -a "Button" "$DLL" | tr '\0' '\n' | grep -oE "Button(Background|Foreground|BorderBrush)[A-Za-z]*" | sort -u
grep -a "ToggleButton" "$DLL" | tr '\0' '\n' | grep -oE "ToggleButtonForeground[A-Za-z]*" | sort -u
grep -a "AccentButton" "$DLL" | tr '\0' '\n' | grep -oE "AccentButton[A-Za-z]+" | sort -u
```

**PowerShell equivalente:**

```powershell
$dll = "$env:USERPROFILE\.nuget\packages\wpf-ui\4.2.0\lib\net8.0-windows7.0\Wpf.Ui.dll"
Select-String -Path $dll -Pattern "CheckBox[A-Za-z]+" -AllMatches |
    ForEach-Object { $_.Matches.Value } | Sort-Object -Unique
```

**Regra de ouro:** Antes de escrever um override de `DynamicResource`, sempre verifique
que o nome existe no DLL. Se nao existe, o override e inutil — e voce gasta tempo
debugando algo que o template nunca vai consultar.

**Resources descobertos (catalogo parcial):**

| Controle | Resources que EXISTEM | Resources que NAO existem (comuns de chutar) |
|----------|----------------------|---------------------------------------------|
| CheckBox | `CheckBoxCheckBackgroundFillChecked*`, `CheckBoxCheckGlyphForeground` | `CheckBoxCheckGlyphForegroundChecked`, `CheckBoxCheckBackgroundStrokeChecked*` |
| Button Primary | `AccentButtonBackground*`, `AccentButtonForeground*`, `AccentButtonBorderBrushPressed` | — |
| ToggleButton | `ToggleButtonForegroundChecked*` (3 estados), `ToggleButtonBackgroundChecked*` | — |
| ProgressRing | `ProgressRingForegroundThemeBrush`, `ProgressRingBackgroundThemeBrush` | Qualquer variacao de estado |
