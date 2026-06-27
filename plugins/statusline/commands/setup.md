---
description: Interactive wizard to configure Claude Code status line — model, context bar, git branch/PR, cost, and 5h/weekly usage limits. Cross-platform (Bash + PowerShell). Triggers — statusline, status bar, footer, rate limit, usage window, PR state.
metadata:
  version: 1.5.1
---

## Status Line Setup

Interactive wizard to configure the Claude Code status line with composable sections.
Automatically detects the OS and generates the appropriate script (`.sh` for Linux/macOS, `.ps1` for Windows).

### Step 1 — Detect OS

Identify the user's platform:

```bash
uname -s 2>/dev/null || echo "Windows"
```

- **Linux / Darwin (macOS):** generate `~/.claude/claude-status.sh` (Bash)
- **Windows / MINGW / MSYS:** generate `~/.claude/claude-status.ps1` (PowerShell)

Store the detected platform for use in the following steps.

### Step 2 — Prerequisites

Check dependencies according to the OS:

**Linux/macOS (Bash):**

```bash
# Check if Python 3 is available (used for JSON parsing — no jq dependency)
which python3 || which python || echo "ERROR: Python not found. Install Python 3.x"

# Check if ~/.claude/ exists
ls -d ~/.claude/ || echo "ERROR: directory ~/.claude/ not found"
```

**Windows (Bash / Git Bash):**

```bash
# Python is the only dependency — jq is NOT required
which python || which python3 || echo "ERROR: Python not found"
ls -d ~/.claude/ || echo "ERROR: directory ~/.claude/ not found"
```

**Windows (PowerShell):**

```powershell
# PowerShell 5.1+ is native on Windows 10+ (ConvertFrom-Json available — no jq needed)
$PSVersionTable.PSVersion

# Check if ~/.claude/ exists
Test-Path "$env:USERPROFILE\.claude"
```

If any prerequisite fails, abort and inform the user how to resolve it.

> **Design note:** The Bash template uses Python (`json` module) for JSON parsing instead of `jq`.
> This is intentional — `jq` is rarely pre-installed on Windows/Git Bash, while Python is almost
> always available on developer machines. This eliminates the most common setup failure.

### Step 3 — Section selection

Present the table of available sections and ask the user which ones to activate.
**By default, suggest the recommended set: sections 1-5, 10, 11, 12** (model, context bar, git branch, folder, cost, 5h usage window, weekly usage, PR state). Sections 10-12 add the most actionable runtime signals — how much of the rolling usage limits is spent and the review state of the current branch's PR — and degrade gracefully when their data is absent (see notes below), so they are safe to enable by default.

| # | Section | JSON Fields | Emoji | Default Color |
|---|---------|------------|-------|---------------|
| 1 | Model name (+ optional effort level) | `model.display_name` + `~/.claude/settings.json#effortLevel` | 🤖 | Magenta |
| 2 | Context bar | `context_window.used_percentage`, `.context_window_size` | 📊 | Dynamic (green < 50%, yellow < 80%, red >= 80%) |
| 3 | Git branch | `workspace.project_dir` + `git rev-parse` | 🌿 | Green |
| 4 | Project folder | `workspace.project_dir` (basename) | 📁 | Blue |
| 5 | Session cost | `cost.total_cost_usd` | 💰 | Yellow |
| 6 | Session duration | `cost.total_duration_ms` | ⏱️ | Cyan |
| 7 | Lines changed | `cost.total_lines_added`, `.total_lines_removed` | 📝 | Green/Red |
| 8 | Token counts | `context_window.total_input_tokens`, `.total_output_tokens` | 🔢 | White |
| 9 | Vim mode | `vim.mode` | ⌨️ | Cyan |
| 10 | 5h usage window | `rate_limits.five_hour.used_percentage` | ⏳ | Dynamic (green < 50%, yellow < 80%, red >= 80%) |
| 11 | Weekly usage | `rate_limits.seven_day.used_percentage` | 📅 | Dynamic (green < 50%, yellow < 80%, red >= 80%) |
| 12 | PR state | `pr.number`, `pr.review_state` | 🔀/✅/✋/💬 | Dynamic (by review state) |

