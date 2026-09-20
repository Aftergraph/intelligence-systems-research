[CmdletBinding()]
param(
    [string]$RunnerDir = "C:\Aftergraph\JAR-EXP-0013\actions-runner",
    [string]$ExpectedRepositoryUrl = "https://github.com/Aftergraph/intelligence-systems-research",
    [switch]$InspectOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Fail([string]$Code, [string]$Message) {
    [ordered]@{
        ok = $false
        code = $Code
        message = $Message
        mutation_performed = $false
    } | ConvertTo-Json -Depth 5
    exit 2
}

$root = try { (Resolve-Path -LiteralPath $RunnerDir -ErrorAction Stop).Path.TrimEnd("\") } catch {
    Fail "runner_dir_missing" "Canonical runner directory is missing."
}

$runnerFile = Join-Path $root ".runner"
$serviceFile = Join-Path $root ".service"

if (-not (Test-Path -LiteralPath $runnerFile -PathType Leaf)) {
    Fail "runner_identity_missing" ".runner is missing; refusing to create or replace registration."
}
if (-not (Test-Path -LiteralPath $serviceFile -PathType Leaf)) {
    Fail "runner_service_identity_missing" ".service is missing; refusing to install a new service."
}

$runnerIdentity = try { Get-Content -LiteralPath $runnerFile -Raw | ConvertFrom-Json } catch {
    Fail "runner_identity_invalid" ".runner is not valid JSON."
}

$registeredUrl = ""
foreach ($field in @("gitHubUrl", "githubUrl", "url")) {
    if ($runnerIdentity.PSObject.Properties.Name -contains $field) {
        $candidate = [string]$runnerIdentity.$field
        if (-not [string]::IsNullOrWhiteSpace($candidate)) {
            $registeredUrl = $candidate.TrimEnd("/")
            break
        }
    }
}
if (-not $registeredUrl) {
    Fail "runner_scope_unknown" "Runner registration scope cannot be established from .runner."
}
if ($registeredUrl.ToLowerInvariant() -ne $ExpectedRepositoryUrl.TrimEnd("/").ToLowerInvariant()) {
    Fail "runner_scope_mismatch" ("Runner is registered to a different scope: " + $registeredUrl)
}

$serviceName = (Get-Content -LiteralPath $serviceFile -Raw).Trim()
if ([string]::IsNullOrWhiteSpace($serviceName)) {
    Fail "runner_service_name_missing" ".service is empty."
}

$svc = Get-CimInstance Win32_Service -ErrorAction Stop |
    Where-Object { [string]$_.Name -eq $serviceName } |
    Select-Object -First 1
if (-not $svc) {
    Fail "runner_service_missing" "Registered runner service was not found. Refusing to reinstall automatically."
}

$rootLower = $root.ToLowerInvariant()
$servicePath = [string]$svc.PathName
if ([string]::IsNullOrWhiteSpace($servicePath) -or
    -not $servicePath.ToLowerInvariant().Contains($rootLower)) {
    Fail "runner_service_path_mismatch" "Service executable is not rooted in the canonical runner directory."
}

$listenersBefore = @(Get-CimInstance Win32_Process -Filter "Name='Runner.Listener.exe'" -ErrorAction SilentlyContinue)
$canonicalBefore = @($listenersBefore | Where-Object {
    $_.ExecutablePath -and ([string]$_.ExecutablePath).ToLowerInvariant().StartsWith($rootLower)
})
$foreignBefore = @($listenersBefore | Where-Object {
    -not $_.ExecutablePath -or -not ([string]$_.ExecutablePath).ToLowerInvariant().StartsWith($rootLower)
})

$stateBefore = [string]$svc.State
$mutation = $false
$action = "inspect_only"

if (-not $InspectOnly) {
    $action = if ($stateBefore -eq "Running") { "restart_canonical_service" } else { "start_canonical_service" }
    if ($stateBefore -eq "Running") {
        Restart-Service -Name $serviceName -Force -ErrorAction Stop
    } else {
        Start-Service -Name $serviceName -ErrorAction Stop
    }
    $mutation = $true

    $deadline = (Get-Date).AddSeconds(30)
    do {
        Start-Sleep -Milliseconds 500
        $serviceNow = Get-Service -Name $serviceName -ErrorAction Stop
        if ($serviceNow.Status -eq "Running") { break }
    } while ((Get-Date) -lt $deadline)

    if ((Get-Service -Name $serviceName -ErrorAction Stop).Status -ne "Running") {
        [ordered]@{
            ok = $false
            code = "runner_service_not_running"
            action = $action
            mutation_performed = $mutation
            service = $serviceName
        } | ConvertTo-Json -Depth 5
        exit 3
    }
}

Start-Sleep -Seconds 2
$serviceAfter = Get-CimInstance Win32_Service -Filter ("Name='" + $serviceName.Replace("'","''") + "'") -ErrorAction Stop
$listenersAfter = @(Get-CimInstance Win32_Process -Filter "Name='Runner.Listener.exe'" -ErrorAction SilentlyContinue)
$canonicalAfter = @($listenersAfter | Where-Object {
    $_.ExecutablePath -and ([string]$_.ExecutablePath).ToLowerInvariant().StartsWith($rootLower)
})
$foreignAfter = @($listenersAfter | Where-Object {
    -not $_.ExecutablePath -or -not ([string]$_.ExecutablePath).ToLowerInvariant().StartsWith($rootLower)
})

$latestDiag = Get-ChildItem -LiteralPath (Join-Path $root "_diag") -Filter "Runner_*.log" -File -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTimeUtc -Descending |
    Select-Object -First 1

$diagFresh = $false
$diagListening = $false
if ($latestDiag) {
    $diagFresh = $latestDiag.LastWriteTimeUtc -gt [DateTime]::UtcNow.AddMinutes(-5)
    try {
        $tail = Get-Content -LiteralPath $latestDiag.FullName -Tail 120 -ErrorAction Stop
        $diagListening = [bool]($tail -match "Listening for Jobs|Running job|Job request")
    } catch {}
}

[ordered]@{
    ok = ([string]$serviceAfter.State -eq "Running" -and $canonicalAfter.Count -ge 1)
    code = if ([string]$serviceAfter.State -eq "Running" -and $canonicalAfter.Count -ge 1) { "runner_local_recovered" } else { "runner_local_not_ready" }
    action = $action
    mutation_performed = $mutation
    repository = $registeredUrl
    runner_name = if ($runnerIdentity.PSObject.Properties.Name -contains "agentName") { [string]$runnerIdentity.agentName } else { $null }
    service = [ordered]@{
        name = $serviceName
        before = $stateBefore
        after = [string]$serviceAfter.State
        start_mode = [string]$serviceAfter.StartMode
    }
    listeners = [ordered]@{
        canonical_before = $canonicalBefore.Count
        foreign_before = $foreignBefore.Count
        canonical_after = $canonicalAfter.Count
        foreign_after = $foreignAfter.Count
    }
    diagnostics = [ordered]@{
        latest_log_fresh = $diagFresh
        listening_signal_seen = $diagListening
    }
    next_evidence = "GitHub must claim queued ISR jobs; local listener state alone is not remote assignment proof."
} | ConvertTo-Json -Depth 7
