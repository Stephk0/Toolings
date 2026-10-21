# Serve the Export Lab folder on http://localhost:<Port>/ without Python (Windows PowerShell 5.1+).
# Started by "Start Export Lab.bat". Close the window to stop it.
param([int]$Port = 8791, [switch]$NoBrowser)

$root = $PSScriptRoot
$types = @{
    '.html' = 'text/html; charset=utf-8'; '.js' = 'text/javascript; charset=utf-8'
    '.json' = 'application/json; charset=utf-8'; '.png' = 'image/png'
    '.glb' = 'model/gltf-binary'; '.fbx' = 'application/octet-stream'
    '.obj' = 'text/plain; charset=utf-8'; '.mtl' = 'text/plain; charset=utf-8'
}
$listener = New-Object System.Net.HttpListener
$listener.Prefixes.Add("http://localhost:$Port/")
$listener.Start()
Write-Host "Export Lab: http://localhost:$Port/  (close this window to stop)"
if (-not $NoBrowser) { Start-Process "http://localhost:$Port/" }
try {
    while ($listener.IsListening) {
        $ctx = $listener.GetContext()
        $rel = [Uri]::UnescapeDataString($ctx.Request.Url.AbsolutePath.TrimStart('/'))
        if ($rel -eq '') { $rel = 'index.html' }
        $path = [IO.Path]::GetFullPath((Join-Path $root $rel))
        $res = $ctx.Response
        if ($path.StartsWith($root) -and (Test-Path $path -PathType Leaf)) {
            $ext = [IO.Path]::GetExtension($path).ToLower()
            $res.ContentType = if ($types.ContainsKey($ext)) { $types[$ext] } else { 'application/octet-stream' }
            $bytes = [IO.File]::ReadAllBytes($path)
            $res.ContentLength64 = $bytes.Length
            $res.OutputStream.Write($bytes, 0, $bytes.Length)
        } else {
            $res.StatusCode = 404
        }
        $res.Close()
    }
} finally {
    $listener.Stop()
}
