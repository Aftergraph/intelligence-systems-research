param(
  [Parameter(Mandatory=$true)][string]$RelayConfig
)
$ErrorActionPreference = 'Stop'
jev-one relay-hub-serve $RelayConfig
exit $LASTEXITCODE
