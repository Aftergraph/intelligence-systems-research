[CmdletBinding()]
param(
    [string]$Repository = "Aftergraph/intelligence-systems-research",
    [string]$RepositoryUrl = "https://github.com/Aftergraph/intelligence-systems-research",
    [string]$Branch = "research/jar-exp-0013-runtime-acceleration",
    [string]$RunnerDir = "C:\Aftergraph\JAR-EXP-0013\actions-runner",
    [string]$HarnessVenv = "C:\Aftergraph\JAR-EXP-0013\harness-venv",
    [string]$EvidenceDir = "C:\Aftergraph\JAR-EXP-0013\evidence",
    [string]$HostConfigPath = "C:\Aftergraph\JAR-EXP-0013\controlled-host.json",
    [string]$HermesPython = "C:\dev\AppData\Local\hermes\hermes-agent\.venv\Scripts\python.exe",
    [string]$ToolRushRepo = "C:\dev\toolrush",
    [string]$ToolRushDoctor = "C:\dev\AppData\Local\hermes\plugins\toolrush\doctor.py",
    [string]$ObscuraRepo = "C:\dev\obscura",
    [string]$ObscuraExecutable = "C:\dev\obscura\target\release\obscura.exe",
    [int]$ObscuraPort = 9222,
    [switch]$SkipRunnerRegistration,
    [switch]$DispatchWorkflow
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Assert-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "Run start-controlled-host.ps1 from an elevated PowerShell session."
    }
}

function Assert-Command([string]$Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' was not found on PATH."
    }
}

function Assert-Path([string]$Name, [string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "$Name is missing: $Path"
    }
}

function Invoke-NativeChecked {
    param(
        [Parameter(Mandatory = $true)][string]$Executable,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [Parameter(Mandatory = $true)][string]$FailureMessage
    )
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$FailureMessage (exit code $LASTEXITCODE)."
    }
}

Assert-Administrator
Assert-Command "python"

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = [IO.Path]::GetFullPath((Join-Path $scriptRoot "..\.."))
$bootstrap = Join-Path $scriptRoot "bootstrap-self-hosted-runner.ps1"
Assert-Path "Runner bootstrap" $bootstrap

$pythonCommand = (Get-Command python -ErrorAction Stop).Source
& $pythonCommand -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 3)"
if ($LASTEXITCODE -ne 0) {
    throw "JAR-EXP-0013 requires Python 3.11 for the isolated harness environment."
}

$harnessRoot = [IO.Path]::GetFullPath($HarnessVenv)
$harnessPython = Join-Path $harnessRoot "Scripts\python.exe"
if (-not (Test-Path -LiteralPath $harnessPython)) {
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $harnessRoot) | Out-Null
    Invoke-NativeChecked -Executable $pythonCommand -Arguments @("-m", "venv", $harnessRoot) -FailureMessage "Failed to create isolated JAR-EXP-0013 harness venv"
}
Assert-Path "Harness Python" $harnessPython

Push-Location $repoRoot
try {
    Invoke-NativeChecked -Executable $harnessPython -Arguments @("-m", "pip", "install", "-r", "requirements-test.txt", "psutil>=6,<7") -FailureMessage "Failed to install isolated JAR-EXP-0013 dependencies"
    Invoke-NativeChecked -Executable $harnessPython -Arguments @("-m", "pytest", "tests/runtime_acceleration", "-q") -FailureMessage "JAR-EXP-0013 functional suite failed on the controlled host"
}
finally {
    Pop-Location
}

# Fail early on host-local treatment paths before creating probe configuration.
Assert-Path "Hermes Python" $HermesPython
Assert-Path "ToolRush repository" $ToolRushRepo
Assert-Path "ToolRush doctor" $ToolRushDoctor
Assert-Path "Obscura repository" $ObscuraRepo
Assert-Path "Obscura executable" $ObscuraExecutable

$configDirectory = Split-Path -Parent ([IO.Path]::GetFullPath($HostConfigPath))
New-Item -ItemType Directory -Force -Path $configDirectory | Out-Null

