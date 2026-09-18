param([string]$AddonName = "library_publisher")
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

# tests/ and __pycache__ have no business in a deployed addon
foreach ($junk in @("tests", "__pycache__", "core\__pycache__", "blender\__pycache__")) {
    $p = Join-Path $dest $junk
    if (Test-Path $p) { Remove-Item $p -Recurse -Force }
}

Write-Host "Deployed $AddonName to $dest - restart Blender (no hot-reload)."
Write-Host ""
Write-Host "Then point the addon at this repo folder:"
Write-Host "  Preferences > Add-ons > Library Publisher > LibraryPublisher Folder"
Write-Host "  $PSScriptRoot"
