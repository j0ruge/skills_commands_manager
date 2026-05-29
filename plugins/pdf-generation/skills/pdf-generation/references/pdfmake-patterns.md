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

### Fonte Roboto bundled tem ligaduras "fi"/"fl"/"ffi" quebradas

A Roboto que vem dentro de `pdfmake@0.3.x` em `pdfmake/fonts/Roboto/Roboto-Regular.ttf` tem tabela GSUB com ligaduras OpenType que o fontkit interno do pdfkit aplica, mas o glyph resultante é renderizado **vazio**. Palavras com "fi"/"fl"/"ffi" perdem a letra "f":

| Original | Renderizado |
|----------|-------------|
| `fiscal` | `fscal` |
| `fixture` | `fxture` |
| `confirmação` | `confrmação` |
| `oficial` | `ofcial` |
| `específico` | `específco` |
| `final` | `fnal` |

**Diagnóstico**: se uma palavra rara perdeu uma letra "f" interna, é esse bug. Não é typo do banco.

**Cura** (em ordem de simplicidade):

1. **Bundle uma versão atualizada do Roboto** baixada do Google Fonts moderno (a versão TTF bundled no pdfmake é antiga e tem o GSUB problemático)
2. **Trocar por outra fonte TTF sem o bug**: Inter, Open Sans, Source Sans 3 — todas têm ligaduras OpenType corretas
3. **NÃO tentar**: trocar para Helvetica via AFM (ver próximo pitfall) — não funciona

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
