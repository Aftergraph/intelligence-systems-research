[CmdletBinding()]
param(
    [string]$Repository = "Aftergraph/intelligence-systems-research",
    [string]$RepositoryUrl = "https://github.com/Aftergraph/intelligence-systems-research",
    [string]$Branch = "main",
    [string]$RunnerDir = "C:\Aftergraph\JAR-EXP-0013\actions-runner",
    [string]$HarnessVenv = "C:\Aftergraph\JAR-EXP-0013\harness-venv",
    [string]$EvidenceDir = "C:\Aftergraph\JAR-EXP-0013\evidence",
    [string]$HostConfigPath = "C:\Aftergraph\JAR-EXP-0013\controlled-host.json",
    [string]$HermesPython = "C:\dev\AppData\Local\hermes\hermes-agent\.venv\Scripts\python.exe",
    [string]$HermesRoot = "C:\dev\AppData\Local\hermes\hermes-agent",
    [string]$Workspace = "C:\Aftergraph\JAR-EXP-0013\workspace",
    [string]$ToolRushRepo = "C:\dev\toolrush",
    [string]$ToolRushDoctor = "C:\dev\AppData\Local\hermes\plugins\toolrush\doctor.py",
    [string]$ToolRushPlugin = "C:\dev\AppData\Local\hermes\plugins\toolrush\__init__.py",
    [string]$ObscuraRepo = "C:\dev\obscura",
    [string]$ObscuraExecutable = "C:\dev\obscura\target\release\obscura.exe",
    [string]$ChromiumExecutable = "C:\Program Files\Google\Chrome\Application\chrome.exe",
    [int]$ObscuraPort = 9222,
    [switch]$RunPhase1,
    [switch]$RunPhase2,
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
    Invoke-NativeChecked -Executable $harnessPython -Arguments @(
        "-m", "pip", "install",
        "-r", "requirements-test.txt",
        "psutil>=6,<7",
        "playwright==1.62.0"
    ) -FailureMessage "Failed to install isolated JAR-EXP-0013 dependencies"
    Invoke-NativeChecked -Executable $harnessPython -Arguments @("-m", "pytest", "tests/runtime_acceleration", "-q") -FailureMessage "JAR-EXP-0013 functional suite failed on the controlled host"
}
finally {
    Pop-Location
}

Assert-Path "Hermes Python" $HermesPython
Assert-Path "Hermes root" $HermesRoot
Assert-Path "ToolRush repository" $ToolRushRepo
Assert-Path "ToolRush doctor" $ToolRushDoctor
Assert-Path "ToolRush plugin" $ToolRushPlugin
Assert-Path "Obscura repository" $ObscuraRepo
Assert-Path "Obscura executable" $ObscuraExecutable
Assert-Path "Chromium executable" $ChromiumExecutable

$resolvedWorkspace = [IO.Path]::GetFullPath($Workspace)
New-Item -ItemType Directory -Force -Path $resolvedWorkspace | Out-Null
Push-Location $repoRoot
try {
    Invoke-NativeChecked -Executable $harnessPython -Arguments @(
        "-c",
        "from experiments.runtime_acceleration.phase2_bindings import prepare_tool_microbench_workspace; import sys; prepare_tool_microbench_workspace(sys.argv[1])",
        $resolvedWorkspace
    ) -FailureMessage "Failed to prepare canonical JAR-EXP-0013 deterministic fixture"
}
finally {
    Pop-Location
}

$configDirectory = Split-Path -Parent ([IO.Path]::GetFullPath($HostConfigPath))
New-Item -ItemType Directory -Force -Path $configDirectory | Out-Null

$config = [ordered]@{
    experiment_id = "JAR-EXP-0013"
    hermes_python = ([IO.Path]::GetFullPath($HermesPython))
    hermes_root = ([IO.Path]::GetFullPath($HermesRoot))
    workspace = $resolvedWorkspace
    toolrush_repo = ([IO.Path]::GetFullPath($ToolRushRepo))
    toolrush_doctor = ([IO.Path]::GetFullPath($ToolRushDoctor))
    toolrush_plugin = ([IO.Path]::GetFullPath($ToolRushPlugin))
    obscura_repo = ([IO.Path]::GetFullPath($ObscuraRepo))
    obscura_executable = ([IO.Path]::GetFullPath($ObscuraExecutable))
    chromium_executable = ([IO.Path]::GetFullPath($ChromiumExecutable))
    obscura_port = $ObscuraPort
}
$config | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $HostConfigPath -Encoding UTF8
$resolvedConfig = [IO.Path]::GetFullPath($HostConfigPath)
Write-Host "Machine-local controlled-host config written: $resolvedConfig"

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

