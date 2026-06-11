# Changelog — pdf-generation

## [1.5.0] — 2026-06-11

### Added

- **SKILL.md § Phase 4 "Keep a Block Together" + references/pdfmake-patterns.md**: padrão `unbreakable` para manter um bloco "título + corpo" indivisível. Envolver `[título, ...corpo]` num único nó `{ stack, unbreakable: true }` impede que o pdfmake quebre entre o título e o corpo — se não couber no espaço restante, o bloco **inteiro** desce para a próxima página (sem título órfão). Documenta a ressalva de **degradação graciosa**: um bloco mais alto que uma página volta a quebrar normalmente (sem clipping nem página em branco), então valide com um render de bloco alto / muitos itens.

### Why / Origin

Sessão de ajustes no PDF da Proposta Comercial (`sales_quote/015`): o bloco "TERMOS E CONDIÇÕES DE VENDA" partia no meio entre páginas, com o título órfão no fim da página. A skill não tinha **nenhuma** cobertura de keep-together/`unbreakable` (grep zero) — lacuna real, não duplicata. Universal para qualquer seção pdfmake que não deva ser dividida.

## [1.4.0] — 2026-05-29

### Added

- **references/pdfmake-patterns.md § "Vector Logo (SVG)" + SKILL.md § Phase 4**: logo vetorial em pdfmake.
  1. **pdfmake renderiza SVG nativamente** via o nó `{ svg, width }` (`svg` é a string XML, não data URI) — há `SVGMeasure.js` no pacote e `ContentSvg` em `@types/pdfmake`. **Não precisa de `svg-to-pdfkit`.** Documentar porque a crença "pdfmake não faz SVG" é comum e custa tempo (leva a rasterizar ou adicionar dependência à toa) — nesta sessão um agente de exploração afirmou isso com convicção e estava errado.
  2. **SVG com fills definidos por `<style>`/classe (`class="cls-1"`) renderiza SEM cor** (paths pretos/vazados), porque o svg-to-pdfkit embutido tem suporte a CSS limitado. **Fix: inline cada `class` como atributo `fill="…"`** e remover `<defs><style>`/`<title>`. Silencioso — build e testes unitários passam; só a render visual revela. Novo pitfall dedicado em `pdfmake-patterns.md`.
  3. **Embutir o vetor padrão como constante `.ts`** (`export const LOGO_SVG = '<svg…>'`), não arquivo no disco: um build `tsc → dist/` não copia arquivos não-`.ts`, e um dir de runtime gitignored (`storage/`) não existe em deploy novo — em ambos os casos o logo renderiza em branco, sem erro. Como código, sobrevive aos dois.

### Why / Origin

Sessão de troca do logo do PDF da Proposta Comercial (`sales_quote/015`) de bitmap (PNG) para vetor (`assets/jrcbrasil_logo.svg`). As três lições custaram ciclos reais: a investigação inicial concluiu (erradamente) que pdfmake 0.3.x não suportava SVG; o SVG exportado da ferramenta de design veio com fills em `<style>`/classe e renderizou preto até inlinar os `fill`; e o build `tsc`/`dist` + `storage/` gitignored obrigaram a embutir o SVG como constante para o logo padrão não sumir em deploy. Universais para qualquer logo vetorial em pdfmake server-side.

---

## v1.3.0 — 2026-05-29

### Added

- **SKILL.md § Phase 6 + § Phase 4 e references/pdfmake-patterns.md**: três lições de verificação visual aprendidas em produção:
  1. **Renderizar e inspecionar TODA página, não só a página 1.** Header/footer colocados em `content[]` (em vez dos slots `header`/`footer` do `docDefinition`) renderizam **uma vez** e somem da página 2 em diante — e isso é **invisível** num teste de 1 página. Por que documentar: o layout de 1 página fica idêntico ao correto; o bug só aparece na página 2. Novo pitfall dedicado em `pdfmake-patterns.md` (com o contraste `content[]` ❌ vs slots ✅) + Phase 6 agora exige exercitar um caso de 2+ páginas (`pdftoppm` por página).
  2. **Campo condicional/opcional: ausência ≠ bug.** Um campo opcional vazio é visualmente idêntico a um quebrado — concluir "não funciona" a partir de um caso sem dado é falso-negativo. Para validar que renderiza, **popular o dado** (fixture/store ou injeção temporária).
  3. **Cache de revisão por hash do INPUT não regenera em mudança de layout/código.** O hash é sobre o dado, não sobre o código de render; uma edição de layout deixa o hash igual e o cache serve o PDF **antigo**. Ao verificar layout, invalidar o cache (apagar revisão persistida + arquivo) antes de re-renderizar — senão inspeciona-se um render obsoleto e conclui-se que a mudança "não fez efeito".

### Why / Origin

Sessão de ajustes de layout/conteúdo no PDF da Proposta Comercial (`sales_quote/015`): rebalanceamento de cabeçalho, barra número/data em 2 colunas, novo campo de cliente. As três lições custaram ciclos reais — o header que não repetia em multipágina, campos de cliente que pareciam "não renderizar" (só faltava dado no snapshot), e o cache hash-based servindo PDF antigo após mudança de layout. Todas são universais para qualquer pipeline de geração de PDF server-side com controle de revisão.

---

## v1.2.1 — 2026-05-29

