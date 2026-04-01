# Tipografia e Cores — Windows 11 / Fluent Design / Dark Theme

Guia de tipografia, cores e contraste para WPF com WPF-UI dark theme.
Leia quando houver problemas de FontSize, cores ou contraste.

---

## Type Ramp do Windows 11

Fonte padrao: **Segoe UI Variable**

| Estilo | Tamanho | Line Height | Peso | Uso |
|--------|---------|-------------|------|-----|
| Caption | 12px | 16px | Regular | Hints, textos auxiliares, timestamps |
| Body | **14px** | 20px | Regular | **Labels, texto padrao, conteudo** |
| Body Strong | 14px | 20px | SemiBold | Sub-headers de secao, enfase |
| Body Large | 18px | 24px | Regular | Subtitulos, titulos secundarios |
| Subtitle | 20px | 28px | SemiBold | Titulos de grupo/secao |
| Title | 28px | 36px | SemiBold | Titulo de pagina |
| Title Large | 40px | 52px | SemiBold | Hero text |
| Display | 68px | 92px | SemiBold | Numeros grandes, dashboards |

### Uso em XAML

**TextBlock padrao:**
```xml
<TextBlock FontSize="14" />                              <!-- Body -->
<TextBlock FontSize="14" FontWeight="SemiBold" />        <!-- Body Strong -->
<TextBlock FontSize="20" FontWeight="SemiBold" />        <!-- Subtitle -->
<TextBlock FontSize="28" FontWeight="SemiBold" />        <!-- Title -->
```

**WPF-UI TextBlock (preferivel):**
```xml
<ui:TextBlock FontTypography="Body" />
<ui:TextBlock FontTypography="BodyStrong" />
<ui:TextBlock FontTypography="Subtitle" />
<ui:TextBlock FontTypography="Title" />
```

**XAML TextBlock Styles (WinUI-compatible):**
```xml
<TextBlock Style="{StaticResource CaptionTextBlockStyle}" />
<TextBlock Style="{StaticResource BodyTextBlockStyle}" />
<TextBlock Style="{StaticResource BodyStrongTextBlockStyle}" />
<TextBlock Style="{StaticResource SubtitleTextBlockStyle}" />
<TextBlock Style="{StaticResource TitleTextBlockStyle}" />
```

### Regras

- **Minimo absoluto:** 12px (Caption). Nunca usar menos.
- **Texto padrao:** 14px (Body). Labels, conteudo de campos.
- **Headers de secao:** 14px SemiBold (Body Strong) ou 20px SemiBold (Subtitle).
- **Titulo de pagina:** 28px SemiBold (Title).
- **Controles de input:** FontSize >= 13px para legibilidade.

---

## Dark Theme — Cores Completas

### Background e Surface

| Resource Name | Hex | Descricao |
|---------------|-----|-----------|
| SolidBackgroundFillColorBaseAlt | `#0A0A0A` | Background mais profundo |
| SolidBackgroundFillColorSecondary | `#1C1C1C` | Background secundario |
| **SolidBackgroundFillColorBase** | **`#202020`** | **Background principal do app** |
| SolidBackgroundFillColorTertiary | `#282828` | Background terciario |
| SolidBackgroundFillColorQuarternary | `#2C2C2C` | Background quaternario |
| SolidBackgroundFillColorQuinary | `#333333` | Background quinario |
| SolidBackgroundFillColorSenary | `#373737` | Background senario |

**Principio:** Em dark theme, cores mais escuras = superficies menos importantes.
Superficies importantes sao destacadas com cores mais claras.

### Card e Layer

| Resource | Hex | Descricao |
|----------|-----|-----------|
| CardBackgroundFillColorSecondary | `#08FFFFFF` | Card sutil |
| CardBackgroundFillColorDefault | `#0DFFFFFF` | Card padrao |
| CardBackgroundFillColorTertiary | `#12FFFFFF` | Card enfatizado |
| LayerFillColorDefault | `#4C3A3A3A` | Overlay de layer |

### Texto / Foreground

