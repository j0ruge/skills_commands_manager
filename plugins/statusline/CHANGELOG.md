# Changelog — statusline

Formato: [Semantic Versioning](https://semver.org/)

## [1.5.1] - 2026-06-27

### Fixed

- **Section 5 (Session cost) — locale-safe formatting**: cost rendered as `$0,00` (and `printf` errored with "invalid number") on machines whose locale uses a comma as the decimal separator. Observed live on a pt-BR Linux machine: `printf "%.2f" "0.37"` rejects the dot because the locale expects `0,37`. The Bash block now wraps `printf` with `LC_NUMERIC=C` to force a dot separator.
- **PowerShell parity** for the same root cause: `"{0:N2}" -f [double]$cost` formats in the current culture and would render a comma (e.g. `$0,37`) on pt-BR/de-DE Windows. Replaced with `([double]$cost).ToString("F2", [System.Globalization.CultureInfo]::InvariantCulture)`.
- Updated the IMPORTANT note and added a troubleshooting row documenting that this is **not Windows-only** — it affects any comma-decimal locale on Linux/macOS too.

## [1.5.0] - 2026-06-09

### Added

- **Section 10 — 5h usage window** (`rate_limits.five_hour.used_percentage`): shows how much of the 5-hour rolling usage limit is spent, with green/yellow/red thresholds (⏳)
- **Section 11 — Weekly usage** (`rate_limits.seven_day.used_percentage`): shows the 7-day usage limit consumption (📅)
- **Section 12 — PR state** (`pr.number` + `pr.review_state`): shows the current branch's PR number with an icon/color per review state — approved ✅ green, changes_requested ✋ red, commented 💬 yellow, other 🔀 cyan
- **New recommended default** — the wizard now suggests sections `1-5, 10, 11, 12` (was `1-5`), surfacing usage limits and PR state out of the box

### Implementation notes

- **Graceful degradation is mandatory and built in**: `rate_limits.*` is only present for Claude.ai Pro/Max subscribers and only after the first API response; `pr.*` only when the branch has an open PR. The Bash parser emits an empty string for absent fields and each block guards on presence (`[ -n "$var" ]` / `$null -ne`), so missing data yields a silently omitted section — never `0%` or an empty slot. This is what makes the new sections safe defaults.
- **Field-name gotcha documented**: the weekly window is `rate_limits.seven_day` (NOT `weekly`); the 5h window is `rate_limits.five_hour`
- PowerShell: added emoji variables for the new sections via `[char]::ConvertFromUtf32()` (consistent with the existing no-inline-emoji rule)
- Step 9 test JSON now includes `rate_limits` and `pr` so the preview exercises sections 10-12; added guidance to re-run without them to confirm graceful omission

## [1.4.0] - 2026-04-18

### Added

- **Effort level badge on Section 1 (Model name)** — status line now reads `effortLevel` from `~/.claude/settings.json` and appends it to the model display (e.g., `🤖 Opus 4.7 [high]`)
- Value is read on every invocation, so changing `effortLevel` takes effect immediately without regenerating the script
- Opt-in behavior: when `effortLevel` is absent, nothing is appended (no visual change for users who don't use it)

### Implementation notes

- Bash: uses the existing `grep -o` + `sed` pattern (no jq / no python dependency added — reuses what's already in the header)
- PowerShell: wrapped in `try/catch` with `Test-Path` guard so a missing or malformed `settings.json` never breaks the status line

## [1.3.0] - 2026-03-25

### Breaking Change

- **Removed `jq` dependency** — Bash template now uses Python (`json` module) for all JSON parsing
- `jq` is no longer a prerequisite; Python 3.x is the only runtime dependency for Bash scripts
- All JSON fields are extracted in a single Python call in the script header, then used as shell variables

### Fixed (Windows / Git Bash)

- Path normalization: convert `C:\...` to `/c/...` so `git -C` and `basename` work in Git Bash
- `realpath --relative-to` fallback: chain through `python3` → `python` → `realpath` → `basename`
- Auto-detect Windows OS and use ASCII-safe progress bar characters (`#`/`-` instead of `█`/`░`)
- Context percentage: robust integer parsing via Python `math.floor()` (fixes `--% ` display)
- Cost formatting: apply `printf "%.2f"` to avoid raw float display (e.g., `$0.05226375` → `$0.05`)

### Changed

- Use `.workspace.current_dir` as primary JSON field (fallback to `.workspace.project_dir` and `.cwd`)
- All Bash git commands now use the normalized `$cwd` variable from the header
- Project folder section computes relative path within the git repo instead of just `basename`
- Added troubleshooting entries for jq-missing, path normalization, and realpath issues

## [1.1.0] - 2026-03-16

### Corrigido (Windows)

- Emojis agora renderizam corretamente — encoding UTF-8 forcado no header do script
- Emojis nao quebram mais o parsing do PowerShell — movidos para variaveis via `[char]::ConvertFromUtf32()`
- Barra de progresso usa `#`/`-` em vez de `█`/`░` (incompativeis com fontes Windows)
- Custo formatado com 2 casas decimais (era float completo, ex: `$0.55226375`)
- settings.json usa `"type": "command"` em vez de `"enabled": true` (corrige erro de validacao)
- Comando inclui `-ExecutionPolicy Bypass` para evitar bloqueio de scripts
- JSON de teste usa `/` em paths (backslash `\` causava erro no `ConvertFrom-Json`)
- Adicionada tabela de troubleshooting no final da skill

## [1.0.0] - 2026-03-16

### Adicionado

- Command `/statusline:setup` — wizard interativo para configurar status line do Claude Code
- Suporte cross-platform: Bash (.sh) para Linux/macOS, PowerShell (.ps1) para Windows
- 9 secoes composiveis: model, context bar, git branch, folder, cost, duration, lines, tokens, vim
- Preferencias visuais: emojis, esquema de cores, largura da barra, separador
- Backup automatico de script existente
- Configuracao automatica do settings.json
- Preview com JSON de exemplo
