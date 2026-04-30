# PowerShell patterns — idiomatic equivalents to the bash idioms

This is **not** a literal port of `bash-patterns.md`. PowerShell has different primitives (`Get-NetTCPConnection`, `Stop-Process`, `Register-EngineEvent`, jobs vs background processes) and getting them right matters more than reading like bash.

Target: **PowerShell 7+** (pwsh) for cross-platform; **PowerShell 5.1** (Windows-only, default Windows 10/11) when the user explicitly says "no install of pwsh". Where 5.1 differs, the section calls it out.

## Header — strict mode + script-dir resolution

```powershell
#Requires -Version 5.1
[CmdletBinding()] param(
  [string]$HostOverride = "",
  [switch]$NoLan,
  [switch]$NoHttps,
  [switch]$Reset,
  [switch]$Down
)

$ErrorActionPreference = 'Stop'        # equivalent to bash `set -e`
Set-StrictMode -Version 3.0            # equivalent to bash `set -u` (catches $undefined)
$PSDefaultParameterValues['*:Encoding'] = 'utf8'

$SCRIPT_DIR = Split-Path -LiteralPath $MyInvocation.MyCommand.Path -Parent
Set-Location -LiteralPath $SCRIPT_DIR
```

Notes:

- `$ErrorActionPreference = 'Stop'` makes non-terminating errors fatal — without it, `Get-NetTCPConnection -Port 3000 -ErrorAction Continue` returning empty doesn't halt the script.
- `Set-StrictMode -Version 3.0` errors out on uninitialized variables and out-of-bounds array access — the closest analogue to `set -u`.
- Use `[CmdletBinding()] param(...)` not raw `$args` parsing — gives you `-Verbose`/`-WhatIf` for free, plus type checking on `[switch]`.

## Color logging (works on PS 5.1 + 7)

```powershell
function Write-Info  { param($Message) Write-Host "[INFO] $Message"  -ForegroundColor Green }
function Write-WarnLog { param($Message) Write-Host "[WARN] $Message"  -ForegroundColor Yellow }
function Write-ErrorLog{ param($Message) Write-Host "[ERROR] $Message" -ForegroundColor Red }
function Write-Step  { param($Message) Write-Host "`n==> $Message" -ForegroundColor Blue }
```

`Write-Host` with `-ForegroundColor` is the right primitive (`Write-Output` would pollute the pipeline). Don't shadow `Write-Warning`/`Write-Error` — they have non-coloring side effects (the latter throws under `-ErrorAction Stop`).

For ANSI color when piping output through services (the equivalent of `sed -u` prefixing in bash), wrap each child process's stdout in PowerShell's `$PSStyle` (PS 7+) or a manual ANSI escape:

```powershell
# PS 7.x — $PSStyle handles ANSI rendering automatically
$webPrefix = "$([char]27)[34m[WEB]$([char]27)[0m"

