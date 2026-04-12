# Reviewer Registry

Maps AI review bots to their GitHub login, comment structure, and output file name.

## Supported Reviewers

| Reviewer | GitHub Login(s) | Output File | Comment Style |
|----------|----------------|-------------|---------------|
| CodeRabbit | `coderabbitai[bot]`, `coderabbitai` | `coderabbit-review.md` | Inline + review body with `<details>` blocks |
| GitHub Copilot | `copilot-pull-request-reviewer` | `copilot-review.md` | Inline comments only |
| Gemini Code Assist | `gemini-code-assist[bot]` | `gemini-review.md` | Inline + review body summary |
| Codex | `github-codex[bot]`, `codex-reviewer[bot]` | `codex-review.md` | Inline comments only |

## Comment Structures by Reviewer

### CodeRabbit (`coderabbitai[bot]`)

Posts in **two places**:

1. **Inline review comments** — file-level, attached to diff lines (typically 2-12 per review)
2. **Review body** — contains the MAJORITY of findings:
   - "Actionable comments posted: N" header
   - `🧹 Nitpick comments` section with `<details>/<summary>` blocks per file
   - `⚠️ Outside diff range comments` section with same structure
   - Each finding: `` `LINES`: _CATEGORY_ | _SEVERITY_ `` followed by `**TITLE**`

**Severity markers**: `🔴` Critical, `🟠` Major/HIGH, `🟡` Medium, `🔵` Minor/LOW, `Refactor suggestion` = MEDIUM

**Metadata to discard**: walkthrough summaries, "Actionable comments posted" headers, paused review notices, `<!-- fingerprinting:... -->` blocks

### GitHub Copilot (`copilot-pull-request-reviewer`)

Posts **inline review comments only** — no review body summary.

- Comments are plain text with markdown formatting
- Severity is typically not explicitly marked — default to MEDIUM
- Suggestions come in ````suggestion` code blocks
- No `<details>` blocks or structured sections

### Gemini Code Assist (`gemini-code-assist[bot]`)

Posts in **two places**:

1. **Review body** — contains a summary with severity-tagged findings
2. **Inline comments** — attached to specific lines

- Severity markers: `critical`, `high`, `medium`, `low` (text-based, case-insensitive)
- Suggestions in standard markdown code blocks

### Codex (`github-codex[bot]`, `codex-reviewer[bot]`)

Posts **inline comments** — similar to Copilot style.

- Plain text with markdown
- May include code suggestions in fenced blocks
- Default severity: MEDIUM

## Detection Strategy

To detect which reviewers are present on a PR, query both comment endpoints and collect unique `user.login` values that match any known bot login from the registry above.

```bash
# Collect all unique reviewer bot logins
gh api "repos/{REPO}/pulls/{PR}/comments" --paginate \
  --jq '[.[].user.login] | unique[]'

gh api "repos/{REPO}/pulls/{PR}/reviews" --paginate \
  --jq '[.[].user.login] | unique[]'
```

Match against the registry. Only process reviewers that have at least one comment.

## Extensibility

When a new reviewer bot appears that isn't in this registry:
1. Use the generic inline-comment parser (same as Copilot)
2. Default severity to MEDIUM
3. Name the output file `{bot-login}-review.md`
4. Log a note: "Unknown reviewer {login} — using generic parser"
