#Requires -Version 7.0
<#
.SYNOPSIS
    Starts the AED4Life GUI (gui/aplikacja) on a local web server. No arguments needed.
    Picks the first free port in 8000-8020 and opens the browser.
    The GUI fetches AED data from the AED4Life WebAPI by itself.
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot 'aplikacja'))
if (-not (Test-Path -LiteralPath (Join-Path $root 'index.html'))) { throw "index.html not found in $root" }

$types = @{
    '.html' = 'text/html; charset=utf-8'; '.js' = 'text/javascript; charset=utf-8'; '.css' = 'text/css; charset=utf-8'
    '.png' = 'image/png'; '.jpg' = 'image/jpeg'; '.svg' = 'image/svg+xml'; '.json' = 'application/json'
    '.webmanifest' = 'application/manifest+json'; '.ico' = 'image/x-icon'
}

$listener = $null
foreach ($port in 8000..8020) {
    try {
        $l = [System.Net.HttpListener]::new()
        $l.Prefixes.Add("http://localhost:$port/")
        $l.Start()
        $listener = $l
        break
    } catch { }
}
if (-not $listener) { throw 'Could not start the server: ports 8000-8020 are all in use.' }

$url = "http://localhost:$port/"
Write-Host "`n  AED4Life is running at: $url" -ForegroundColor Green
Write-Host '  Press Ctrl+C to stop.' -ForegroundColor DarkGray

try {
    if ($IsWindows) { Start-Process $url }
    elseif ($IsMacOS) { & open $url }
    elseif (Get-Command xdg-open -ErrorAction SilentlyContinue) { & xdg-open $url *> $null }
} catch { }

try {
    while ($listener.IsListening) {
        $ctx = $listener.GetContext()
        try {
            $rel = [Uri]::UnescapeDataString($ctx.Request.Url.AbsolutePath.TrimStart('/'))
            if ([String]::IsNullOrEmpty($rel) -or $rel -eq 'start') { $rel = 'index.html' }
            $full = [IO.Path]::GetFullPath((Join-Path $root $rel))
            if ($full.StartsWith($root + [IO.Path]::DirectorySeparatorChar) -and (Test-Path -LiteralPath $full -PathType Leaf)) {
                $bytes = [IO.File]::ReadAllBytes($full)
                $ext = [IO.Path]::GetExtension($full).ToLowerInvariant()
                $ctx.Response.ContentType = $types.ContainsKey($ext) ? $types[$ext] : 'application/octet-stream'
                $ctx.Response.Headers.Add('Cache-Control', 'no-store')
                $ctx.Response.ContentLength64 = $bytes.Length
                $ctx.Response.OutputStream.Write($bytes, 0, $bytes.Length)
            } else {
                $ctx.Response.StatusCode = 404
            }
        } catch { } finally { $ctx.Response.Close() }
    }
} finally {
    $listener.Stop()
}
