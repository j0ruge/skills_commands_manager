---
name: pdf-generation
metadata:
  version: 1.0.0
description: "PDF generation design toolkit — analyzes reference templates (PDF/Excel), maps dynamic vs fixed fields with browser preview, recommends libraries (pdfmake, pdf-lib, PDFKit, Puppeteer, @react-pdf) with trade-offs, designs modular section architecture with conditional columns, auto-generated observations, bold markup, and revision control. Triggers — PDF generation, generate PDF, PDF template, PDF layout, pdfmake, commercial proposal PDF, invoice PDF, report PDF."
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding.

## Purpose

Guide the design and implementation of programmatic PDF generation from structured data. This skill covers the full lifecycle: analyzing reference templates, recommending libraries, designing modular layouts, and producing implementation-ready specifications.

**This skill is NOT for:**
- Acrobat JavaScript / AcroForms (use `pdf-intelligent-forms` skill)
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

#### Header/Footer on All Pages

Use callback functions for dynamic content:

```typescript
footer: (currentPage, pageCount) => ({
  text: `PAGE ${currentPage} OF ${pageCount}`,
  alignment: 'right',
  margin: [40, 10]
})
```

### Phase 5: Generate Implementation Spec

Produce a complete specification covering:
- Data model (new entities for revision tracking, configurable content)
- API contracts (endpoints for PDF generation, admin CRUD)
- Section-by-section layout description
- Conditional logic rules
- Test scenarios (column combinations, multi-page pagination, revision idempotency)

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
