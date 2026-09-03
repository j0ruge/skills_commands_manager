---
name: pdf-generation
metadata:
  version: 1.6.1
description: "PDF generation design toolkit — analyze a reference template, pick the library (pdfmake, pdf-lib, PDFKit, Puppeteer, @react-pdf), and design modular sections with conditional columns, revision control, and visual verification. Carries hard-won pdfmake pitfalls: column widths that silently push the table off the page, colorless SVG logos, glyph-eating ligatures. Triggers — PDF generation, PDF template, pdfmake, invoice/proposal/report PDF, column overflow, SVG logo in PDF."
---

## User Input

```text
$ARGUMENTS
```

Consider the user input before proceeding.

## Purpose

Guide the design and implementation of programmatic PDF generation from structured data. This skill covers the full lifecycle: analyzing reference templates, recommending libraries, designing modular layouts, and producing implementation-ready specifications.

**This skill is NOT for:**
- Acrobat JavaScript / AcroForms (interactive form logic)
- Editing or merging existing PDFs (use `pdf-lib` directly)
- Browser-side PDF viewing (standard iframe/embed)

## Workflow

### Phase 1: Analyze Reference Template

When the user provides a reference PDF, Excel, or image:

1. **Read the reference file** — use the Read tool for PDFs/images
2. **Identify sections** — header, data blocks, tables, summaries, footer
3. **Classify each field** as:
   - **Fixed** — hard-coded in template (company name, terms & conditions, logo)
   - **Dynamic** — comes from system data (client name, item prices, totals)
   - **Calculated** — derived from other fields (subtotals, tax, grand total)
   - **Conditional** — appears only when condition is met (discount column, tax column)
4. **Show visual preview** — if brainstorming visual companion is available, render an HTML mockup mapping fields to data sources. Use color coding:
   - Dynamic fields in **red** (`#ed1c24`)
   - Fixed content in default color
   - Conditional sections with dashed borders

Output a **Field Mapping Table**:

```markdown
| Section | Field | Type | Source | Condition |
|---------|-------|------|--------|-----------|
| Header | Logo | Fixed | config/logo.png | — |
| Header | Quote Number | Dynamic | cotacao.numero | — |
| Items | Discount % | Conditional | item.desconto | Only if any item has discount > 0 |
```

### Phase 2: Recommend Library

Load `references/library-comparison.md` and present a comparison tailored to the user's requirements.

**Key decision factors:**
- Table complexity (number of columns, conditional columns, multi-page pagination)
- Visual fidelity requirements (pixel-perfect vs structured)
- Deployment constraints (server-side vs browser, Docker availability)
- Performance requirements (generation time, concurrent users)
- Future customization needs (designer involvement, CSS-based theming)

**Always recommend one approach** with clear reasoning, and document alternatives for future reference.

### Phase 3: Design Document Structure

Design the PDF as modular sections. Each section is an independent function that returns a document definition fragment.

**Standard section architecture:**

```text
pdf/
├── quote-pdf-generator.ts    ← orchestrator (assembles all sections)
├── sections/
│   ├── header.ts             ← logo + title (repeats on all pages)
│   ├── info-block.ts         ← multi-column info (supplier, client, etc.)
│   ├── items-table.ts        ← data table with conditional columns
│   ├── summary.ts            ← conditions + totals
│   ├── notes.ts              ← auto-generated + free text observations
│   └── terms.ts              ← terms & conditions
├── observation-engine.ts     ← business rules → auto-generated text
├── bold-parser.ts            ← **markdown** → formatted output
├── styles.ts                 ← visual tokens (colors, fonts, margins)
└── fonts.ts                  ← font registration
```

### Phase 4: Handle Common Patterns

#### Conditional Columns

Scan ALL data rows before building the table. Omit columns where no row has a non-zero/non-null value. Redistribute column widths automatically.

```typescript
const hasDiscount = items.some(i => i.descontoPercent > 0);
const hasIpi = items.some(i => i.ipiPercent > 0);
// Build column definitions dynamically
```

#### Units in the Header, Not the Cell

In a data table, declare the unit (`R$`, `$`, `%`, `kg`) **once** — in the column
label, or in a small caption above the table — and leave the cells bare. A
currency prefix repeated in every row buys nothing and costs real width: at 8pt,
`R$` is ~9pt per cell, and across three monetary columns that is the difference
between a value fitting on one line and wrapping.