> **Note (sections 10-12 are conditional):** `rate_limits.*` is only present for Claude.ai **Pro/Max** subscribers and only after the first API response of the session; `pr.*` is only present when the current branch has an associated PR. The Bash/PowerShell blocks for these sections render **only when the field exists** — when absent, the section is silently omitted, never showing `0%` or an empty slot. This is why they are safe defaults: users without the data simply don't see them.
>
> **Field naming gotcha:** the weekly window is `rate_limits.seven_day` (NOT `weekly`). The 5-hour window is `rate_limits.five_hour`.

Ask: "Which sections do you want to activate? (e.g.: 1,2,3,4,5,10,11,12 or 'all' for all)"

### Step 4 — Visual preferences

Ask the user about customization:

1. **Emoji style:** Keep the default emojis from the table or disable them?
2. **Color scheme:** Use default ANSI colors or no colors (plain text)?
3. **Context bar width:** Number of characters for the progress bar (default: 20)
4. **Section separator:** Separator character (default: ` | `)

If the user wants to keep the defaults, proceed without further questions.

### Step 5 — Backup

Check if a status line script already exists:

**Linux/macOS:**
```bash
ls ~/.claude/claude-status.sh 2>/dev/null
```

**Windows:**
```powershell
Test-Path "$env:USERPROFILE\.claude\claude-status.ps1"
```

If it exists, ask the user whether to back it up before overwriting.
If yes, copy with a timestamp:

```bash
# Linux/macOS
cp ~/.claude/claude-status.sh ~/.claude/claude-status.sh.bak.$(date +%Y%m%d%H%M%S)
```

```powershell
# Windows
Copy-Item "$env:USERPROFILE\.claude\claude-status.ps1" "$env:USERPROFILE\.claude\claude-status.ps1.bak.$(Get-Date -Format 'yyyyMMddHHmmss')"
```

### Step 6 — Generate script

Build the script by composing only the blocks for the sections chosen by the user.

#### Script header

**Bash (`claude-status.sh`):**

```bash
#!/bin/bash
# Claude Code Status Line Script
# Generated by /statusline:setup on {GENERATION_DATE}
# Uses Python for JSON parsing (no jq dependency)

input=$(cat)

# --- Parse all JSON fields with Python in a single call ---
# This eliminates the jq dependency which is rarely available on Windows/Git Bash.
# Python extracts every field, normalizes Windows paths, and exports shell variables.
PYTHON_CMD=$(command -v python3 || command -v python)
eval "$($PYTHON_CMD -c "
import json, sys, math
d = json.loads(sys.stdin.read())
cw = d.get('context_window', {})
ws = d.get('workspace', {})
co = d.get('cost', {})
md = d.get('model', {})
cu = cw.get('current_usage', {})
vm = d.get('vim', {})
rl = d.get('rate_limits', {}) or {}
fh = rl.get('five_hour', {}) or {}
sd = rl.get('seven_day', {}) or {}
pr = d.get('pr', {}) or {}

cwd = ws.get('current_dir') or ws.get('project_dir') or d.get('cwd', '.')
# Normalize Windows path for Git Bash: C:\... → /c/...
cwd = cwd.replace('\\\\', '/')
if len(cwd) >= 3 and cwd[1] == ':' and cwd[2] == '/':
    cwd = '/' + cwd[0].lower() + cwd[2:]

print(f'cwd=\"{cwd}\"')
print(f'model_name=\"{md.get(\"display_name\", \"Unknown\")}\"')
print(f'pct={math.floor(cw.get(\"used_percentage\", 0) or 0)}')
print(f'ctx_size={cw.get(\"context_window_size\", 200000) or 200000}')
print(f'cost_raw={co.get(\"total_cost_usd\", 0) or 0}')
print(f'duration_ms={co.get(\"total_duration_ms\", 0) or 0}')
print(f'lines_added={co.get(\"total_lines_added\", 0) or 0}')
print(f'lines_removed={co.get(\"total_lines_removed\", 0) or 0}')
print(f'input_tokens={cw.get(\"total_input_tokens\", 0) or 0}')
print(f'output_tokens={cw.get(\"total_output_tokens\", 0) or 0}')
print(f'vim_mode=\"{vm.get(\"mode\", \"\")}\"')

# Rate limits (Pro/Max only, present after first API response) — empty string when absent
fh_pct = fh.get('used_percentage')
sd_pct = sd.get('used_percentage')
print(f'fh_pct={\"\" if fh_pct is None else math.floor(fh_pct)}')
print(f'sd_pct={\"\" if sd_pct is None else math.floor(sd_pct)}')

# PR state (present only when the branch has an associated PR) — empty when absent
pr_num = pr.get('number')
print(f'pr_num={\"\" if pr_num is None else int(pr_num)}')
print(f'pr_state=\"{pr.get(\"review_state\", \"\") or \"\"}\"')
" <<< "$input")"

# Detect Windows and use ASCII-safe progress bar characters
# Unicode block characters (█░) don't render correctly in most Windows terminal fonts.
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || -n "$WINDIR" ]]; then
  BAR_FILLED="#"
  BAR_EMPTY="-"
else
  BAR_FILLED="█"
  BAR_EMPTY="░"
fi

# ANSI color codes
RST='\033[0m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[0;37m'
```

