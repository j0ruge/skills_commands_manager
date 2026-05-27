# Changelog — pdf-generation

## v1.0.0 — 2026-05-27

### Added

- **SKILL.md**: PDF generation design toolkit with 5-phase workflow (analyze template → recommend library → design sections → handle patterns → generate spec)
- **references/library-comparison.md**: Comparison of 5 PDF libraries (pdfmake, pdf-lib, PDFKit, Puppeteer/Playwright, @react-pdf/renderer) with decision matrix, trade-offs, and flowchart
- **references/layout-analysis.md**: Step-by-step guide for analyzing reference PDFs, classifying fields (fixed/dynamic/calculated/conditional), and rendering browser previews with color-coded field mapping
- **references/pdfmake-patterns.md**: Production-ready patterns for conditional columns, multi-column info blocks, bold markup parser, observation engine, hash-based revision control, dynamic headers/footers, and custom table layouts

### Origin

Born from a real session designing a commercial proposal PDF (Proposta Comercial) for JRC Brasil's sales quote system. Key lessons encoded:

- **Conditional columns** — scan all rows before building the table; omit columns where no row has a non-zero value (e.g., hide discount column from clients who don't get discounts)
- **Visual preview** — showing the field mapping in a browser companion (HTML mockup with red for dynamic fields) dramatically accelerated design decisions
- **Library selection** — pdfmake wins for structured documents with tables; Puppeteer wins for pixel-perfect CSS-designed documents; document the runner-up for future migration
- **Configurable "fixed" content** — even company info and terms should come from database (multi-branch support), not hard-coded
- **Bold markup** — simple `**text**` markers stored in database, parsed to formatted segments at render time
- **Revision control** — SHA-256 hash of input data for idempotent generation; same data = same PDF, no wasted revisions
