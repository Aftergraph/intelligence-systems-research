# ToolRush production runtime promotion

JAR-EXP-0013 promoted ToolRush (`G-TR: PASS`) for Windows file, search, shell, and RPC acceleration. Chromium remains the authoritative browser runtime.

Use `start-hermes-toolrush.ps1` as the guarded launcher. It selects ToolRush only when the frozen ToolRush revision matches, installed plugin and doctor byte-match the pinned checkout, and `doctor.py --smoke` passes. Otherwise it starts stock Hermes and records a structured fallback reason.

Kill switch:

```powershell
$env:AFTERGRAPH_TOOLRUSH_DISABLED = "1"
```

The launcher writes the latest non-secret routing decision to `%LOCALAPPDATA%\hermes\runtime-status\toolrush-runtime.json`.

Example:

```powershell
.\experiments\runtime_acceleration\start-hermes-toolrush.ps1 `
  -HermesExe "hermes" `
  -HermesPython "C:\path\to\python.exe" `
  -ToolRushRepo "C:\path\to\toolrush" `
  -ToolRushDoctor "C:\Users\empir\AppData\Local\hermes\plugins\toolrush\doctor.py" `
  -ToolRushPlugin "C:\Users\empir\AppData\Local\hermes\plugins\toolrush\__init__.py"
```

Do not silently enable an unverified runtime. Hash drift, doctor failure, revision drift, or the kill switch must select stock Hermes.