**PowerShell (`claude-status.ps1`):**

```powershell
# Claude Code Status Line Script
# Generated by /statusline:setup on {GENERATION_DATE}

# Force UTF-8 output so emojis render correctly in Windows Terminal
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$input = $Input | Out-String
$json = $input | ConvertFrom-Json

# ANSI color codes (PowerShell 5.1 compatible)
$ESC = [char]27
$RST = "$ESC[0m"
$GREEN = "$ESC[0;32m"
$YELLOW = "$ESC[0;33m"
$RED = "$ESC[0;31m"
$BLUE = "$ESC[0;34m"
$MAGENTA = "$ESC[0;35m"
$CYAN = "$ESC[0;36m"
$WHITE = "$ESC[0;37m"

# Emojis as variables — inline emojis break PowerShell parsing
# Include only the emoji variables needed for the selected sections
$eRobot = [char]::ConvertFromUtf32(0x1F916)    # Section 1 - Model
$eChart = [char]::ConvertFromUtf32(0x1F4CA)    # Section 2 - Context bar
$eLeaf = [char]::ConvertFromUtf32(0x1F33F)     # Section 3 - Git branch
$eFolder = [char]::ConvertFromUtf32(0x1F4C1)   # Section 4 - Project folder
$eMoney = [char]::ConvertFromUtf32(0x1F4B0)    # Section 5 - Cost
$eTimer = [char]::ConvertFromUtf32(0x23F1)     # Section 6 - Duration
$ePen = [char]::ConvertFromUtf32(0x1F4DD)      # Section 7 - Lines changed
$eNumbers = [char]::ConvertFromUtf32(0x1F522)  # Section 8 - Token counts
$eKeyboard = [char]::ConvertFromUtf32(0x2328)  # Section 9 - Vim mode
$eHourglass = [char]::ConvertFromUtf32(0x23F3) # Section 10 - 5h usage window
$eCalendar = [char]::ConvertFromUtf32(0x1F4C5) # Section 11 - Weekly usage
$ePr = [char]::ConvertFromUtf32(0x1F500)       # Section 12 - PR (default icon)
$ePrOk = [char]::ConvertFromUtf32(0x2705)      # Section 12 - PR approved
$ePrBlock = [char]::ConvertFromUtf32(0x270B)   # Section 12 - PR changes_requested
$ePrComment = [char]::ConvertFromUtf32(0x1F4AC)# Section 12 - PR commented
```

> **IMPORTANT (Windows):** Never place emoji characters directly inside PowerShell strings.
> PowerShell 5.1 cannot parse inline emoji — it breaks on surrogate pairs.
> Always use `[char]::ConvertFromUtf32(0x...)` stored in variables, then interpolate the variable.

