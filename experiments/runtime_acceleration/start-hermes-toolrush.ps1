param(
  [string]$HermesExe = "hermes",
  [string]$HermesPython = "python",
  [string]$ToolRushRepo,
  [string]$ToolRushDoctor,
  [string]$ToolRushPlugin,
  [string]$ExpectedToolRushHead = "4ecd8810fdc9e6e0c64af3d532f876d06f6a278e",
  [string[]]$HermesArgs = @()
)
$ErrorActionPreference = "Stop"

function Sha256([string]$Path) {
  return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

$selected = "stock"
$fallback = "not_promoted"
$disabled = $env:AFTERGRAPH_TOOLRUSH_DISABLED -eq "1"
$healthy = $false

if (-not $disabled -and $ToolRushRepo -and $ToolRushDoctor -and $ToolRushPlugin) {
  try {
    $head = (& git -C $ToolRushRepo rev-parse HEAD).Trim().ToLowerInvariant()
    if ($head -ne $ExpectedToolRushHead.ToLowerInvariant()) { throw "revision_mismatch" }
    $pinnedPlugin = Join-Path $ToolRushRepo "v2/plugin/__init__.py"
    $pinnedDoctor = Join-Path $ToolRushRepo "v2/plugin/doctor.py"
    if ((Sha256 $ToolRushPlugin) -ne (Sha256 $pinnedPlugin)) { throw "plugin_hash_mismatch" }
    if ((Sha256 $ToolRushDoctor) -ne (Sha256 $pinnedDoctor)) { throw "doctor_hash_mismatch" }
    & $HermesPython $ToolRushDoctor --smoke | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "doctor_failed" }
    $healthy = $true
  } catch {
    $fallback = $_.Exception.Message
  }
}

if ($disabled) { $fallback = "kill_switch" }
elseif ($healthy) {
  $selected = "toolrush"
  $fallback = $null
  $env:TOOLRUSH_FASTLANE = "1"
  $env:TOOLRUSH_SEARCH = "1"
  $env:TOOLRUSH_PERSIST = "1"
} else {
  Remove-Item Env:TOOLRUSH_FASTLANE -ErrorAction SilentlyContinue
  Remove-Item Env:TOOLRUSH_SEARCH -ErrorAction SilentlyContinue
  Remove-Item Env:TOOLRUSH_PERSIST -ErrorAction SilentlyContinue
}

$statusDir = Join-Path $env:LOCALAPPDATA "hermes/runtime-status"
New-Item -ItemType Directory -Force -Path $statusDir | Out-Null
@{
  timestamp_utc = [DateTime]::UtcNow.ToString("o")
  selected_runtime = $selected
  fallback_reason = $fallback
  promoted_gate = "G-TR:PASS"
} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $statusDir "toolrush-runtime.json") -Encoding UTF8

& $HermesExe @HermesArgs
exit $LASTEXITCODE
