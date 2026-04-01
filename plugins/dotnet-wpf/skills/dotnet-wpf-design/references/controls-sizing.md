# Controls Sizing — Dimensoes Minimas e Recomendadas

Guia de sizing para controles WPF e controles customizados.
Leia quando houver controles pequenos, texto cortado ou touch targets inadequados.

---

## Dimensoes Padrao (Fluent Design)

### Controles de Input

| Controle | MinHeight | Height padrao | MinWidth | FontSize |
|----------|-----------|---------------|----------|----------|
| TextBox (single-line) | 32px | 32px | — | 14px |
| TextBox (multi-line) | 60px | — | — | 14px |
| ComboBox | 32px | 32-44px | 100px | 14px |
| NumberBox | 32px | 32px | 80px | 14px |
| PasswordBox | 32px | 32px | — | 14px |
| DatePicker | 32px | 32px | 120px | 14px |

### Controles de Acao

| Controle | MinHeight | MinWidth | FontSize |
|----------|-----------|----------|----------|
| Button | 32px | — | 14px |
| ToggleButton | 28px | 48px | 12px |
| ToggleSwitch | 20px | 40px | — |
| CheckBox | 20px | — | 14px |
| RadioButton | 20px | — | 14px |

### Touch Targets

| Padrao | Tamanho minimo |
|--------|----------------|
| WCAG 2.5.8 (AA) | 24 x 24 px |
| WCAG 2.5.5 (AAA) | 44 x 44 px |
| Microsoft Fluent (iOS/Web) | 44 x 44 px |
| Microsoft Fluent (Android) | 48 x 48 px |
| Win32 minimum | 16 x 16 relative pixels |
| Gap minimo entre interativos | 5 px |

---

## Controles Customizados deste Projeto

### AptDateWPF (Day / Month / Year)

**Atual (problematico):**
```xml
<UserControl Height="27">
    <TextBox Width="35" FontSize="12" />    <!-- Dia: muito estreito -->
    <ComboBox Width="65" FontSize="11" />   <!-- Mes: "Jun." cortado -->
    <TextBox Width="50" FontSize="12" />    <!-- Ano: ok -->
</UserControl>
```

**Recomendado:**
```xml
<UserControl Height="32" Margin="0,2">
    <StackPanel Orientation="Horizontal" VerticalAlignment="Center">
        <TextBox x:Name="txtDay" Width="40" MaxLength="2" FontSize="13"
                 MinHeight="28" TextAlignment="Center"
                 VerticalContentAlignment="Center" />
        <TextBlock Text="/" VerticalAlignment="Center"
                   Margin="4,0" FontSize="13"
                   Foreground="{DynamicResource TextFillColorSecondaryBrush}" />
        <ComboBox x:Name="cmbMonth" Width="80" FontSize="13"
                  MinHeight="28" VerticalContentAlignment="Center" />
        <TextBlock Text="/" VerticalAlignment="Center"
                   Margin="4,0" FontSize="13"
                   Foreground="{DynamicResource TextFillColorSecondaryBrush}" />
        <TextBox x:Name="txtYear" Width="55" MaxLength="4" FontSize="13"
                 MinHeight="28" TextAlignment="Center"
                 VerticalContentAlignment="Center" />
    </StackPanel>
</UserControl>
```

**Mudancas:**
- Height: 27 → 32 (alinha com padrao Fluent)
- ComboBox Width: 65 → 80 (mostra "Jun." completo com padding)
- TextBox Day Width: 35 → 40
- TextBox Year Width: 50 → 55
- FontSize: 11-12 → 13 (mais legivel)
- Margin separadores: 2,0 → 4,0 (mais respiro)

### APTCheckBoxWPF (Yes / No / N-A)

**Atual:**
```xml
<UserControl Height="27" MinWidth="140">
    <ToggleButton Content="Yes" Width="45" Height="25" FontSize="11" />
    <ToggleButton Content="No" Width="45" Height="25" FontSize="11" />
    <ToggleButton Content="N/A" Width="45" Height="25" FontSize="11" />
</UserControl>
```

**Recomendado:**
```xml
<UserControl Height="32" MinWidth="155">
    <StackPanel Orientation="Horizontal" VerticalAlignment="Center">
        <ToggleButton Content="Yes" Width="48" Height="28"
                      FontSize="12" Margin="0,0,4,0" />
        <ToggleButton Content="No" Width="48" Height="28"
                      FontSize="12" Margin="0,0,4,0" />
        <ToggleButton Content="N/A" Width="48" Height="28"
                      FontSize="12" />
    </StackPanel>
</UserControl>
```

**Mudancas:**
- Height: 27 → 32
- ToggleButton: 45x25 → 48x28 (atende touch target minimo 24x24)
- FontSize: 11 → 12 (Caption size, minimo legivel)
- Margin entre botoes: 2px → 4px

### AptTimeWPF (Hour : Minute)

**Atual:**
```xml
<UserControl Height="27">
    <TextBox Width="35" FontSize="12" />
    <TextBox Width="35" FontSize="12" />
</UserControl>
```

**Recomendado:**
```xml
<UserControl Height="32" Margin="0,2">
    <StackPanel Orientation="Horizontal" VerticalAlignment="Center">
        <TextBox Width="40" FontSize="13" MinHeight="28" />
        <TextBlock Text=":" Margin="4,0" FontSize="13" />
        <TextBox Width="40" FontSize="13" MinHeight="28" />
    </StackPanel>
</UserControl>
```

---

## ComboBox Width — Tabela de Referencia

O Width do ComboBox deve acomodar o conteudo mais longo + padding interno (~20px):

| Conteudo | Chars | Width minimo |
|----------|-------|-------------|
| "Jan." a "Dec." | 4 | 80px |
| "Good" / "No Good" | 7 | 120px |
| "JCY-1900" | 8 | 130px |
| "No.1 & No.2" | 12 | 160px |
| "406.031MHz ±5KHz" | 17 | 200px |

### ComboBoxItems com Espacos

**Anti-padrao:** Usar espacos iniciais para padding:
```xml
<ComboBoxItem Content="   Good" />  <!-- 3 espacos = fragil -->
```

**Melhor:** Usar Padding no ComboBox ou nos items:
```xml
<ComboBox Padding="8,4">
    <ComboBoxItem Content="Good" />
</ComboBox>
```

---

## DataGrid Sizing

### Virtualizacao

Para DataGrids com muitas linhas (>100), garantir virtualizacao:

```xml
<DataGrid
    VirtualizingPanel.IsVirtualizing="True"
    VirtualizingPanel.VirtualizationMode="Recycling"
    EnableRowVirtualization="True"
    EnableColumnVirtualization="True" />
```

### Column Sizing

| Estrategia | Quando usar |
|-----------|-------------|
| `Width="*"` | Coluna principal que preenche espaco |
| `Width="Auto"` | Colunas curtas (status, icone) |
| `Width="150"` | Colunas com conteudo previsivel |
| `MinWidth="80"` | Prevenir coluna invisivel |

### Row Height

- MinRowHeight: 32px (padrao Fluent)
- RowHeight: 36-40px para melhor legibilidade
- HeaderRowHeight: 40px
