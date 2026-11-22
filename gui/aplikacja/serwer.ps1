$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$types = @{ '.html'='text/html; charset=utf-8'; '.js'='text/javascript; charset=utf-8'; '.css'='text/css; charset=utf-8'; '.png'='image/png'; '.jpg'='image/jpeg'; '.svg'='image/svg+xml'; '.json'='application/json'; '.csv'='text/csv; charset=utf-8'; '.geojson'='application/geo+json'; '.webmanifest'='application/manifest+json'; '.ico'='image/x-icon' }
$listener = $null
foreach ($port in 8000..8020) {
  try { $l = New-Object System.Net.HttpListener; $l.Prefixes.Add("http://localhost:$port/"); $l.Start(); $listener = $l; break } catch { }
}
if (-not $listener) { Write-Host 'Nie udalo sie uruchomic serwera (porty 8000-8020 zajete).'; Read-Host 'Enter, aby zamknac'; exit 1 }
$url = "http://localhost:$port/index.html"
Write-Host ''
Write-Host '  Punkt Zycia dziala pod adresem:' -ForegroundColor Green
Write-Host "  $url" -ForegroundColor Cyan
Write-Host '  Zostaw to okno otwarte. Zamkniecie okna wylacza strone.'
Write-Host ''
Start-Process $url
try {
  while ($listener.IsListening) {
    $ctx = $listener.GetContext()
    try {
      $rel = [Uri]::UnescapeDataString($ctx.Request.Url.AbsolutePath.TrimStart('/'))
      if ([string]::IsNullOrEmpty($rel)) { $rel = 'index.html' }
      $full = [IO.Path]::GetFullPath((Join-Path $root $rel))
      if ($full.StartsWith($root) -and (Test-Path -LiteralPath $full -PathType Leaf)) {
        $bytes = [IO.File]::ReadAllBytes($full)
        $ext = [IO.Path]::GetExtension($full).ToLower()
        $ctx.Response.ContentType = $(if ($types.ContainsKey($ext)) { $types[$ext] } else { 'application/octet-stream' })
        $ctx.Response.Headers.Add('Cache-Control','no-store')
        $ctx.Response.ContentLength64 = $bytes.Length
        $ctx.Response.OutputStream.Write($bytes, 0, $bytes.Length)
      } else { $ctx.Response.StatusCode = 404 }
    } catch { } finally { $ctx.Response.Close() }
  }
} finally { $listener.Stop() }
