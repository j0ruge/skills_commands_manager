# pdfmake Patterns & Examples

## Server-Side Setup (Node.js/TypeScript)

```typescript
import pdfmake from "pdfmake";

const fonts = {
  Roboto: {
    normal: "fonts/Roboto-Regular.ttf",
    bold: "fonts/Roboto-Medium.ttf",
    italics: "fonts/Roboto-Italic.ttf",
    bolditalics: "fonts/Roboto-MediumItalic.ttf"
  }
};

pdfmake.addFonts(fonts);

const pdf = pdfmake.createPdf(docDefinition);
const buffer = await pdf.getBuffer();
```

## Tables with Conditional Columns

```typescript
interface ColumnDef {
  header: string;
  width: string | number;
  getValue: (item: Item) => string;
  align?: string;
}

function buildItemsTable(items: Item[]): object {
  const hasDiscount = items.some(i => i.discountPercent > 0);
  const hasTax = items.some(i => i.taxPercent > 0);

  const columns: ColumnDef[] = [
    { header: "Code", width: "auto", getValue: i => i.code },
    { header: "Description", width: "*", getValue: i => i.description },
    { header: "Qty", width: 40, getValue: i => String(i.qty) },
    { header: "Unit Price", width: 70, getValue: i => formatCurrency(i.unitPrice) },
  ];

  if (hasDiscount) {
    columns.push(
      { header: "Disc %", width: 45, getValue: i => `${i.discountPercent}%` },
      { header: "Unit w/o Tax", width: 70, getValue: i => formatCurrency(i.unitNoTax) }
    );
  }

  columns.push({ header: "NCM", width: 65, getValue: i => i.ncm });

  if (hasTax) {
    columns.push(
      { header: "Tax %", width: 45, getValue: i => `${i.taxPercent}%` },
      { header: "Unit w/ Tax", width: 70, getValue: i => formatCurrency(i.unitWithTax) }
    );
  }

  columns.push({ header: "Total", width: 75, getValue: i => formatCurrency(i.total), align: "right" });

  return {
    table: {
      headerRows: 1,
      widths: columns.map(c => c.width),
      body: [
        columns.map(c => ({ text: c.header, bold: true, fillColor: "#333333", color: "#ffffff" })),
        ...items.map(item => columns.map(c => ({
          text: c.getValue(item),
          alignment: c.align || "center"
        })))
      ]
    },
    layout: {
      hLineWidth: (i, node) => (i <= 1 || i === node.table.body.length) ? 1 : 0.5,
      vLineWidth: () => 0.5,
      hLineColor: (i) => i <= 1 ? "#333333" : "#dddddd",
      vLineColor: () => "#dddddd"
    }
  };
}
```

## Multi-Column Info Block

```typescript
function buildInfoBlock(supplier: Filial, client: ClienteData, seller: VendedorData): object {
  return {
    table: {
      widths: ["*", "1.2*", "0.8*"],
      body: [[
        {
          stack: [
            { text: "Fornecedor", bold: true, margin: [0, 0, 0, 4] },
            supplier.razaoSocial,
            supplier.endereco,
            `CNPJ: ${supplier.cnpj}`,
            `I.E.: ${supplier.inscricaoEstadual}`
          ],
          margin: 8
        },
        {
          stack: [
            { text: "Cliente", bold: true, margin: [0, 0, 0, 4] },
            client.empresa,
            `CNPJ: ${client.cnpj}`,
            `Contato: ${client.contato}`,
            `E-mail: ${client.email}`,
            `Tel.: ${client.telefone}`
          ],
          margin: 8
        },
        {
          stack: [
            { text: "Vendedor", bold: true, margin: [0, 0, 0, 4] },
            `Vendedor: ${seller.nome}`,
            `Data: ${formatDate(seller.data)}`,
            `E-mail: ${seller.email}`
          ],
          margin: 8
        }
      ]]
    },
    layout: "noBorders"
  };
}
```

