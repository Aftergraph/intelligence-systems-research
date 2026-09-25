param(
  [Parameter(Mandatory=$true)][string]$Config
)
$ErrorActionPreference = 'Stop'
jev-one node-doctor $Config
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
jev-one node-serve $Config
exit $LASTEXITCODE
