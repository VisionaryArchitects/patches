$ErrorActionPreference = 'Stop'
$root = 'C:\VisionaryArchitects'   # change if needed
Set-Location "$root\agents\patches"

# Health snapshot (optional)
try { nvidia-smi | Select-Object -First 3 | Out-Host } catch {}
wsl --status | Out-Host

# Run Patches (defaults to PowerShell target from patches.yaml)
py -3.11 patches.py
