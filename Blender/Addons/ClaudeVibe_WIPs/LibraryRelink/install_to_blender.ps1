param([string]$AddonName = "library_relink")
$ErrorActionPreference = "Stop"
# find highest installed Blender userdata dir
$root = Join-Path $env:APPDATA "Blender Foundation\Blender"
$ver  = Get-ChildItem $root -Directory | Where-Object { $_.Name -match '^\d+\.\d+$' } |
        Sort-Object { [version]$_.Name } -Descending | Select-Object -First 1
if (-not $ver) { throw "No Blender userdata under $root" }
$dest = Join-Path $ver.FullName "extensions\user_default\$AddonName"
$src  = Join-Path $PSScriptRoot "source"
if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
Copy-Item $src $dest -Recurse -Force
Write-Host "Deployed $AddonName to $dest — restart Blender (no hot-reload)."
