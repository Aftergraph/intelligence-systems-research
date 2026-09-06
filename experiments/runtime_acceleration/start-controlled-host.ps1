[CmdletBinding()]
param(
    [string]$Repository = "Aftergraph/intelligence-systems-research",
    [string]$RepositoryUrl = "https://github.com/Aftergraph/intelligence-systems-research",
    [string]$Branch = "research/jar-exp-0013-runtime-acceleration",
    [string]$RunnerDir = "C:\Aftergraph\JAR-EXP-0013\actions-runner",
    [string]$HostConfigPath = "C:\Aftergraph\JAR-EXP-0013\controlled-host.json",
    [string]$HermesPython = "C:\dev\AppData\Local\hermes\hermes-agent\.venv\Scripts\python.exe",
    [string]$ToolRushRepo = "C:\dev\toolrush",
    [string]$ToolRushDoctor = "C:\dev\AppData\Local\hermes\plugins\toolrush\doctor.py",
    [string]$ObscuraRepo = "C:\dev\obscura",
    [string]$ObscuraExecutable = "C:\dev\obscura\target\release\obscura.exe",
    [int]$ObscuraPort = 9222,
    [switch]$SkipRunnerRegistration,
    [switch]$NoDispatch
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

Assert-Administrator
Assert-Command "gh"

# Require an already-authenticated GitHub CLI session. No PAT or long-lived credential is
# accepted by this script; GitHub CLI owns credential storage and authentication policy.
& gh auth status --hostname github.com | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "GitHub CLI is not authenticated. Run 'gh auth login' and retry."
}

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$bootstrap = Join-Path $scriptRoot "bootstrap-self-hosted-runner.ps1"
Assert-Path "Runner bootstrap" $bootstrap

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

# Fail early on host-local treatment paths before creating or dispatching configuration.
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

if ($NoDispatch) {
    Write-Host "Dispatch skipped by request. Host handoff preparation is complete."
    exit 0
}

Write-Host "Dispatching the manual controlled-host probe to the dedicated Windows runner..."
& gh workflow run "jar-exp-0013-controlled-host.yml" --repo $Repository --ref $Branch -f "host_config_path=$resolvedConfig"
if ($LASTEXITCODE -ne 0) {
    throw "GitHub workflow dispatch failed with exit code $LASTEXITCODE."
}

Write-Host "JAR-EXP-0013 controlled-host workflow dispatched."
Write-Host "Branch: $Branch"
Write-Host "Host config: $resolvedConfig"
Write-Host "Next evidence state must come from the self-hosted controlled-host run; hosted-runner timing is not performance evidence."
