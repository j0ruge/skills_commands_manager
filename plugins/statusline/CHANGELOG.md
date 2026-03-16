# Changelog — statusline

Formato: [Semantic Versioning](https://semver.org/)

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
