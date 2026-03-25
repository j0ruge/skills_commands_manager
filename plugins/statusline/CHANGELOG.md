# Changelog — statusline

Formato: [Semantic Versioning](https://semver.org/)

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