#### Composable blocks per section

Include only the blocks for the sections selected in step 3.

**Section 1 — Model name (with optional effort level):**

The model display name is augmented with the `effortLevel` value from `~/.claude/settings.json` when set (e.g., `Opus 4.7 [high]`). This is the same file Claude Code uses for per-user configuration, so the status line stays in sync with whatever effort level is active. When the field is absent, nothing is appended — no visual change for users who don't use it.

Bash:
```bash
# $model_name is set by the Python JSON parser in the header.
# Optionally append effortLevel from ~/.claude/settings.json (e.g., " [high]").
effort=$(grep -o '"effortLevel"[[:space:]]*:[[:space:]]*"[^"]*"' ~/.claude/settings.json 2>/dev/null \
  | head -1 | sed 's/^"effortLevel"[[:space:]]*:[[:space:]]*"//;s/"$//')
if [ -n "$effort" ]; then
  model_name="${model_name} [${effort}]"
fi
parts+=("🤖 ${MAGENTA}${model_name}${RST}")
```

PowerShell:
```powershell
$model = if ($json.model.display_name) { $json.model.display_name } else { "Unknown" }

# Optionally append effortLevel from ~/.claude/settings.json (e.g., " [high]").
$effort = ""
try {
  $settingsPath = Join-Path $env:USERPROFILE ".claude\settings.json"
  if (Test-Path $settingsPath) {
    $settings = Get-Content $settingsPath -Raw | ConvertFrom-Json
    if ($settings.effortLevel) { $effort = " [$($settings.effortLevel)]" }
  }
} catch {}

$parts += "$eRobot $MAGENTA$model$effort$RST"
```

> **Note:** `effortLevel` is an opt-in field in `~/.claude/settings.json`. The script reads it on every invocation, so toggling the value takes effect immediately without regenerating the script.

**Section 2 — Context bar:**

Bash:
```bash
# $pct and $ctx_size are set by the Python JSON parser in the header
total_k=$((ctx_size / 1000))

if [ "$pct" -lt 50 ]; then BAR_COLOR="$GREEN"
elif [ "$pct" -lt 80 ]; then BAR_COLOR="$YELLOW"
else BAR_COLOR="$RED"; fi

filled=$((pct * {BAR_WIDTH} / 100))
empty=$(({BAR_WIDTH} - filled))
bar=""
for ((i = 0; i < filled; i++)); do bar+="$BAR_FILLED"; done
for ((i = 0; i < empty; i++)); do bar+="$BAR_EMPTY"; done

parts+=("📊 ${BAR_COLOR}${pct}%${RST} of ${total_k}k [${BAR_COLOR}${bar}${RST}]")
```

PowerShell:
```powershell
$pct = [math]::Floor($json.context_window.used_percentage)
if (-not $pct) { $pct = 0 }
$total = if ($json.context_window.context_window_size) { $json.context_window.context_window_size } else { 200000 }
$totalK = [math]::Floor($total / 1000)

if ($pct -lt 50) { $barColor = $GREEN }
elseif ($pct -lt 80) { $barColor = $YELLOW }
else { $barColor = $RED }

$filled = [math]::Floor($pct * {BAR_WIDTH} / 100)
$empty = {BAR_WIDTH} - $filled
$bar = ("#" * $filled) + ("-" * $empty)

$parts += "$eChart $barColor$pct%$RST of ${totalK}k [$barColor$bar$RST]"
```

> **IMPORTANT (Windows):** Use `#` and `-` for the progress bar instead of `█` and `░`.
> The Unicode block characters do not render correctly in most Windows terminal fonts.

**Section 3 — Git branch:**

Bash:
```bash
# Uses $cwd from the header (already normalized for Windows)
branch=$(git -C "$cwd" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "n/a")
parts+=("🌿 ${GREEN}${branch}${RST}")
```