### Corrected

- **references/pdfmake-patterns.md § ligaduras fi/fl/ffi**: a causa-raiz documentada na v1.2.0 ("GSUB antigo / glyph renderizado vazio") estava **errada**. O parse direto das tabelas SFNT da fonte bundled mostrou: o `pdfmake@0.3.9` traz uma Roboto **atual** (`name[5]` = "Version 3.014; 2025") com `GSUB` `liga`/`dlig` **ativas** e os glifos de ligadura **presentes** no `cmap` (U+FB01/FB02/FB03 → 471/472/473). O bug real: a cadeia pdfkit/fontkit **aplica** a substituição `liga` mas **falha ao embutir/subsetar** o glifo no PDF. Corrigida a explicação e a ordem de cura (desabilitar `liga` primeiro; só depois bundle de TTF próprio).

### Added

- **Técnica de diagnóstico**: parsear as tabelas SFNT (`name`/`GSUB`/`cmap`) para confirmar se o glifo existe e quais features estão ativas **antes** de assumir "fonte quebrada" — glifo presente + feature ativa + caractere sumindo ⇒ problema de embedding, não da fonte.
- **Gotcha de fonte**: pacotes `@fontsource-variable/*` entregam **só `.woff2`**, que pdfmake/pdfkit (TTF/OTF-only) não consomem — "já temos Inter via fontsource" é uma armadilha. Confirmar `.ttf`/`.otf` antes de planejar troca de fonte.

### Origin

Sessão criando um agente de projeto especializado no PDF da Proposta Comercial (`sales_quote/015`). Ao escopar o bug residual de ligaduras (Jira SQ-37), o parse SFNT da Roboto bundled refutou a hipótese "fonte antiga" da v1.2.0 e revelou a causa real (embedding de glifo de ligadura). Lição universal para qualquer setup pdfmake 0.3.x server-side.

---

## v1.2.0 — 2026-05-29

### Added

- **references/pdfmake-patterns.md § Pitfalls**: três novos pitfalls comprovados em produção:
  1. **Cell padding NÃO é descontado de `widths`** — o pitfall mais grave do pacote pdfmake. Layout default adiciona `paddingLeft: 4` + `paddingRight: 4` = 8pt extras por célula, somando 64pt+ com 8 colunas e estourando A4 silenciosamente. Última coluna (geralmente "Total" em invoices) some sem erro. Fix: layout customizado com `paddingLeft/Right: 2`.
  2. **Fonte Roboto bundled tem ligaduras "fi"/"fl"/"ffi" quebradas** — palavras como "fiscal"→"fscal", "fixture"→"fxture", "confirmação"→"confrmação" perdem o "f". Bug do GSUB antigo da Roboto bundled em pdfmake 0.3.x interagindo com fontkit interno do pdfkit. Fix: bundle TTF moderno ou trocar para Inter/Open Sans.
  3. **`pdfmake.addFonts()` rejeita AFM silenciosamente** — tentar registrar Helvetica AFM (que pdfkit bundla) parece funcionar mas estoura erro 500 genérico no `getBuffer()`. AFM tem só métricas, não glifos. Conclusão: pdfmake requer TTF/OTF.

- **SKILL.md § Phase 6 Visual Verification (NON-NEGOTIABLE)**: nova fase explícita no workflow. Bugs de render só aparecem visualmente — automação não pega overflow de coluna, glifos quebrados, paginação ruim. Inclui checklist de risk-areas (last column cut, value truncation, header repeat, font glyphs, conditional columns).

- **SKILL.md § Key Principles #7**: princípio "Verify visually before declaring done" elevado ao topo das diretrizes.

### Origin

Lições aprendidas durante a verificação visual T056 da feature `sales_quote/015-pdf-proposta-comercial`. Após 57 tasks com **todos os testes automatizados passando**, a inspeção manual de PDFs reais com dados de produção revelou:

1. Tabela de uma cotação de 11 itens com totais de R$300k+ teve a coluna "Total" cortada na borda direita (R$49.12 em vez de R$49.126,35). Causa: padding pitfall.
2. Palavras como "fiscal" renderizadas como "fscal" no PDF gerado. Causa: ligaduras Roboto.
3. Tentativa de fix substituindo Roboto por Helvetica AFM gerou erro 500 silencioso — perdemos ~20min até identificar que pdfmake não aceita AFM.

Todas as três lições são **universais** para qualquer setup pdfmake server-side, não específicas do projeto.

---

## v1.1.0 — 2026-05-27

### Added

- **references/pdfmake-patterns.md § Pitfalls**: nova seção documentando dois gotchas reais de produção:
  1. **`pdfmake/interfaces` não resolve em `moduleResolution: "NodeNext"`** — `@types/pdfmake` declara os tipos, mas o `package.json` do pdfmake não exporta o subpath. Fix: shim local `pdfmake-types.ts`.
  2. **Font path quebra em monorepos** — `require.resolve("pdfmake/package.json")` + `path.dirname()` é a forma robusta; paths relativos (`node_modules/pdfmake/...`) falham com hoisting.

### Origin

Ambos os pitfalls custaram tempo de debug durante a implementação real do PDF da Proposta Comercial no projeto `sales_quote` (feature 015). São universais para qualquer setup pdfmake + TypeScript NodeNext em monorepo.

---

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
