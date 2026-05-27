# PDF Layout Analysis Guide

## Step 1: Read the Reference Template

Use the Read tool to open the reference PDF or image. If the user provides an Excel file, read it too — Excel templates often contain formulas that reveal calculated fields.

## Step 2: Identify Sections

Scan the document top-to-bottom and identify distinct visual blocks:

| Section Type | Common Examples | Characteristics |
|-------------|----------------|-----------------|
| **Header** | Logo, document title, document number | Repeats on every page |
| **Info Block** | Supplier/Client/Salesperson details | Multi-column layout, mix of labels and values |
| **Data Table** | Line items, inventory list | Rows × columns, header row, totals row |
| **Summary** | Commercial conditions, price breakdown | Two-column: labels left, values right |
| **Notes** | Observations, disclaimers | Free-form text, may include bold formatting |
| **Terms** | Terms & conditions, legal text | Numbered paragraphs, smaller font |
| **Footer** | Page numbers, confidentiality notice | Repeats on every page |

## Step 3: Classify Fields

For each field in each section, determine its type:

### Fixed Fields
Content that never changes between documents.

- Company name, address, CNPJ
- Logo image
- Terms and conditions text
- Column headers ("Qty", "Unit Price", "Total")

**Design note:** Even "fixed" fields should be configurable (stored in database or config) to support multi-branch scenarios.

### Dynamic Fields
Content that varies per document, sourced from system data.

- Client name, contact info
- Item descriptions, quantities, prices
- Dates, quote numbers
- Salesperson info

### Calculated Fields
Derived from other fields using business logic.

- Subtotals (qty × unit price)
- Tax amounts (base × tax rate)
- Grand total (sum of subtotals + taxes)
- Discounted price (price × (1 - discount%))

**Important:** Calculations should use the system's existing calculation library, not re-implement in the PDF generator.

### Conditional Fields
Fields or columns that appear only when certain conditions are met.

- Discount column → only if any item has discount > 0
- Tax column → only if any item has tax > 0
- Shipping info → only if freight type is CIF
- Special notes → only if certain business rules trigger

## Step 4: Visual Preview (Browser Companion)

When a brainstorming visual companion is available, render an HTML mockup showing the field mapping. Use this pattern:

```html
<h2>Template Field Mapping</h2>
<p class="subtitle">
  Fields in <span style="color:#ed1c24;font-weight:bold">red</span> are dynamic (from database).
  Fixed content in default color.
</p>

<div class="mockup">
  <div class="mockup-header">Document Name — Sections Identified</div>
  <div class="mockup-body">
    <!-- Reproduce the template layout with HTML/CSS -->
    <!-- Mark dynamic fields with red color -->
    <!-- Mark conditional sections with dashed borders -->
  </div>
</div>

<!-- Summary table below the mockup -->
<div style="margin-top:24px; padding:16px; background:#1a1a2e; border-radius:8px; color:#e0e0e0;">
  <h3 style="color:#ed1c24; margin-top:0;">Fields Identified</h3>
  <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px;">
    <div>
      <div style="font-weight:bold; color:#fff;">Section Name (type)</div>
      <ul style="margin:0; padding-left:16px;">
        <li>field1 — source</li>
        <li>field2 — source</li>
      </ul>
    </div>
    <!-- More sections... -->
  </div>
</div>
```

**Color coding convention:**
- `#ed1c24` (red) — dynamic fields from database
- Default text color — fixed/hard-coded content
- Dashed borders — conditional sections that may be omitted

## Step 5: Produce Field Mapping Table

Output a structured table that becomes the specification for the PDF generator:

```markdown
| # | Section | Field | Type | Source | Condition |
|---|---------|-------|------|--------|-----------|
| 1 | Header | Logo | Fixed | filial.logo_path | — |
| 2 | Header | Document Title | Fixed | "PROPOSTA COMERCIAL" | — |
| 3 | Header | Quote Number | Dynamic | cotacao.numero | — |
| 4 | Header | Revision | Dynamic | revisao.numero | — |
| 5 | Info | Client Name | Dynamic | cotacao.cliente_razao_social | — |
| 6 | Items | Discount % | Conditional | item.desconto_percent | any item > 0 |
| 7 | Summary | Grand Total | Calculated | sum(items.total) + freight | — |
| 8 | Notes | Advance Payment | Conditional | auto-generated text | sinal > 0 |
```

This table directly informs the section builder implementation.

## Common Pitfalls

1. **Assuming fixed content stays fixed** — company info, terms, and even logos should be configurable (multi-branch support)
2. **Ignoring multi-page behavior** — always test with enough data to trigger page breaks; verify header/footer repeat
3. **Hard-coding column count** — conditional columns mean the table structure is dynamic; test all permutations
4. **Forgetting empty states** — what happens when there are no items? No observations? All terms disabled?
5. **Reference file has Excel errors** — `#REF!` or `#N/A` in Excel templates indicate broken formulas; ask the user what the intended value is