$plansDir = Join-Path $resolvedEvidenceDir "plans"
New-Item -ItemType Directory -Force -Path $plansDir | Out-Null
$protocolPath = Join-Path $repoRoot "experiments\runtime_acceleration\protocol.yaml"

$planStamp = [DateTime]::UtcNow.ToString("yyyyMMddTHHmmssfffZ")
$tracePlanPath = Join-Path $plansDir "trace-plan-$planStamp.json"
$tracePath = Join-Path $repoRoot "experiments\runtime_acceleration\workloads\trace_replay.yaml"
Push-Location $repoRoot
try {
    Invoke-NativeChecked -Executable $harnessPython -Arguments @(
        "-m", "experiments.runtime_acceleration.measurement_plan",
        "--trace", $tracePath,
        "--output", $tracePlanPath,
        "--repetitions", "20",
        "--seed", "130013"
    ) -FailureMessage "Failed to freeze JAR-EXP-0013 Phase-1 trace plan"
}
finally {
    Pop-Location
}
Write-Host "Phase-1 trace plan frozen: $tracePlanPath"
Write-Host "Phase-1 schedule: 20 paired blocks x 4 conditions = 80 planned runs; plan creation is not performance evidence."

$phase2PlanStamp = [DateTime]::UtcNow.ToString("yyyyMMddTHHmmssfffZ")
$phase2PlanPath = Join-Path $plansDir "phase2-plan-$phase2PlanStamp.json"
$toolMicrobenchPath = Join-Path $repoRoot "experiments\runtime_acceleration\workloads\tool_microbench.yaml"
Push-Location $repoRoot
try {
    Invoke-NativeChecked -Executable $harnessPython -Arguments @(
        "-m", "experiments.runtime_acceleration.phase2_tool_microbench",
        "--workload", $toolMicrobenchPath,
        "--protocol", $protocolPath,
        "--output", $phase2PlanPath
    ) -FailureMessage "Failed to freeze JAR-EXP-0013 Phase-2 tool microbenchmark plan"
}
finally {
    Pop-Location
}
$phase2Plan = Get-Content -LiteralPath $phase2PlanPath -Raw -Encoding UTF8 | ConvertFrom-Json
Write-Host "Phase-2 tool plan frozen: $phase2PlanPath"
Write-Host "Phase-2 schedule: $($phase2Plan.paired_blocks) paired blocks x 2 conditions = $($phase2Plan.planned_runs) planned runs; plan creation is not performance evidence."