PowerShell:
```powershell
$projectDir = if ($json.workspace.project_dir) { $json.workspace.project_dir } elseif ($json.cwd) { $json.cwd } else { "." }
$branch = try { git -C $projectDir rev-parse --abbrev-ref HEAD 2>$null } catch { "n/a" }
if (-not $branch) { $branch = "n/a" }
$parts += "$eLeaf $GREEN$branch$RST"
```

**Section 4 — Project folder:**

Bash:
```bash
# Uses $cwd from the header (already normalized for Windows)
# realpath --relative-to is unavailable on Git Bash; fallback through python → realpath → basename
if git_root=$(git -C "$cwd" rev-parse --show-toplevel 2>/dev/null); then
  folder=$(python3 -c "import os,sys; print(os.path.relpath(sys.argv[1],sys.argv[2]))" "$cwd" "$git_root" 2>/dev/null \
    || python -c "import os,sys; print(os.path.relpath(sys.argv[1],sys.argv[2]))" "$cwd" "$git_root" 2>/dev/null \
    || realpath --relative-to="$git_root" "$cwd" 2>/dev/null \
    || basename "$cwd")
  [ "$folder" = "." ] && folder=$(basename "$git_root")
else
  folder=$(basename "$cwd")
fi
parts+=("📁 ${BLUE}${folder}${RST}")
```

PowerShell:
```powershell
$projectDir = if ($json.workspace.project_dir) { $json.workspace.project_dir } elseif ($json.cwd) { $json.cwd } else { "." }
$folder = Split-Path $projectDir -Leaf
$parts += "$eFolder $BLUE$folder$RST"
```

**Section 5 — Session cost:**

Bash:
```bash
# $cost_raw is set by the Python JSON parser in the header.
# LC_NUMERIC=C forces a dot decimal separator — without it, printf errors
# ("invalid number") and renders $0,00 on comma-decimal locales (pt-BR, de-DE, fr-FR, ...).
cost=$(LC_NUMERIC=C printf "%.2f" "$cost_raw")
parts+=("💰 ${YELLOW}\$${cost}${RST}")
```

PowerShell:
```powershell
$cost = if ($json.cost.total_cost_usd) { $json.cost.total_cost_usd } else { 0 }
# InvariantCulture forces a dot decimal separator — "{0:N2}" -f formats in the
# current culture and would render a comma (e.g. 0,37) on pt-BR/de-DE Windows.
$costFormatted = ([double]$cost).ToString("F2", [System.Globalization.CultureInfo]::InvariantCulture)
$parts += "$eMoney $YELLOW`$$costFormatted$RST"
```

> **IMPORTANT (locale safety):** Cost formatting must be locale/culture-independent.
> On Bash, wrap `printf "%.2f"` with `LC_NUMERIC=C` — otherwise it errors with "invalid number"
> and renders `$0,00` on comma-decimal locales (pt-BR, de-DE, fr-FR, ...).
> On PowerShell, use `([double]$cost).ToString("F2", [CultureInfo]::InvariantCulture)` — `"{0:N2}" -f`
> formats in the current culture and would render a comma (e.g. `$0,37`).
> Both also fix the raw-float-too-many-decimals case (e.g. `$0.55226375` → `$0.55`).

**Section 6 — Session duration:**

Bash:
```bash
# $duration_ms is set by the Python JSON parser in the header
duration_min=$((duration_ms / 60000))
duration_sec=$(( (duration_ms % 60000) / 1000 ))
parts+=("⏱️ ${CYAN}${duration_min}m${duration_sec}s${RST}")
```

PowerShell:
```powershell
$durationMs = if ($json.cost.total_duration_ms) { $json.cost.total_duration_ms } else { 0 }
$durationMin = [math]::Floor($durationMs / 60000)
$durationSec = [math]::Floor(($durationMs % 60000) / 1000)
$parts += "$eTimer $CYAN${durationMin}m${durationSec}s$RST"
```

**Section 7 — Lines changed:**

Bash:
```bash
# $lines_added and $lines_removed are set by the Python JSON parser in the header
parts+=("📝 ${GREEN}+${lines_added}${RST}/${RED}-${lines_removed}${RST}")
```

PowerShell:
```powershell
$added = if ($json.cost.total_lines_added) { $json.cost.total_lines_added } else { 0 }
$removed = if ($json.cost.total_lines_removed) { $json.cost.total_lines_removed } else { 0 }
$parts += "$ePen $GREEN+$added$RST/$RED-$removed$RST"
```

**Section 8 — Token counts:**

Bash:
```bash
# $input_tokens and $output_tokens are set by the Python JSON parser in the header
input_k=$((input_tokens / 1000))
output_k=$((output_tokens / 1000))
parts+=("🔢 ${WHITE}${input_k}k in / ${output_k}k out${RST}")
```

PowerShell:
```powershell
$inputTokens = if ($json.context_window.total_input_tokens) { $json.context_window.total_input_tokens } else { 0 }
$outputTokens = if ($json.context_window.total_output_tokens) { $json.context_window.total_output_tokens } else { 0 }
$inputK = [math]::Floor($inputTokens / 1000)
$outputK = [math]::Floor($outputTokens / 1000)
$parts += "$eNumbers $WHITE${inputK}k in / ${outputK}k out$RST"
```

**Section 9 — Vim mode:**

Bash:
```bash
# $vim_mode is set by the Python JSON parser in the header
if [ -n "$vim_mode" ]; then
  parts+=("⌨️ ${CYAN}${vim_mode}${RST}")
