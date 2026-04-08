# Form Design — Espacamento, Labels e Respiro

Guia detalhado de design de formularios WPF seguindo Fluent Design System.
Leia quando houver problemas de espacamento, label alignment ou falta de respiro.

---

## Fluent Design Spacing Ramp

Unidade base: **4px**. Todos os valores sao multiplos de 4.

| Token | Valor | Uso |
|-------|-------|-----|
| spacingXS | 4px | Margem minima entre elementos inline |
| spacingS | 8px | Entre botoes, entre controle e header |
| spacingM | 12px | Entre controle e label lateral, entre cards |
| spacingL | 16px | Padding de superficie, margem de pagina |
| spacingXL | 20px | Espacamento medio |
| spacingXXL | **24px** | **Entre campos de formulario (padrao)** |
| spacingXXXL | 32px | Entre grupos de campos |

### Aplicacao em Formularios

```
┌─ Secao (Padding: 16,12,16,16) ──────────────────────┐
│                                                       │
│  [Header Secao]  FontSize=14 SemiBold                │
│  ↕ 8px (spacingS) entre header e primeiro campo      │
│  [Label]          [TextBox                    ]       │
│  ↕ 24px (spacingXXL) entre campos                    │
│  [Label]          [ComboBox                   ]       │
│  ↕ 24px                                              │
│  [Label]          [DatePicker                 ]       │
│                                                       │
└───────────────────────────────────────────────────────┘
↕ 12px (spacingM) entre secoes
┌─ Proxima Secao ──────────────────────────────────────┐
```

---

## Espacamento Entre Campos

### Padrao Fluent (24px)

Microsoft recomenda 24px entre campos de formulario (`Margin="0,24,0,0"`):

```xml
<TextBlock Text="Ship Name" Margin="0,0,0,8" />  <!-- 8px antes do campo -->
<TextBox MinHeight="32" />
<TextBlock Text="Flag" Margin="0,24,0,8" />       <!-- 24px do campo anterior -->
<TextBox MinHeight="32" />
```

### Compacto (8-12px) — para formularios densos

Para formularios com muitos campos (como APT com 80+ controles), o padrao de 24px
consome muito espaco vertical. Um compromisso aceitavel:

```xml
<!-- Label + Campo em Grid row com Margin="0,8" -->
<TextBlock Grid.Row="0" Text="Label" Margin="0,8" VerticalAlignment="Center" />
<TextBox Grid.Row="0" Grid.Column="1" MinHeight="32" Margin="0,4" />
```

**Regra:** Nunca menos que **8px** entre campos. 4px e muito pouco e prejudica legibilidade.

### Tabela de Decisao

| Quantidade de campos | Spacing recomendado | Margin XAML |
|----------------------|---------------------|-------------|
| Ate 10 campos | 24px (padrao Fluent) | `Margin="0,24,0,0"` |
| 10-30 campos | 12px (compacto) | `Margin="0,12,0,0"` ou `Margin="0,6"` |
| 30+ campos (formulario denso) | 8px (minimo) | `Margin="0,8,0,0"` ou `Margin="0,4"` |

---

## Margin Cirurgico vs Estilo Implicito (FORM-003)

**Problema:** Em uma pagina onde varias linhas de formulario aparecem "coladas" (inputs
verticalmente encostados nos da linha seguinte), e tentador adicionar um estilo implicito
no `<StackPanel.Resources>` ou `<Page.Resources>` para padronizar o `Margin` de todos os
`TextBox`/`ComboBox`/`UserControl` de uma vez. **Isso quase sempre quebra outros layouts
da mesma pagina.**

### Causa raiz

Estilos implicitos (`<Style TargetType="{x:Type TextBox}">` sem `x:Key`) aplicam-se a
TODOS os elementos do tipo dentro do escopo do Resources. Paginas reais de formulario
costumam misturar:

- Grids verticais de campos rotulados (onde a margem vertical ajuda)
- `StackPanel Orientation="Horizontal"` para grupos inline (label + 1 input + botao)
- UserControls horizontais (data, hora) que internamente usam TextBox/ComboBox
- Toolbar com botoes/inputs lado a lado

Adicionar margem vertical em TODOS os TextBoxes/ComboBoxes da pagina desalinha tudo que
nao e form vertical. O sintoma e: "consertei o espacamento mas o controle X esta deslocado
agora".

### Errado — estilo implicito amplo

```xml
<StackPanel Width="900">
    <StackPanel.Resources>
        <Style TargetType="{x:Type TextBox}">
            <Setter Property="Margin" Value="0,4" />
        </Style>
        <Style TargetType="{x:Type ComboBox}">
            <Setter Property="Margin" Value="0,4" />
        </Style>
    </StackPanel.Resources>
    <!-- Afeta TextBox/ComboBox em StackPanel horizontal tambem -> desalinha -->
</StackPanel>
```

### Correto — Margin cirurgico nos inputs do formulario