## Dynamic Header with Logo and Revision

```typescript
const docDefinition = {
  header: (currentPage: number) => ({
    columns: [
      { image: logoBase64, width: 80, margin: [40, 20, 0, 0] },
      {
        text: "PROPOSTA COMERCIAL",
        alignment: "right",
        fontSize: 18,
        bold: true,
        margin: [0, 25, 40, 0]
      }
    ]
  }),
  footer: (currentPage: number, pageCount: number) => ({
    text: `PAGE ${currentPage} OF ${pageCount}`,
    alignment: "right",
    fontSize: 8,
    margin: [0, 0, 40, 20],
    color: "#999999"
  }),
  content: [/* sections */],
  pageMargins: [40, 80, 40, 50]
};
```

## Vector Logo (SVG)

pdfmake renders SVG **natively** — `pdfmake@0.2+`/`0.3.x` bundle SVG support (there's an `SVGMeasure.js` inside the package, and `@types/pdfmake` declares a `ContentSvg` interface). A vector logo stays crisp at any zoom and is usually smaller than an equivalent PNG. You do **not** need a separate `svg-to-pdfkit` dependency — the node is just `{ svg, width }`, where `svg` is the raw XML **string** (not a data URI):

```typescript
{ svg: '<svg viewBox="0 0 296 74">…</svg>', width: 155 }   // ✅ vector
{ image: logoDataUri, width: 155 }                          // raster (base64 data URI)
```

> A recurring misconception is that pdfmake can't do SVG (leading people to rasterize or add a dependency). It can — reach for `{ svg }` first for logos and line art.

If a logo can arrive in either format (e.g. a configurable per-branch logo read from disk vs. a bundled default), discriminate before building the node — `{ svg }` and `{ image }` are different content shapes:

```typescript
type LogoAsset =
  | { type: "svg"; svg: string }        // → { svg, width }
  | { type: "raster"; dataUri: string } // → { image, width }
  | null;                               // → blank cell, don't abort generation

function logoCell(logo: LogoAsset) {
  if (logo === null) return { text: "" };
  return logo.type === "svg"
    ? { svg: logo.svg, width: 155 }
    : { image: logo.dataUri, width: 155 };
}
```

**Ship the default vector as a `.ts` string constant, not a file on disk.** Two deploy traps make a file fragile, and both fail *silently* (blank logo, no error):

- A `tsc → dist/` build does **not** copy non-`.ts` files — an `.svg` placed under `src/` never reaches the bundle.
- A gitignored runtime asset dir (e.g. `storage/`) won't exist on a fresh checkout/deploy.

A small SVG (a few KB) embedded as `export const LOGO_SVG = '<svg…>'` sidesteps both: it compiles to JS automatically, is version-controlled, and needs no file I/O. Keep the design `.svg` as the source of truth and generate the constant from it (see the inline-fill transform in Pitfalls).

## Bold Markup Parser

```typescript
interface TextSegment {
  text: string;
  bold?: boolean;
}

function parseBoldMarkdown(input: string): TextSegment[] {
  if (!input || !input.includes("**")) return [{ text: input || "" }];

  const parts = input.split(/(\*\*[^*]+\*\*)/);
  return parts
    .filter(p => p.length > 0)
    .map(part => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return { text: part.slice(2, -2), bold: true };
      }
      return { text: part };
    });
}
```

## Observation Engine Pattern

```typescript
type ObservationRule = (data: QuoteSnapshot) => string | null;

const rules: ObservationRule[] = [
  (data) => {
    if (data.sinalAntecipacao <= 0) return null;
    const saldo = data.totalCotacao - data.sinalAntecipacao;
    return `O valor total desta proposta é de **${fmt(data.totalCotacao)}**. `
      + `Para fins de quitação financeira, será considerado o abatimento do `
      + `sinal/adiantamento de **${fmt(data.sinalAntecipacao)}**. `
      + `O boleto será gerado sobre o saldo de **${fmt(saldo)}**.`;
  },
  (data) => {
    if (data.tipoFrete !== "CIF" || !data.clienteCidade) return null;
    return `Valor do frete incluso para **${data.clienteCidade}**.`;
  },
  (data) => {
    if (!data.beneficioFiscalCodigo) return null;
    return `Proposta contempla benefício fiscal: **${data.beneficioFiscalDescricao}**.`;
  },
  (data) => {
    if (data.tipoOperacao !== "REVENDA") return null;
    return "Operação destinada à revenda — alíquotas conforme regime do destinatário.";
  }
];

function generateObservations(data: QuoteSnapshot, freeText?: string): string {
  const auto = rules.map(r => r(data)).filter(Boolean).join("\n");
  return [auto, freeText].filter(Boolean).join("\n\n");
}
```

## Hash-Based Revision Control

```typescript
import { createHash } from "node:crypto";

function computeSnapshotHash(cotacao: CotacaoSnapshot, termos: TermoSnapshot[], filial: FilialSnapshot): string {
  const payload = JSON.stringify({ cotacao, termos, filial }, Object.keys({ cotacao, termos, filial }).sort());
  return createHash("sha256").update(payload).digest("hex");
}

async function getOrCreateRevision(cotacaoId: string, hash: string, generatePdf: () => Promise<Buffer>): Promise<{ revisao: number; pdfPath: string }> {
  const latest = await findLatestRevision(cotacaoId);

  if (latest && latest.hashDados === hash) {
    return { revisao: latest.revisao, pdfPath: latest.pdfPath };
  }

  const nextRev = latest ? latest.revisao + 1 : 0;
  const buffer = await generatePdf();
  const pdfPath = `storage/pdfs/${cotacao.numero}-Rev${nextRev}.pdf`;
  await writeFile(pdfPath, buffer);
  await saveRevisionRecord(cotacaoId, nextRev, pdfPath, hash);

  return { revisao: nextRev, pdfPath };
}
```

## Custom Table Layout

```typescript
const proposalLayout = {
  hLineWidth: (i: number, node: any) => {
    if (i === 0 || i === node.table.body.length) return 1;
    return i === node.table.headerRows ? 2 : 0.5;
  },
  vLineWidth: () => 0.5,
  hLineColor: (i: number, node: any) => {
    if (i === 0 || i === node.table.body.length) return "#333333";
    return i === node.table.headerRows ? "#333333" : "#eeeeee";
  },
  vLineColor: () => "#dddddd",
  paddingLeft: () => 6,
  paddingRight: () => 6,
  paddingTop: () => 4,
  paddingBottom: () => 4
};
```

## Two-Column Summary (Conditions + Totals)

```typescript
function buildSummary(conditions: ConditionData, totals: TotalsData): object {
  return {
    columns: [
      {
        width: "*",
        stack: [
          { text: [{ text: "Validade: ", bold: true }, `${conditions.validadeDias} Dias`] },
          { text: [{ text: "Prazo entrega: ", bold: true }, conditions.prazoEntrega] },
          { text: [{ text: "Pagamento: ", bold: true }, conditions.formaPagamento] },
          { text: [{ text: "Frete: ", bold: true }, conditions.frete] },
        ],
        fontSize: 10
      },
      {
        width: "*",
        stack: [
          { columns: [{ text: "Total Produto:", width: "*" }, { text: fmt(totals.mercadoria), alignment: "right" }] },
          { columns: [{ text: "Total Desconto:", width: "*" }, { text: fmt(totals.desconto), alignment: "right" }] },
          { columns: [{ text: "Total IPI:", width: "*" }, { text: fmt(totals.ipi), alignment: "right" }] },
          {
            columns: [
              { text: "Valor Total >>>", width: "*", bold: true, fontSize: 12 },
              { text: fmt(totals.total), alignment: "right", bold: true, fontSize: 12 }
            ],
            margin: [0, 8, 0, 0],
            background: "#f5f5f5"
          }
        ],
        fontSize: 10
      }
    ],
    columnGap: 20
  };
}
```

## Pitfalls — pdfmake v0.3.x + TypeScript

### `pdfmake/interfaces` não resolve em `moduleResolution: "NodeNext"`

`@types/pdfmake` declara tipos em `pdfmake/interfaces`, mas o `package.json` do pdfmake **não exporta** o subpath `./interfaces`. Com `moduleResolution: "NodeNext"`, o import falha:

```
error TS2307: Cannot find module 'pdfmake/interfaces'
```

**Fix**: criar um shim local com os tipos necessários:

```typescript
// pdf/pdfmake-types.ts
/* eslint-disable @typescript-eslint/no-explicit-any */
export type Content = Record<string, any> | string | Content[];
export type TableCell = Record<string, any> | string | number;
export type ContentText = Record<string, any>;
```

Importar `from "./pdfmake-types.js"` nos arquivos de seção em vez de `from "pdfmake/interfaces"`.

### Font path em monorepos — usar `require.resolve`

Paths relativos (`node_modules/pdfmake/fonts/...`) falham em monorepos com hoisting. Resolver via `require.resolve`:

```typescript
import { createRequire } from "node:module";
import path from "node:path";

function resolveRobotoFont(filename: string): string {
  const require = createRequire(import.meta.url);
  const root = path.dirname(require.resolve("pdfmake/package.json"));
  return path.join(root, "fonts", "Roboto", filename);
}
```

Funciona independentemente de onde `node_modules/pdfmake` foi instalado (raiz do monorepo, workspace-level, etc.).

### Cell padding NÃO é descontado de `widths` — última coluna corta silenciosamente

**Bug mais grave deste pitfall set.** O array `widths: [...]` declara apenas a largura **do conteúdo**, não a largura total da célula. O layout default (e os builtin `lightHorizontalLines`/`noBorders`) adiciona `paddingLeft: 4` + `paddingRight: 4` = **8pt por célula**, somados ao conteúdo. Com 8 colunas isso adiciona 64pt; com 10, 80pt — facilmente excede a largura útil de uma página A4 (≈515pt com margens 40pt).

**Sintoma**: a coluna mais à direita (geralmente "Total" em invoices) some do PDF, sem erro nem warning. Os dados ainda estão no `body`, mas são renderizados fora da página visível.

**Não confunda com**: colunas `auto` colapsando — esse é outro problema. Se o sintoma é "última coluna sumiu mesmo com widths fixos", é padding.

**Fix**: layout customizado com padding reduzido (2pt cada lado economiza 32pt para 8 colunas):

```typescript
const tableLayoutCompact = {
  hLineWidth: (i, node) => {
    if (i === 0 || i === node.table.body.length) return 0.7;
    return i === 1 ? 0.7 : 0.3;
  },
  vLineWidth: () => 0,
  hLineColor: (i, node) => {
    if (i === 0 || i === node.table.body.length || i === 1) return "#999999";
    return "#dddddd";
  },
  paddingLeft: () => 2,
  paddingRight: () => 2,
  paddingTop: () => 3,
  paddingBottom: () => 3,
};

// ... aplicar no table:
{ table: { widths, body }, layout: tableLayoutCompact }
```

**Regra prática**: ao dimensionar widths fixos, considerar que cada coluna consome `width + 2 × paddingHorizontal`. Para 8 colunas em A4 com padding 2pt, descontar `8 × 4 = 32pt` da largura útil ao planejar.

### Fonte Roboto bundled: ligaduras "fi"/"fl"/"ffi" somem do PDF

Palavras com "fi"/"fl"/"ffi" perdem a letra "f" no PDF renderizado:

| Original | Renderizado |
|----------|-------------|
| `fiscal` | `fscal` |
| `fixture` | `fxture` |
| `confirmação` | `confrmação` |
| `oficial` | `ofcial` |
| `específico` | `específco` |
| `final` | `fnal` |

**Diagnóstico**: se uma palavra rara perdeu uma letra "f" interna, é esse bug — não é typo do banco.

**Causa real** (verificada por parse SFNT — corrige o diagnóstico "fonte antiga / glyph vazio" de versões anteriores): a Roboto bundled em `pdfmake@0.3.9` é **atual** (`name[5]` = "Version 3.014; 2025"), tem `GSUB` com as features `liga`/`dlig` **ativas**, e os glifos de ligadura **existem** no `cmap` (`U+FB01`/`FB02`/`FB03` → glyphs 471/472/473). A cadeia pdfkit/fontkit interna **aplica** a substituição `liga` (`f`+`i` → glyph 471) durante o layout, mas **falha ao embutir/subsetar** esse glifo no PDF — daí o "fi" sumir. Não é fonte velha nem glyph ausente: é o embedding do glifo de ligadura quebrado no pipeline do pdfmake 0.3.x.

**Confirme antes de trocar a fonte.** Chutar "a fonte está quebrada" custa tempo; as tabelas SFNT respondem direto: `name[5]` = versão, `GSUB` = features ativas, `cmap` = se o glifo de ligadura existe. Glifo presente + feature ativa + palavra sumindo ⇒ o problema é embedding (pipeline), não a fonte.

**Cura** (em ordem de custo):

1. **Desabilitar a ligadura** — se a sua versão do pdfmake/pdfkit expuser controle de features OpenType, desligar `liga` evita a substituição e, com ela, o glifo problemático. Mais barato que trocar a fonte; tentar primeiro.
2. **Bundle um TTF que você controla** — Roboto atual (ou Inter/Open Sans/Source Sans 3) baixado e versionado nos seus assets, resolvido por path próprio em vez de `node_modules/pdfmake`. **Cuidado**: não assuma que a fonte do front serve — pacotes `@fontsource-variable/*` entregam **só `.woff2`**, e pdfmake/pdfkit exigem **TTF/OTF** (`.woff2` não é consumível). Confirme que existe um `.ttf`/`.otf` antes de planejar a troca.
3. **NÃO tentar**: trocar para Helvetica via AFM (ver próximo pitfall) — não funciona.

**Após qualquer fix, verifique visualmente** (Phase 6): abrir o PDF e conferir "fiscal" com o "i". Nenhum teste automatizado pega isso.

### `pdfmake.addFonts()` rejeita AFM silenciosamente — erro 500 no render

Tentativa intuitiva: como o `pdfkit` (transitivo de pdfmake) bundla os AFM das 14 Standard PDF Fonts em `pdfkit/js/data/Helvetica.afm`, parece razoável registrar:

```typescript
pdfmake.addFonts({
  Roboto: {
    normal: resolveStandardFont("Helvetica.afm"),
    // ...
  },
});
```

`addFonts()` aceita silenciosamente (não há validação). Mas no momento de `getBuffer()`, o `fontkit` falha porque AFM são **apenas métricas, sem glifos** — o erro borbulha como erro 500 genérico no endpoint, sem indicação clara da causa.

**Conclusão**: pdfmake requer **TTF/OTF**. As Standard PDF Fonts (Helvetica, Times, Courier) não são acessíveis via `addFonts()`. Se precisar dessas fontes, considere usar `pdf-lib` diretamente, ou bundle uma versão TTF (ex: `Helvetica-Neue.ttf` se licenciado, ou Nimbus Sans no espírito Helvetica).

### Header/footer em `content[]` não repetem — use os slots `header`/`footer`

Sintoma: o cabeçalho (logo, título, barra de número) e/ou o rodapé com numeração aparecem na **página 1** e somem da **página 2** em diante.

**Causa**: os nós de header/footer foram empurrados para dentro do array `content[]` do `docDefinition`. `content[]` é o **fluxo** do documento — renderiza uma vez, na ordem, e não se repete por página. Quem repete por página são os **slots dedicados** `header`/`footer` do `docDefinition`, que aceitam função `(currentPage, pageCount) => Content`.

```typescript
// ❌ ERRADO — renderiza uma vez no topo; pág. 2+ fica sem header
const docDefinition = { content: [ buildHeader(), ...sections ] };

// ✅ CERTO — header/footer rodam por página (ver "Dynamic Header with Logo and Revision")
const docDefinition = {
  header: (currentPage, pageCount) => buildHeader(currentPage),
  footer: (currentPage, pageCount) => buildFooter(currentPage, pageCount),
  content: [ ...sections ],
};
```

**Por que escapa dos testes**: em uma cotação de **1 página** os dois layouts são visualmente idênticos — o bug só se manifesta na página 2. Por isso a Phase 6 exige renderizar e inspecionar **a página 2+**, não só a primeira. Cuidado também com a margem superior/inferior da página (`pageMargins`): com header/footer nos slots, reserve espaço suficiente para eles não sobreporem o conteúdo.

### Bloco se parte no meio / título de seção fica órfão — agrupe com `unbreakable`

Sintoma: o título de uma seção (ex.: "TERMOS E CONDIÇÕES") aparece sozinho no fim de uma página e o corpo desce para a próxima; ou um bloco "título + parágrafos" é cortado no meio por uma quebra de página.

**Causa**: título e corpo são nós **irmãos** no `content[]` — o fluxo do documento pode quebrar entre quaisquer dois nós quando o espaço da página acaba. Não existe "keep-together" implícito.

**Fix**: envolva o bloco inteiro num único nó `stack` marcado `unbreakable: true`. O pdfmake trata o stack como indivisível: se não couber no espaço restante da página atual, desce **inteiro** para a próxima — sem deixar o título órfão.

```typescript
// ❌ título e corpo soltos no fluxo → o título pode orfanar no fim da página
content: [ horizontalRule, sectionTitle, ...paragraphs ]

// ✅ bloco indivisível → desce inteiro se não couber
content: [ { stack: [ horizontalRule, sectionTitle, ...paragraphs ], unbreakable: true } ]
```

**Ressalva (degradação graciosa)**: `unbreakable` só mantém junto o que **cabe em uma página**. Um bloco mais alto que a página inteira não tem como ser mantido indiviso — o pdfmake volta a quebrar normalmente (sem clipping nem página em branco), só não faz o impossível. Por isso valide com um render de bloco **alto / muitos itens**, não só um curto.

### SVG com fills via `<style>`/classe não renderiza — inline os `fill`

Um SVG exportado de ferramenta de design (Illustrator/Figma) costuma definir as cores num bloco `<style>` com seletores de classe, em vez de atributos diretos:

```xml
<defs><style>.cls-1{fill:#ec2228;}.cls-2{fill:#1e1e1e;}</style></defs>
<path class="cls-1" d="…"/>
```

O svg-to-pdfkit embutido no pdfmake tem suporte a CSS `<style>`/seletores **limitado** — frequentemente ignora essas regras e renderiza os paths **sem fill** (pretos, ou vazados sobre fundo claro). Não há erro nem warning: o logo só aparece errado no PDF final.

**Fix**: inline o fill como **atributo de apresentação** em cada elemento e descarte o `<style>` — atributo `fill="…"` é sempre respeitado:

```xml
<path fill="#ec2228" d="…"/>   <!-- ✅ -->
```

Faça a transformação ao gerar a constante embutida (ver "Vector Logo (SVG)"): `class="cls-1"` → `fill="#ec2228"`, e remova `<defs><style>…</style></defs>` e `<title>`. É uma substituição barata de string e elimina a dependência do parser de CSS.

**Por que escapa dos testes**: build e testes unitários passam normalmente — o shape do nó `{ svg }` está correto, só a renderização do fill é que falha. Só a **verificação visual** (Phase 6) revela: rasterize (`pdftoppm -png -r 150`) e confirme que as cores aparecem.