fi
```

PowerShell:
```powershell
if ($json.vim -and $json.vim.mode) {
  $parts += "$eKeyboard $CYAN$($json.vim.mode)$RST"
}
```

**Section 10 — 5h usage window (rate limit):**

Renders only when `rate_limits.five_hour.used_percentage` is present (Pro/Max, after the first API response). Color uses the same green/yellow/red thresholds as the context bar.

Bash:
```bash
# $fh_pct is set by the Python JSON parser ("" when the field is absent)
if [ -n "$fh_pct" ]; then
  if [ "$fh_pct" -lt 50 ]; then FH_COLOR="$GREEN"
  elif [ "$fh_pct" -lt 80 ]; then FH_COLOR="$YELLOW"
  else FH_COLOR="$RED"; fi
  parts+=("⏳ 5h ${FH_COLOR}${fh_pct}%${RST}")
fi
```

PowerShell:
```powershell
$fhPct = $json.rate_limits.five_hour.used_percentage
if ($null -ne $fhPct) {
  $fhPct = [math]::Floor($fhPct)
  if ($fhPct -lt 50) { $fhColor = $GREEN } elseif ($fhPct -lt 80) { $fhColor = $YELLOW } else { $fhColor = $RED }
  $parts += "$eHourglass 5h $fhColor$fhPct%$RST"
}
```

**Section 11 — Weekly usage (rate limit):**

Renders only when `rate_limits.seven_day.used_percentage` is present. Note the field is `seven_day`, not `weekly`.

Bash:
```bash
# $sd_pct is set by the Python JSON parser ("" when the field is absent)
if [ -n "$sd_pct" ]; then
  if [ "$sd_pct" -lt 50 ]; then SD_COLOR="$GREEN"
  elif [ "$sd_pct" -lt 80 ]; then SD_COLOR="$YELLOW"
  else SD_COLOR="$RED"; fi
  parts+=("📅 semana ${SD_COLOR}${sd_pct}%${RST}")
fi
```

PowerShell:
```powershell
$sdPct = $json.rate_limits.seven_day.used_percentage
if ($null -ne $sdPct) {
  $sdPct = [math]::Floor($sdPct)
  if ($sdPct -lt 50) { $sdColor = $GREEN } elseif ($sdPct -lt 80) { $sdColor = $YELLOW } else { $sdColor = $RED }
  $parts += "$eCalendar semana $sdColor$sdPct%$RST"
}
```

**Section 12 — PR state:**

Renders only when the current branch has an associated PR (`pr.number` present). Icon and color follow `pr.review_state`.

Bash:
```bash
# $pr_num and $pr_state are set by the Python JSON parser ("" when absent)
if [ -n "$pr_num" ]; then
  case "$pr_state" in
    approved)          PR_COLOR="$GREEN";  PR_ICON="✅" ;;
    changes_requested) PR_COLOR="$RED";    PR_ICON="✋" ;;
    commented)         PR_COLOR="$YELLOW"; PR_ICON="💬" ;;
    *)                 PR_COLOR="$CYAN";   PR_ICON="🔀" ;;
  esac
  parts+=("${PR_ICON} ${PR_COLOR}#${pr_num}${RST}")