if (-not $RunPhase1) {
    Write-Host "Phase-1 measurements were NOT started. Re-run with -RunPhase1 after reviewing READY probe and frozen plan."
}
else {
    $phase1ExecutionId = "phase1-" + [DateTime]::UtcNow.ToString("yyyyMMddTHHmmssfffZ")
    Write-Host "Starting controlled Phase-1 execution: $phase1ExecutionId"
    $phase1Arguments = @(
        "-m", "experiments.runtime_acceleration.phase1_host_run",
        "--config", $resolvedConfig,
        "--plan", $tracePlanPath,
        "--probe", $probePath,
        "--protocol", $protocolPath,
        "--evidence-root", $resolvedEvidenceDir,
        "--execution-id", $phase1ExecutionId
    )
    Push-Location $repoRoot
    try {
        & $harnessPython @phase1Arguments
        $phase1RunExit = $LASTEXITCODE
    }
    finally {
        Pop-Location
    }

    $phase1SessionDir = Join-Path $resolvedEvidenceDir $phase1ExecutionId
    $phase1SummaryPath = Join-Path $phase1SessionDir "summary.json"
    $phase1AnalysisJson = Join-Path $phase1SessionDir "phase1-analysis.json"
    $phase1AnalysisMarkdown = Join-Path $phase1SessionDir "phase1-analysis.md"
    Assert-Path "Phase-1 summary" $phase1SummaryPath

    Push-Location $repoRoot
    try {
        Invoke-NativeChecked -Executable $harnessPython -Arguments @(
            "-m", "experiments.runtime_acceleration.phase1_analysis",
            "--summary", $phase1SummaryPath,
            "--protocol", $protocolPath,
            "--json-output", $phase1AnalysisJson,
            "--markdown-output", $phase1AnalysisMarkdown
        ) -FailureMessage "JAR-EXP-0013 Phase-1 analysis did not complete cleanly"
    }
    finally {
        Pop-Location
    }

    Write-Host "Controlled Phase-1 execution finished: $phase1ExecutionId"
    Write-Host "Evidence root: $resolvedEvidenceDir"
    Write-Host "Phase-1 analysis JSON: $phase1AnalysisJson"
    Write-Host "Phase-1 analysis report: $phase1AnalysisMarkdown"
    Write-Host "Promotion gates remain INCONCLUSIVE after Phase-1 trace analysis."

    if ($phase1RunExit -ne 0) {
        Write-Host "Diagnostic Phase-1 analysis was retained, but the controlled execution was non-clean (exit code $phase1RunExit)."
        exit $phase1RunExit
    }
}

if (-not $RunPhase2) {
    Write-Host "Phase-2 tool measurements were NOT started. Re-run with -RunPhase2 after reviewing READY probe and frozen plan."
}
else {
    $phase2ExecutionId = "phase2-" + [DateTime]::UtcNow.ToString("yyyyMMddTHHmmssfffZ")
    Write-Host "Starting controlled Phase-2 execution: $phase2ExecutionId"
    $phase2Arguments = @(
        "-m", "experiments.runtime_acceleration.phase2_host_run",
        "--config", $resolvedConfig,
        "--plan", $phase2PlanPath,
        "--probe", $probePath,
        "--protocol", $protocolPath,
        "--evidence-root", $resolvedEvidenceDir,
        "--execution-id", $phase2ExecutionId
    )
    Push-Location $repoRoot
    try {
        & $harnessPython @phase2Arguments
        $phase2RunExit = $LASTEXITCODE
    }
    finally {
        Pop-Location
    }

    $phase2SessionDir = Join-Path $resolvedEvidenceDir $phase2ExecutionId
    $phase2SummaryPath = Join-Path $phase2SessionDir "summary.json"
    $phase2AnalysisJson = Join-Path $phase2SessionDir "phase2-analysis.json"
    $phase2AnalysisMarkdown = Join-Path $phase2SessionDir "phase2-analysis.md"
    Assert-Path "Phase-2 summary" $phase2SummaryPath

    Push-Location $repoRoot
    try {
        Invoke-NativeChecked -Executable $harnessPython -Arguments @(
            "-m", "experiments.runtime_acceleration.phase2_analysis",
            "--summary", $phase2SummaryPath,
            "--protocol", $protocolPath,
            "--json-output", $phase2AnalysisJson,
            "--markdown-output", $phase2AnalysisMarkdown
        ) -FailureMessage "JAR-EXP-0013 Phase-2 analysis did not complete cleanly"
    }
    finally {
        Pop-Location
    }

    Write-Host "Controlled Phase-2 execution finished: $phase2ExecutionId"
    Write-Host "Evidence root: $resolvedEvidenceDir"
    Write-Host "Phase-2 analysis JSON: $phase2AnalysisJson"
    Write-Host "Phase-2 analysis report: $phase2AnalysisMarkdown"
    Write-Host "Promotion gates remain INCONCLUSIVE after Phase-2 tool analysis."

    if ($phase2RunExit -ne 0) {
        Write-Host "Diagnostic Phase-2 analysis was retained, but the controlled execution was non-clean (exit code $phase2RunExit)."
        exit $phase2RunExit
    }
}

if (-not $DispatchWorkflow) {
    Write-Host "GitHub self-hosted workflow dispatch is optional and was not requested."
    Write-Host "Hosted-runner timing remains non-performance evidence."
    exit 0
}

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