```xml
<Grid>  <!-- form vertical -->
    <Grid.RowDefinitions>
        <RowDefinition Height="Auto" />
        <RowDefinition Height="Auto" />
    </Grid.RowDefinitions>
    <TextBlock Grid.Row="0" Grid.Column="0" Text="Flag" Margin="0,8" />
    <TextBox   Grid.Row="0" Grid.Column="1" Margin="0,4" />  <!-- explicito -->
    <TextBlock Grid.Row="1" Grid.Column="0" Text="Tonnage" Margin="0,8" />
    <TextBox   Grid.Row="1" Grid.Column="1" Margin="0,4" />  <!-- explicito -->
</Grid>
```

### Alternativa — Style com `x:Key` aplicado seletivamente

```xml
<Page.Resources>
    <Style x:Key="FormFieldInput" TargetType="TextBox">
        <Setter Property="Margin" Value="0,4" />
    </Style>
</Page.Resources>
...
<TextBox Style="{StaticResource FormFieldInput}" />
<!-- TextBoxes que NAO recebem o style continuam intactos -->
```

### Por que `Margin` no input e melhor que `Margin` no `RowDefinition`

Com `RowDefinition Height="Auto"` a altura da linha = `max(label+margem, input)`. Quando
o input e mais alto que o label, a margem so do label nao cria espaco entre linhas
vizinhas — os inputs adjacentes acabam encostando. Uma `Margin="0,4"` no input garante
4px de respiro acima e abaixo dele independente do que o label faz.

### Quando o estilo implicito E aceitavel

Quando voce tem certeza absoluta de que aquele escopo de Resources contem APENAS controles
de formulario verticais e NENHUM layout misto (toolbar, StackPanel horizontal, UserControl
horizontal). Em paginas reais, isso e raro — quase sempre a versao cirurgica e mais segura.

---

## Label Placement

### Labels ao lado (horizontal) — padrao deste projeto

Para formularios densos com muitos campos, labels ao lado economizam espaco vertical:

```xml
<Grid>
    <Grid.ColumnDefinitions>
        <ColumnDefinition Width="200" />  <!-- Label coluna fixa -->
        <ColumnDefinition Width="*" />    <!-- Campo expandivel -->
    </Grid.ColumnDefinitions>

    <TextBlock Grid.Column="0" Text="Ship Name"
               Foreground="{DynamicResource TextFillColorSecondaryBrush}"
               VerticalAlignment="Center" Margin="0,8" />
    <TextBox Grid.Column="1" MinHeight="32" />
</Grid>
```

**Largura do label:** 200px e adequado para labels ate ~25 caracteres em ingles.
Para labels mais longos, considere 240-280px.

### Labels acima (vertical) — recomendacao Microsoft

Para formularios com poucos campos (ate 10), labels acima sao mais faceis de localizar:

```xml
<StackPanel Margin="0,24,0,0">
    <TextBlock Text="Ship Name"
               Style="{StaticResource BodyTextBlockStyle}"
               Margin="0,0,0,8" />
    <TextBox MinHeight="32" />
</StackPanel>
```

Ou usando a propriedade `Header` do WPF-UI:

```xml
<ui:TextBox Header="Ship Name" MinHeight="32" Margin="0,24,0,0" />
```

---

## Padding de Secoes

### Border/Card como container de secao

```xml
<Style x:Key="SectionBorder" TargetType="Border">
    <Setter Property="BorderBrush"
            Value="{DynamicResource ControlStrokeColorDefaultBrush}" />
    <Setter Property="BorderThickness" Value="1" />
    <Setter Property="CornerRadius" Value="4" />
    <Setter Property="Margin" Value="0,12" />        <!-- 12px entre secoes -->
    <Setter Property="Padding" Value="16,12,16,16" /> <!-- respiro interno -->
</Style>
```

**Comparacao de Padding:**

| Padding | Visual | Uso |
|---------|--------|-----|
| `12,8,12,12` | Apertado | Formularios muito densos |
| `16,12,16,16` | Confortavel | **Recomendado** |
| `20,16,20,20` | Espadoso | Formularios com poucos campos |

---

## Separadores entre Zonas

Para separar grandes areas do formulario (ex: paginas do PDF):

```xml
<Style x:Key="ZoneSeparator" TargetType="Border">
    <Setter Property="BorderBrush"
            Value="{DynamicResource DividerStrokeColorDefaultBrush}" />
    <Setter Property="BorderThickness" Value="0,0,0,1" />
    <Setter Property="Margin" Value="0,24,0,24" />  <!-- 24px acima e abaixo -->
</Style>
```

---

## Largura do Formulario

Para formularios dentro de ScrollViewer, usar largura fixa centralizada:

```xml
<ScrollViewer VerticalScrollBarVisibility="Auto">
    <StackPanel Width="900" HorizontalAlignment="Center">
        <!-- secoes -->
    </StackPanel>
</ScrollViewer>
```

**Valores recomendados:**

| Cenario | Width |
|---------|-------|
| Formulario padrao | 800-900px |
| Formulario com 3+ colunas | 1000-1100px |
| Formulario simples (poucas colunas) | 600-700px |
| Maximo antes de parar de expandir | 600px (Win32 guideline) |