| Resource | Hex | Opacidade | Descricao |
|----------|-----|-----------|-----------|
| **TextFillColorPrimary** | `#FFFFFF` | 100% | Texto principal |
| **TextFillColorSecondary** | `#C5FFFFFF` | ~77% | Labels, texto secundario |
| TextFillColorTertiary | `#87FFFFFF` | ~53% | Hints, placeholders |
| TextFillColorDisabled | `#5DFFFFFF` | ~36% | Texto desabilitado |
| TextFillColorInverse | `#E4000000` | ~89% black | Texto sobre accent |

### Bordas e Separadores

| Resource | Hex | Descricao |
|----------|-----|-----------|
| ControlStrokeColorDefault | `#12FFFFFF` | Borda padrao de controle |
| ControlStrokeColorSecondary | `#18FFFFFF` | Borda secundaria |
| DividerStrokeColorDefault | `#15FFFFFF` | Divisores/separadores |
| CardStrokeColorDefault | `#19000000` | Borda de card |
| SurfaceStrokeColorDefault | `#66757575` | Borda de superficie |

### Controles

| Resource | Hex | Descricao |
|----------|-----|-----------|
| ControlFillColorDefault | `#0FFFFFFF` | Background padrao de controle |
| ControlFillColorSecondary | `#15FFFFFF` | Hover state |
| ControlFillColorTertiary | `#08FFFFFF` | Pressed state |
| ControlFillColorDisabled | `#0BFFFFFF` | Desabilitado |
| ControlFillColorInputActive | `#B31E1E1E` | Input field ativo |

### Uso em XAML

```xml
<!-- Labels -->
<TextBlock Foreground="{DynamicResource TextFillColorSecondaryBrush}" />

<!-- Bordas de secao -->
<Border BorderBrush="{DynamicResource ControlStrokeColorDefaultBrush}" />

<!-- Separadores -->
<Border BorderBrush="{DynamicResource DividerStrokeColorDefaultBrush}" />

<!-- Texto principal -->
<TextBlock Foreground="{DynamicResource TextFillColorPrimaryBrush}" />
```

---

## Contraste — WCAG Accessibility

### Ratios Minimos

| Elemento | Ratio minimo | Padrao |
|----------|-------------|--------|
| Texto normal (< 24px) | **4.5:1** | WCAG AA |
| Texto bold (>= 19px) | **3:1** | WCAG AA |
| Texto grande (>= 24px) | **3:1** | WCAG AA |
| Componentes UI nao-texto | **3:1** | WCAG 2.1 AA |

### Verificacao com Dark Theme

| Combinacao | Ratio aprox | OK? |
|-----------|-------------|-----|
| #FFFFFF sobre #202020 | 15.4:1 | Excelente |
| #C5FFFFFF sobre #202020 | ~12:1 | Bom |
| #B0B0B0 sobre #202020 | ~8.5:1 | Bom |
| #87FFFFFF sobre #202020 | ~7:1 | Aceitavel |
| #5DFFFFFF sobre #202020 | ~4.5:1 | Limite |
| #666666 sobre #202020 | ~2.8:1 | **FALHA** para texto normal |

### Suporte a Text Scaling

Windows suporta text scaling de 1.0x a 2.25x. Controles WPF-UI respeitam
automaticamente. Evite `MaxHeight` fixo em controles de texto que impeca
expansao com scaling.

---

## Shapes e Borders

### Corner Radius

| Token | Valor | Uso |
|-------|-------|-----|
| borderRadiusSmall | 2px | Badges, shapes < 32px |
| **borderRadiusMedium** | **4px** | **Padrao — botoes, dropdowns, controles** |
| borderRadiusLarge | 6px | — |
| borderRadiusXLarge | 8px | Botoes grandes |
| borderRadius2XLarge | 12px | Popovers, sheets |

### Stroke Widths

| Token | Valor |
|-------|-------|
| strokeWidthThin | 1px |
| strokeWidthThick | 2px |
| strokeWidthThicker | 3px |

**Nota:** Windows usa **strokes em vez de shadows** para delinear objetos
(diferente de web/mobile que usam sombras).