The trade is asymmetric, which is why this is worth doing by default rather than
as a rescue: **a header that wraps costs one extra line per page; a cell that
wraps breaks the alignment of every row.** So when a label doesn't fit, prefer
shortening the label over narrowing the column — and if even the short label is
too wide, move the unit to a caption (`Valores em R$` / `All amounts in USD`) and
keep all labels short.

```typescript
// Header carries the unit; cells are bare.
headerCell("Unit (R$)");        dataCell(formatCurrencyCell(v));  // "103.927,00"
// If "Unit w/ tax (R$)" is too wide for its column, drop the suffix from all
// monetary labels and add one caption above the table instead.
```

Scope the rule to tables. In running prose ("Deposit of **R$5,000.00** on
signing") and in a totals block, each line is a labelled sentence with no column
header to carry the unit — the prefix belongs in the string there.

Known limit worth stating when you use a caption: it renders **once**, while the
table's `headerRows` repeats on every page. On a multi-page table, page 2 shows
bare labels. That is usually fine when a totals block later in the document
prints the currency, but decide it deliberately rather than discovering it.

#### Measure Text Before Calibrating Column Widths

Guessing a column width and re-rendering to check is a slow loop, and it fails
in the direction that looks safe — a label that "should fit" wraps, and you only
find out by eye. Measure the glyphs instead. With pdfmake you already have
`fontkit` transitively (`pdfmake → pdfkit → fontkit`), so this needs no new
dependency:

```javascript
import { createRequire } from "node:module";
import path from "node:path";
import * as fontkit from "fontkit"; // namespace import — there is no default export
const require = createRequire(import.meta.url);
const root = path.dirname(require.resolve("pdfmake/package.json"));
const font = fontkit.openSync(path.join(root, "fonts", "Roboto", "Roboto-Medium.ttf"));
const widthPt = (s, size) => (font.layout(s).advanceWidth / font.unitsPerEm) * size;
```

Run it from a directory that resolves the project's `node_modules` — a script in
`/tmp` will not. Measure the **header in the bold face** and the **worst-case
cell in the regular face**, then compare both against the declared width. Doing
this before implementing turns column calibration into arithmetic and documents
the ceiling: write the worst case you verified next to each width
(`50, // Unit — fits "9,999,999.99" = 46.3pt`), because that comment is the only
thing that will tell the next person the column has a limit at all.

#### Auto-Generated Observations

Business rules as pure functions: `(data) => string | null`. Compose output by concatenating all non-null results + free text.

#### Bold Markup

Store text with `**bold**` markers. Parse with simple regex split:

```typescript
function parseBold(text: string): Array<{text: string; bold?: boolean}> {
  return text.split(/(\*\*[^*]+\*\*)/).map(part => {
    if (part.startsWith('**') && part.endsWith('**'))
      return { text: part.slice(2, -2), bold: true };
    return { text: part };
  });
}
```

#### Revision Control

Hash-based idempotency: SHA-256 of input data snapshot. Same hash → return cached PDF. Different hash → generate new revision (Rev. 0, 1, 2...).

Note the hash is over the **input data**, not the rendering code. A layout/style change (font size, column widths, a moved field) leaves the hash unchanged, so the cache happily serves the **old** PDF. When verifying a layout edit, invalidate the cache first (delete the persisted revision row + the cached file) — otherwise you'll inspect a stale render and conclude your change "did nothing". See Phase 6.

#### Header/Footer on All Pages

Put header/footer in the document's dedicated `header`/`footer` slots (callback functions), **not** in the `content[]` array. A header node pushed into `content[]` renders **once** at the top of the flow and is silently absent from page 2 onward — and you won't notice in a single-page test. The dedicated slots run per page:

```typescript
footer: (currentPage, pageCount) => ({
  text: `PAGE ${currentPage} OF ${pageCount}`,
  alignment: 'right',
  margin: [40, 10]
})
```

#### Keep a Block Together (no orphaned heading)

A section heading and its body are separate sibling nodes in `content[]` by default, so pdfmake will happily break between them — leaving the heading stranded at the bottom of a page while the body flows onto the next. Wrap the heading + body in a single `{ stack: [...], unbreakable: true }` node and pdfmake keeps the whole block on one page: if it doesn't fit in the remaining space, the entire block moves to the next page.

```typescript
// Heading + body never split across a page boundary
{ stack: [horizontalRule, sectionTitle, ...paragraphs], unbreakable: true }
```

Caveat worth knowing: `unbreakable` only keeps the block together when it fits within **one** page. A block taller than a full page can't be kept whole, so pdfmake falls back to normal breaking — it degrades gracefully (no clipping, no blank page), it just can't do the impossible. So verify with a tall / many-item render, not only a short one.

#### Vector Logos (SVG)

Prefer a vector logo over a raster one — it stays crisp at any zoom. pdfmake renders SVG **natively** via the `{ svg, width }` node (no `svg-to-pdfkit` dependency). Two gotchas decide whether it actually works, both detailed in `references/pdfmake-patterns.md`:

- **Inline the fills.** A design-tool SVG defines colors in a `<style>` block with class selectors (`class="cls-1"`); pdfmake's bundled SVG parser often ignores those and renders the logo with no color (black/blank), silently. Convert each `class="…"` to a direct `fill="…"` attribute.
- **Ship the default vector as a `.ts` constant, not a file.** A `tsc → dist/` build won't copy an `.svg`, and a gitignored runtime asset dir won't exist on a fresh deploy — either way the logo renders blank. Embedding `export const LOGO_SVG = '<svg…>'` survives both.

### Phase 5: Generate Implementation Spec

Produce a complete specification covering:
- Data model (new entities for revision tracking, configurable content)
- API contracts (endpoints for PDF generation, admin CRUD)
- Section-by-section layout description
- Conditional logic rules
- Test scenarios (column combinations, multi-page pagination, revision idempotency)

### Phase 6: Visual Verification

Automated tests cannot catch rendering bugs. Layout overflow, font glyph issues, conditional column logic, and pagination behavior **only show up in the rendered PDF**. Make this an explicit phase, not optional:

1. **Test with real data** — use a quote/invoice with the most rows the system supports (or a realistic stress case: 10–50 line items, long descriptions, large monetary values 6+ digits, and at least one field containing an **unbreakable token** — a long string with no spaces, like `SN:AAA111,BBB222,CCC333`). That last one is not the same test as "long description": length alone wraps fine, while a token with no break opportunity makes the flexible column grow past the page (see `references/pdfmake-patterns.md`). Real data supplies these — serial-number lists, URLs, part codes — so pull a genuinely awkward row rather than typing a tidy one.
2. **Test with edge cases** — single row, max rows, all conditional columns hidden, all visible, multi-page pagination
3. **Render and open EVERY page, not just page 1** — convert each page to an image (`pdftoppm -png -r 150 out.pdf page`) and inspect them. Page 1 looking right tells you nothing about whether the header/footer survive onto page 2 (a frequent bug — see the `content[]` trap below). Always exercise a 2+ page case.
4. **Bust the cache before re-rendering** — if the pipeline caches by input-hash (Revision Control), a layout/code change won't regenerate. Delete the persisted revision + cached file first, or you'll inspect the stale PDF and wrongly conclude your edit had no effect.
5. **Check specific render risks**:
   - Last column not cut at right margin (the pdfmake padding pitfall — see `references/pdfmake-patterns.md`)
   - All values fully visible (no `R$49.12` when value is `R$49.126,35`)
   - Header/footer present on page 2+ — **inspect page 2 itself**; a header placed in `content[]` instead of the `header`/`footer` slots renders once and silently vanishes on later pages
   - Footer page numbers correct
   - Long descriptions wrap, don't overflow — and a description containing an unbreakable token doesn't push the table off the right edge
   - Font glyphs render correctly (no "fiscal"→"fscal" from broken ligatures)
   - Conditional columns omit/appear correctly based on data
   - **Conditional/optional fields: absence ≠ bug.** An optional field that's simply empty looks identical to one that's broken. To confirm a conditional field actually renders, populate it in the test data (or inject it temporarily) — don't conclude it's broken from a case where the data happens to be absent.

6. **Diff the rendered PDF against reference template visually** — open both side-by-side. Automated pixel diff is overkill; human eye catches what matters.

Skipping this phase will ship bugs that passed every automated test.

## References

For detailed guidance on specific topics, load these on demand:

- `references/library-comparison.md` — full comparison of 5 PDF libraries
- `references/layout-analysis.md` — how to analyze and map template layouts
- `references/pdfmake-patterns.md` — pdfmake-specific patterns and examples

## Key Principles

1. **Analyze before designing** — always start from a reference template or clear layout description
2. **Modular sections** — each PDF section is an independent, testable function
3. **Conditional by default** — assume columns/sections may need to be hidden based on data
4. **Data-driven, not hard-coded** — configurable content (company info, terms) comes from database, not code
5. **Preview when possible** — use browser visual companion to show field mapping before implementation
6. **Document alternatives** — always note the runner-up library for future migration
7. **Verify visually before declaring done** — automated tests miss render bugs. Always open the rendered PDF and compare against the reference template, especially with realistic data (stress cases). See Phase 6.
