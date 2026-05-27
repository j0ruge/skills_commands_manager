# PDF Generation Libraries — Comparison Guide

## Decision Matrix

| Criterion | pdf-lib | PDFKit | Puppeteer/Playwright | @react-pdf/renderer | **pdfmake** |
|-----------|---------|--------|----------------------|---------------------|-------------|
| Table layout | Manual XY coordinates | Manual + community plugin | CSS native (grid, flexbox) | Flexbox-based Views | **Native, first-class** |
| Page numbers | Manual calculation | Manual via events | CSS @page rules | Component-based | **Built-in callback** |
| Header/footer repeat | Manual per-page | Event-based | CSS @page fixed | Component per-page | **Built-in callback** |
| Text wrapping | None (manual) | Built-in | CSS native | Flexbox | **Automatic** |
| Auto pagination | None | Built-in | CSS page-break | Built-in | **Built-in with headerRows** |
| TypeScript | Good (@types) | @types/pdfkit | Good | Good (native) | **@types/pdfmake** |
| Bundle size (server) | ~200 KB | ~1 MB | **~400 MB** (Chromium) | ~2 MB | ~1.5 MB |
| Generation speed | Fast (~100ms) | Fast (~200ms) | **Slow (2-5s)** | ~500ms | **~300ms** |
| npm weekly downloads | ~1.5M | ~800K | ~3M | ~860K | **~1.76M** |
| Learning curve | High (coordinate math) | Medium | Low (if know CSS) | Medium (JSX) | **Low (declarative JSON)** |
| Custom fonts | Yes (embed TTF/OTF) | Yes (register path) | CSS @font-face | Yes (register) | **Yes (VFS or path)** |
| Images | Yes (embed) | Yes (file/buffer) | HTML img/CSS | Yes (source prop) | **Yes (data URI or path)** |

## When to Use Each

### pdfmake — Structured Documents (RECOMMENDED DEFAULT)

**Best for:** Invoices, proposals, reports, certificates, receipts — any document with tables, headers, and structured data.

**Why:** Declarative JSON API maps directly to document structure. Tables are first-class with automatic column width distribution, header row repetition across pages, and cell-level styling. Header/footer callbacks receive `currentPage` and `pageCount` for free.

```typescript
const docDefinition = {
  header: (currentPage, pageCount) => ({ text: `Page ${currentPage}/${pageCount}` }),
  content: [
    { text: 'INVOICE', style: 'header' },
    {
      table: {
        headerRows: 1,
        widths: ['auto', '*', 60, 80],
        body: [
          ['Code', 'Description', 'Qty', 'Total'],
          ...items.map(i => [i.code, i.desc, i.qty, formatCurrency(i.total)])
        ]
      }
    }
  ],
  styles: { header: { fontSize: 18, bold: true } }
};
```

### Puppeteer/Playwright — Pixel-Perfect Visual Documents

**Best for:** Marketing brochures, branded certificates, design-heavy documents where CSS control is essential. Also ideal when a designer provides HTML/CSS mockups.

**Why:** Full CSS support (grid, flexbox, custom fonts, gradients). Maximum visual fidelity. Works with Claude Design output directly.

**Trade-offs:** ~400MB Chromium dependency, 2-5s generation time, complex Docker deployment, larger output files (~1.7MB vs ~200KB).

**Use when:** Visual design is more important than generation speed, or when migrating from an HTML template.

### pdf-lib — PDF Manipulation & Form Filling

**Best for:** Filling existing PDF forms, merging/splitting PDFs, adding watermarks, stamping signatures. NOT recommended for creating documents from scratch.

**Why:** Excellent at modifying existing PDFs. Pure JavaScript, no external dependencies.

**Trade-offs:** No tables, no text wrapping, no automatic pagination. Every element requires manual X/Y coordinate calculation.

### PDFKit — Streaming Generation with Fine Control

**Best for:** Documents needing streaming output (large files) or precise positioning control with some text wrapping support.

**Trade-offs:** No built-in table component — requires community plugin `pdfkit-table` (low maintenance).

### @react-pdf/renderer — React Ecosystem Integration

**Best for:** Teams already using React who want JSX-based document definitions. Good for documents generated in the browser.

**Trade-offs:** Flexbox layout model doesn't support all CSS (no grid, no float). Tables require manual View+Text nesting.

## Decision Flowchart

```text
Need to modify existing PDF? → pdf-lib
Need pixel-perfect CSS design? → Puppeteer/Playwright
Need tables with pagination? → pdfmake
Using React, generating in browser? → @react-pdf/renderer
Need streaming for large files? → PDFKit
```
