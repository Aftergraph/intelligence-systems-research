[CmdletBinding()]
param(
    [string]$RepositoryUrl = "https://github.com/Aftergraph/intelligence-systems-research",
    [string]$RunnerDir = "C:\Aftergraph\JAR-EXP-0013\actions-runner",
    [string]$RunnerVersion = "2.337.0",
    [string]$RunnerSha256 = "1150692afa94e71f872017e254ea55b6eece1eece3fe7e3a6d4c93d0a1b85cfc",
    [string]$RunnerName = "$env:COMPUTERNAME-jar-exp-0013",
    [string]$Labels = "aftergraph-jar-exp-0013",
    [string]$WorkFolder = "_work",
    [securestring]$RegistrationToken
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Assert-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "Run this bootstrap from an elevated PowerShell session. The runner service install requires Administrator privileges."
    }
}

function ConvertFrom-SecureToken([securestring]$SecureToken) {
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureToken)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
    }
}

Assert-Administrator

if (-not $RegistrationToken) {
    $RegistrationToken = Read-Host "Paste the short-lived GitHub self-hosted runner registration token" -AsSecureString
}

if (-not $RegistrationToken -or $RegistrationToken.Length -eq 0) {
    throw "A short-lived GitHub runner registration token is required."
}

$RunnerVersion = $RunnerVersion.TrimStart("v")
$archiveName = "actions-runner-win-x64-$RunnerVersion.zip"
$downloadUrl = "https://github.com/actions/runner/releases/download/v$RunnerVersion/$archiveName"
$runnerRoot = [IO.Path]::GetFullPath($RunnerDir)
$archivePath = Join-Path ([IO.Path]::GetTempPath()) $archiveName

if (Test-Path -LiteralPath (Join-Path $runnerRoot ".runner")) {
    throw "Runner directory is already configured: $runnerRoot. Refusing to overwrite an existing runner identity."
}

New-Item -ItemType Directory -Force -Path $runnerRoot | Out-Null

Write-Host "Downloading GitHub Actions runner v$RunnerVersion..."
Invoke-WebRequest -Uri $downloadUrl -OutFile $archivePath -UseBasicParsing

$actualSha = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant()
$expectedSha = $RunnerSha256.ToLowerInvariant()
if ($actualSha -ne $expectedSha) {
    Remove-Item -LiteralPath $archivePath -Force -ErrorAction SilentlyContinue
    throw "Runner archive SHA256 mismatch. Expected $expectedSha, got $actualSha."
}

Write-Host "Runner archive verified with SHA256."
Expand-Archive -LiteralPath $archivePath -DestinationPath $runnerRoot -Force
Remove-Item -LiteralPath $archivePath -Force

$configCmd = Join-Path $runnerRoot "config.cmd"
$svcCmd = Join-Path $runnerRoot "svc.cmd"
if (-not (Test-Path -LiteralPath $configCmd)) {
    throw "config.cmd missing after runner extraction."
}
if (-not (Test-Path -LiteralPath $svcCmd)) {
    throw "svc.cmd missing after runner extraction."
}

$plainToken = ConvertFrom-SecureToken $RegistrationToken
try {
    Push-Location $runnerRoot
    try {
        & $configCmd --unattended --url $RepositoryUrl --token $plainToken --name $RunnerName --labels $Labels --work $WorkFolder --replace
        if ($LASTEXITCODE -ne 0) {
            throw "GitHub runner configuration failed with exit code $LASTEXITCODE."
        }

        & $svcCmd install
        if ($LASTEXITCODE -ne 0) {
            throw "Runner service installation failed with exit code $LASTEXITCODE."
        }

        & $svcCmd start
        if ($LASTEXITCODE -ne 0) {
            throw "Runner service start failed with exit code $LASTEXITCODE."
        }
    }
    finally {
        Pop-Location
    }
}
finally {
    $plainToken = $null
    $RegistrationToken = $null
}

Write-Host "JAR-EXP-0013 runner registered and service started."
Write-Host "Required labels: self-hosted, Windows, X64, aftergraph-jar-exp-0013"
Write-Host "Runner directory: $runnerRoot"