$config = [ordered]@{
    experiment_id = "JAR-EXP-0013"
    hermes_python = ([IO.Path]::GetFullPath($HermesPython))
    toolrush_repo = ([IO.Path]::GetFullPath($ToolRushRepo))
    toolrush_doctor = ([IO.Path]::GetFullPath($ToolRushDoctor))
    obscura_repo = ([IO.Path]::GetFullPath($ObscuraRepo))
    obscura_executable = ([IO.Path]::GetFullPath($ObscuraExecutable))
    obscura_port = $ObscuraPort
}
$config | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $HostConfigPath -Encoding UTF8
$resolvedConfig = [IO.Path]::GetFullPath($HostConfigPath)
Write-Host "Machine-local controlled-host config written: $resolvedConfig"

# Run the authoritative preflight locally first. This avoids depending on workflow_dispatch
# availability on the default branch and gives the operator immediate READY/BLOCKED evidence.
$resolvedEvidenceDir = [IO.Path]::GetFullPath($EvidenceDir)
New-Item -ItemType Directory -Force -Path $resolvedEvidenceDir | Out-Null
$probePath = Join-Path $resolvedEvidenceDir "controlled-host-probe.json"

Push-Location $repoRoot
try {
    & $harnessPython -m experiments.runtime_acceleration.controlled_host --config $resolvedConfig --output $probePath
    $probeExit = $LASTEXITCODE
}
finally {
    Pop-Location
}

if (-not (Test-Path -LiteralPath $probePath)) {
    throw "Controlled-host probe did not produce evidence: $probePath"
}
$probe = Get-Content -LiteralPath $probePath -Raw -Encoding UTF8 | ConvertFrom-Json
Write-Host "Controlled-host state: $($probe.state)"
Write-Host "Probe evidence: $probePath"

if ($probe.state -ne "READY") {
    Write-Host "Controlled-host probe is not READY; confirmatory performance execution is blocked."
    if ($probeExit -ne 0) {
        exit $probeExit
    }
    exit 2
}

Write-Host "Controlled-host probe READY. The machine may enter the preregistered measurement phases."

if (-not $DispatchWorkflow) {
    Write-Host "GitHub self-hosted workflow dispatch is optional and was not requested."
    Write-Host "Local probe evidence is authoritative for host readiness; hosted-runner timing remains non-performance evidence."
    exit 0
}

# Optional GitHub self-hosted workflow path. GitHub CLI owns credential storage; only a
# short-lived runner registration token is materialized, and it is cleared after bootstrap.
Assert-Command "gh"
& gh auth status --hostname github.com | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "GitHub CLI is not authenticated. Run 'gh auth login' and retry with -DispatchWorkflow."
}

$runnerIdentity = Join-Path ([IO.Path]::GetFullPath($RunnerDir)) ".runner"
if (-not $SkipRunnerRegistration -and -not (Test-Path -LiteralPath $runnerIdentity)) {
    Write-Host "Requesting a short-lived self-hosted runner registration token through authenticated GitHub CLI..."
    $token = (& gh api --method POST "repos/$Repository/actions/runners/registration-token" --jq ".token").Trim()
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($token)) {
        $token = $null
        throw "GitHub did not return a runner registration token. Verify repository admin access."
    }

    $secureToken = ConvertTo-SecureString $token -AsPlainText -Force
    $token = $null
    try {
        & $bootstrap -RepositoryUrl $RepositoryUrl -RunnerDir $RunnerDir -RegistrationToken $secureToken
        if ($LASTEXITCODE -ne 0) {
            throw "Runner bootstrap failed with exit code $LASTEXITCODE."
        }
    }
    finally {
        $secureToken = $null
    }
}
elseif (Test-Path -LiteralPath $runnerIdentity) {
    Write-Host "Dedicated JAR-EXP-0013 runner identity already exists; registration is skipped."
}
else {
    Write-Host "Runner registration explicitly skipped."
}

Write-Host "Dispatching the controlled-host probe to the dedicated Windows runner..."
& gh workflow run "jar-exp-0013-controlled-host.yml" --repo $Repository --ref $Branch -f "host_config_path=$resolvedConfig"
if ($LASTEXITCODE -ne 0) {
    throw "GitHub workflow dispatch failed. The workflow must be available to workflow_dispatch on the repository default branch before remote dispatch can be used. Local READY evidence remains valid."
}

Write-Host "JAR-EXP-0013 controlled-host workflow dispatched."
Write-Host "Branch: $Branch"
Write-Host "Host config: $resolvedConfig"
