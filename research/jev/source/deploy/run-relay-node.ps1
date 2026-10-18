param(
  [Parameter(Mandatory=$true)][string]$RelayConfig
)
$ErrorActionPreference = 'Stop'
jev-one relay-node-serve $RelayConfig
exit $LASTEXITCODE