fi
```

PowerShell:
```powershell
if ($json.pr -and $json.pr.number) {
  switch ($json.pr.review_state) {
    "approved"          { $prColor = $GREEN;  $prIcon = $ePrOk }
    "changes_requested" { $prColor = $RED;    $prIcon = $ePrBlock }
    "commented"         { $prColor = $YELLOW; $prIcon = $ePrComment }
    default             { $prColor = $CYAN;   $prIcon = $ePr }
  }
  $parts += "$prIcon $prColor#$($json.pr.number)$RST"
}
```

#### Script footer — join parts with the separator

**Bash:**

```bash
# Join parts with separator
separator="{SEPARATOR}"
output=""
for i in "${!parts[@]}"; do
  if [ "$i" -gt 0 ]; then
    output+="$separator"
  fi
  output+="${parts[$i]}"
done

echo -e "$output"
```

**PowerShell:**

```powershell
# Join parts with separator
$separator = "{SEPARATOR}"
$output = $parts -join $separator
Write-Host $output
```

Replace `{BAR_WIDTH}` with the width chosen in step 4 (default: 20).
Replace `{SEPARATOR}` with the separator chosen in step 4 (default: ` | `).
Replace `{GENERATION_DATE}` with the current date.
If the user disabled emojis, remove the emojis from each block.
If the user disabled colors, remove the ANSI variables and color references.

Write the script to the appropriate path using the Write tool.

### Step 7 — Permissions

**Linux/macOS only:**

```bash
chmod +x ~/.claude/claude-status.sh
```

On Windows, PowerShell scripts do not need chmod. However, the default Windows execution policy blocks unsigned scripts.
Instead of asking the user to change the system policy, the solution is to use `-ExecutionPolicy Bypass` in the `settings.json` command (already handled in Step 8).

> **IMPORTANT:** Do NOT recommend `Set-ExecutionPolicy` — it is simpler and safer to use `-ExecutionPolicy Bypass` directly in the invocation command.

### Step 8 — Update settings.json

Read the `~/.claude/settings.json` file and insert or update the `statusLine` field:

**Linux/macOS:**

```json
{
  "statusLine": {
    "type": "command",
    "command": "~/.claude/claude-status.sh"
  }
}
```

**Windows:**

```json
{
  "statusLine": {
    "type": "command",
    "command": "powershell -ExecutionPolicy Bypass -File ~/.claude/claude-status.ps1"
  }
}
```

> **IMPORTANT:** The `statusLine` field requires `"type": "command"` (NOT `"enabled": true`).
> Using `"enabled": true` causes a validation error in `settings.json`.
> On Windows, include `-ExecutionPolicy Bypass` to avoid execution policy blocking.

Use the Read tool to read the current settings.json, preserve all existing settings, and use the Edit tool to update only the `statusLine` field. If the field already exists, overwrite it. If it does not exist, add it.

### Step 9 — Preview and verification

Run the generated script with a sample JSON to show the result to the user:

**Test JSON:**

```json
{
  "model": { "display_name": "Opus 4.6" },
  "context_window": {
    "used_percentage": 42,
    "context_window_size": 1000000,
    "total_input_tokens": 85000,
    "total_output_tokens": 12000
  },
  "workspace": { "current_dir": "{CURRENT_PROJECT_DIR}", "project_dir": "{CURRENT_PROJECT_DIR}" },
  "cost": {
    "total_cost_usd": 0.05,
    "total_duration_ms": 120000,
    "total_lines_added": 30,
    "total_lines_removed": 5
  },
  "rate_limits": {
    "five_hour": { "used_percentage": 23, "resets_at": 1738425600 },
    "seven_day": { "used_percentage": 81, "resets_at": 1738857600 }
  },
  "pr": { "number": 128, "url": "https://github.com/owner/repo/pull/128", "review_state": "approved" }
}
```

Replace `{CURRENT_PROJECT_DIR}` with the user's current working directory. The `rate_limits` and `pr` blocks are included so the preview exercises sections 10-12; in a real session they appear only for Pro/Max subscribers and branches with an open PR, respectively. To preview the graceful-omission behavior, run the script a second time with a JSON that omits both blocks and confirm those sections disappear.

**Linux/macOS:**
```bash
echo '<TEST_JSON>' | ~/.claude/claude-status.sh
```

**Windows:**
```powershell
'<TEST_JSON>' | powershell -ExecutionPolicy Bypass -File ~/.claude/claude-status.ps1
```

> **IMPORTANT (Windows):** In the test JSON, use forward slashes (`/`) in paths, not backslashes (`\`).
> Backslashes in JSON are interpreted as escape sequences by PowerShell's `ConvertFrom-Json`,
> causing an error: "Unrecognized escape sequence".
> Example: use `"C:/Users/pc_admin"` instead of `"C:\\Users\\pc_admin"`.

Display the output to the user and confirm that the status line is configured correctly.

If the output is correct, inform: "Status line configured successfully! Restart Claude Code to see the new status line in action."

If there is an error, diagnose and fix the script.

### Notes

- The status line is automatically updated by Claude Code on each interaction
- The input JSON contains data from the current session (model, context, costs, etc.)
- To reconfigure, simply run `/statusline:setup` again
- To disable, remove the `statusLine` block from `settings.json`
- The script should execute quickly (< 100ms) to avoid impacting the experience
- **Sections 10-12 are conditional**: the 5h/weekly usage sections (`rate_limits.*`) appear only for Claude.ai Pro/Max subscribers and only after the first API response of the session; the PR section (`pr.*`) appears only when the current branch has an associated PR. Their blocks guard on field presence and are silently omitted otherwise — so they are safe to keep in the default set even for users who never see them.

### Windows Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| Emojis appear as `??` | Missing UTF-8 encoding in the script | Add `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8` in the header |
| Emojis cause parsing error | Inline emoji in PowerShell code | Use variables with `[char]::ConvertFromUtf32()` — never embed emoji directly in the string |
| Progress bar shows diamonds | Characters `█░` incompatible with font | Use `#` and `-` instead |
| Cost with too many decimal places | Unformatted float value | Format with `([double]$cost).ToString("F2", [CultureInfo]::InvariantCulture)` |
| Cost shows `$0,00` / `printf: invalid number` (Bash) or comma decimal (PowerShell) | Locale/culture uses comma as decimal separator (pt-BR, de-DE, fr-FR, ...) — applies on Linux/macOS too, not Windows-only | Bash: `LC_NUMERIC=C printf "%.2f"`. PowerShell: `.ToString("F2", [CultureInfo]::InvariantCulture)` |
| Script blocked by execution policy | Default Windows policy | Use `-ExecutionPolicy Bypass` in the settings.json command |
| Error "unrecognized escape sequence" | Backslash `\` in test JSON | Use forward slashes `/` in paths inside the JSON |
| settings.json validation fails | Invalid `"enabled": true` field | Use `"type": "command"` instead of `"enabled": true` |
| Status line shows no data (Bash on Windows) | `git -C` fails because paths use `C:\...` format | Normalize paths in the script header: convert `\` to `/` and `C:/` to `/c/` (see header template) |
| `realpath --relative-to` not found | Git Bash doesn't ship `realpath` with `--relative-to` | Use the Python fallback chain: `python3` → `python` → `realpath` → `basename` |
| All fields show `--` or `$0.00` | `jq` not installed (old template) | Regenerate with `/statusline:setup` — new template uses Python, no jq needed |