# Stream a child process's output with the prefix
Start-ThreadJob {
  param($prefix)
  & npm run dev -- --host 0.0.0.0 --port 5173 2>&1 |
    ForEach-Object { Write-Host "$prefix $_" }
} -ArgumentList $webPrefix
```

On Windows PS 5.1, ANSI doesn't render in legacy console hosts unless you enable VT mode:

```powershell
if ($PSVersionTable.PSVersion.Major -lt 7) {
  # Enable VT processing in legacy conhost (Windows 10+)
  $signature = '[DllImport("kernel32.dll")] public static extern bool SetConsoleMode(IntPtr hConsoleHandle, uint dwMode);
                [DllImport("kernel32.dll")] public static extern IntPtr GetStdHandle(int nStdHandle);'
  Add-Type -MemberDefinition $signature -Name VT -Namespace WinAPI -ErrorAction SilentlyContinue
  $h = [WinAPI.VT]::GetStdHandle(-11)  # STD_OUTPUT_HANDLE
  [WinAPI.VT]::SetConsoleMode($h, 0x0007) | Out-Null
}
```

If that's too much for the script, drop ANSI on PS 5.1 and rely on `-ForegroundColor` only — colors still work, just not in the prefix-per-line streaming.

## LAN IP detection

```powershell
function Get-LanIp {
  # Prefer the route-to-internet source IP (mirrors `ip route get 1.1.1.1`)
  try {
    $route = Find-NetRoute -RemoteIPAddress 1.1.1.1 -ErrorAction Stop |
             Select-Object -First 1
    if ($route -and $route.IPAddress) { return $route.IPAddress }
  } catch { }

  # Fallback: first non-loopback IPv4 address that is up
  $ip = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object { $_.IPAddress -notmatch '^(127\.|169\.254\.)' -and $_.PrefixOrigin -eq 'Dhcp' } |
        Select-Object -ExpandProperty IPAddress -First 1
  return $ip
}
```

`Find-NetRoute` is the closest analogue to `ip route get`. The fallback filters out APIPA (`169.254.x.x`) and loopback. On non-Windows pwsh, `Get-NetIPAddress` doesn't exist — use this fallback:

```powershell
if ($IsLinux -or $IsMacOS) {
  function Get-LanIp { (hostname -I).Trim().Split()[0] }
}
```

## Healthchecks

### Postgres in docker

```powershell
Write-Step "Waiting for Postgres…"
$ok = $false
for ($i = 1; $i -le 30; $i++) {
  $null = docker compose -f $ComposeFile exec -T postgres pg_isready -U $DbUser 2>&1
  if ($LASTEXITCODE -eq 0) { Write-Info "Postgres ready"; $ok = $true; break }
  Start-Sleep -Seconds 1
}
if (-not $ok) { Write-ErrorLog "Postgres did not become ready"; exit 1 }
```

`$LASTEXITCODE` is the equivalent of bash `$?` for native commands. Don't trust `$?` alone in PowerShell — it's a `[bool]` that conflates several signals.

### HTTP service

```powershell
Write-Step "Waiting for service at $BaseUrl/healthz…"
$caCert = if ($TlsMode) { (mkcert -CAROOT) + "/rootCA.pem" } else { $null }
$ok = $false
for ($i = 1; $i -le 60; $i++) {
  try {
    if ($caCert) {
      # PS 7+: -SkipCertificateCheck or load CA into a custom HttpClient.
      # The cleanest portable route: shell out to curl which honors --cacert.
      $null = curl --silent --fail --cacert $caCert "$BaseUrl/healthz" 2>&1
    } else {
      $null = Invoke-WebRequest -Uri "$BaseUrl/healthz" -UseBasicParsing -TimeoutSec 5
    }
    if ($LASTEXITCODE -eq 0 -or $? -eq $true) { Write-Info "Service ready"; $ok = $true; break }
  } catch { }
  Start-Sleep -Seconds 2
}
if (-not $ok) { Write-ErrorLog "Service did not become ready at $BaseUrl"; exit 1 }
```

PowerShell's `Invoke-WebRequest` will throw on a self-signed cert with no good way to inject a CA bundle (the `-Certificate` param is for client auth, not server trust). `-SkipCertificateCheck` (PS 7+) bypasses validation entirely, which defeats the point. **Shell out to `curl`** when you need real CA validation against a local root CA. curl is on Windows 10 1803+ by default.

## Port reclaim — Windows-native

```powershell
function Stop-PortHolder {
  param([int]$Port)
  $owners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
  foreach ($o in $owners) {
    $proc = Get-Process -Id $o.OwningProcess -ErrorAction SilentlyContinue
    if ($proc) {
      Write-WarnLog "Port $Port held by $($proc.ProcessName) ($($o.OwningProcess)) — killing"
      Stop-Process -Id $o.OwningProcess -Force -ErrorAction SilentlyContinue
      Start-Sleep -Milliseconds 500
    }
  }
}
```

`Get-NetTCPConnection -LocalPort` is Windows-only. On non-Windows pwsh, fall through to the bash idioms via shell out (`fuser`/`lsof`/`ss`). A cross-platform wrapper:

```powershell
function Stop-PortHolder {
  param([int]$Port)
  if ($IsWindows -or [Environment]::OSVersion.Platform -eq 'Win32NT') {
    # ... Windows version above ...
  } else {
    $pids = & fuser "$Port/tcp" 2>$null | ForEach-Object { $_ -replace '\s+', '' } | Where-Object { $_ -match '^\d+$' }
    if (-not $pids) { $pids = & lsof "-tiTCP:$Port" "-sTCP:LISTEN" 2>$null }
    foreach ($pidNum in $pids) {
      Write-WarnLog "Port $Port held by PID $pidNum — killing"
      & kill -9 $pidNum 2>$null
    }
  }
}
```

## Cleanup — Register-EngineEvent + try/finally

PowerShell has no `trap` syntax for shell-style cleanup. The combo that works:

```powershell
$Global:DevScriptChildJobs = @()

function Stop-DevScriptChildren {
  foreach ($j in $Global:DevScriptChildJobs) {
    try {
      Stop-Job -Job $j -ErrorAction SilentlyContinue
      Remove-Job -Job $j -Force -ErrorAction SilentlyContinue
    } catch { }
  }
}

# Catches Ctrl+C *and* normal exit
Register-EngineEvent -SourceIdentifier PowerShell.Exiting -SupportEvent -Action {
  Stop-DevScriptChildren
} | Out-Null

try {
  # ... start jobs ...
  Wait-Job -Job $Global:DevScriptChildJobs
}
finally {
  Stop-DevScriptChildren
  if ($Down) {
    Write-WarnLog "--Down: tearing down containers"
    docker compose -f $ComposeFile down 2>&1 | Out-Null
  }
  Write-Info "Stopped."
}
```

If using `Start-Process` instead of jobs (for true child processes with their own stdout streams), track `$proc.Id` and `Stop-Process -Id` them in the cleanup.

**Important on PS 5.1**: `Start-ThreadJob` requires the `ThreadJob` module (preinstalled on PS 7, available via `Install-Module ThreadJob` on 5.1). Prefer `Start-Job` if you can't assume the module — slower (process per job) but works everywhere.

## Patching `.env` files

```powershell
function Set-EnvKv {
  param([string]$File, [string]$Key, [string]$Value)
  if (-not (Test-Path -LiteralPath $File)) { New-Item -ItemType File -Path $File | Out-Null }
  $content = Get-Content -LiteralPath $File -Raw -ErrorAction SilentlyContinue
  if ($null -eq $content) { $content = "" }
  $pattern = "(?m)^${Key}=.*$"
  if ($content -match $pattern) {
    $new = [regex]::Replace($content, $pattern, "${Key}=${Value}")
  } else {
    $new = $content.TrimEnd("`r","`n") + "`n${Key}=${Value}`n"
  }
  Set-Content -LiteralPath $File -Value $new -NoNewline:$false
}

Set-EnvKv -File $BackendEnv -Key 'AUTH_ISSUER'   -Value $ZitadelBase
Set-EnvKv -File $BackendEnv -Key 'AUTH_AUDIENCE' -Value $ProjectId
```

Use `[regex]::Replace` not `-replace` — the latter has surprising precedence. Use `-LiteralPath` everywhere file paths are involved (handles spaces and `[` in paths).

## Heredoc-equivalent — multi-line file content

```powershell
$caddyfile = @"
{
  auto_https off
  admin off
}

${ExternalDomain}:${WebPort} {
  tls /certs/dev.pem /certs/dev.key
  reverse_proxy localhost:5173
}
"@
Set-Content -LiteralPath $CaddyfilePath -Value $caddyfile
```

`@"…"@` is a here-string with variable interpolation. `@'…'@` is the literal version (no interpolation) — useful when the content contains `$` references that aren't PowerShell variables.

## Background services with prefixed output (PS 7+)

```powershell
function Start-PrefixedJob {
  param([string]$Name, [string]$Color, [scriptblock]$Action)
  $prefix = "$([char]27)[${Color}m[$Name]$([char]27)[0m"
  Start-ThreadJob -Name $Name -ScriptBlock {
    param($prefix, $Action)
    & $Action 2>&1 | ForEach-Object { Write-Host "$prefix $_" }
  } -ArgumentList $prefix, $Action
}

$backendJob = Start-PrefixedJob -Name 'BACKEND' -Color '32' -Action {
  Set-Location packages/backend
  $env:NODE_EXTRA_CA_CERTS = "$Using:MkcertCaroot/rootCA.pem"
  npm run dev
}

$webJob = Start-PrefixedJob -Name 'WEB' -Color '34' -Action {
  $env:DEV_SH_EXTERNAL = $Using:ExternalDomain
  npm run dev -- --config .vite.config.lan.ts --host 0.0.0.0 --port 5173 --strictPort
}

$Global:DevScriptChildJobs = @($backendJob, $webJob)
Wait-Job -Job $Global:DevScriptChildJobs
```

ANSI codes `[32m` (green) and `[34m` (blue) — assumes VT mode is on (PS 7 by default; PS 5.1 needs the shim above).

## Final summary

```powershell
Write-Host ""
Write-Host "=============================================" -ForegroundColor Green
Write-Host "  $ProjectName — dev mode"               -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Frontend   → $WebBase"   -ForegroundColor Blue
Write-Host "  Backend    → $ApiBase/api" -ForegroundColor Green
if ($ZitadelBase) {
  Write-Host "  IdP        → $ZitadelBase" -ForegroundColor Magenta
}
Write-Host ""
Write-Host "  Ctrl+C to stop dev servers (containers stay; --Down to tear down)."
Write-Host "=============================================" -ForegroundColor Green
Write-Host ""
```

## Bash → PowerShell equivalence cheatsheet

| Bash | PowerShell |
|---|---|
| `set -e` | `$ErrorActionPreference = 'Stop'` |
| `set -u` | `Set-StrictMode -Version 3.0` |
| `set -o pipefail` | (no direct equivalent — chain explicit `if (-not $?) { throw }`) |
| `trap fn EXIT SIGINT` | `Register-EngineEvent PowerShell.Exiting -Action {…}` + `try/finally` |
| `kill -- "-$pid"` (process group) | `Stop-Process -Id $pid -Force` (no group concept; track jobs/processes individually) |
| `command -v X` | `Get-Command X -ErrorAction SilentlyContinue` |
| `mktemp` | `New-TemporaryFile` (returns FileInfo) |
| `realpath`/`readlink -f` | `Resolve-Path -LiteralPath` (PS 6+: `-Relative` flag exists) |
| heredoc `<<EOF` | here-string `@"..."@` |
| `awk '{print $1}'` | `($_ -split '\s+')[0]` or `(... | Select-Object -First 1)` |
| `&` (background) | `Start-Job` / `Start-ThreadJob` / `Start-Process` |
| `wait` | `Wait-Job` / `Wait-Process` |
| `$?` (last exit) | `$LASTEXITCODE` (native) or `$?` (cmdlet) |
| `${var:-default}` | `if ($var) { $var } else { 'default' }` or coalesce `$var ?? 'default'` (PS 7+) |
