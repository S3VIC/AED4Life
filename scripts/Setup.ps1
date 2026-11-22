#Requires -Version 7.0
<#
.SYNOPSIS
    One-step setup of the AED4Life WebAPI infrastructure (PowerShell 7: Windows, Linux, macOS).

.DESCRIPTION
    1. Creates .env with random, hash-derived passwords (existing values are kept).
    2. Starts the MariaDB container with Docker Compose and waits until it is healthy.
       Uses Docker on PATH, or Docker inside WSL when Docker is not available on Windows.
    3. Applies the SQL schema/seed scripts from .\database (safe to re-run).
    4. Stores the ConnectionStrings:AED4Life value in the WebAPI's .NET user secrets.
    5. Starts the WebAPI (skip with -NoRun).

    Run it with no arguments:  pwsh ./scripts/Setup.ps1
#>
[CmdletBinding()]
param(
    [Switch] $NoRun,
    [String] $Distribution = 'Ubuntu',
    [String] $ProjectName = 'aed4life'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $root '.env'
$apiProject = Join-Path $root 'src/AED4Life'
$script:UseWsl = $false

function Write-Step([String] $Message) { Write-Host "`n==> $Message" -ForegroundColor Cyan }

function New-Secret {
    # 32 random bytes from the OS CSPRNG, passed through SHA-256 -> 64 hex characters (URL/connection-string safe).
    $bytes = [Byte[]]::new(32)
    [System.Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
    return [Convert]::ToHexString([System.Security.Cryptography.SHA256]::HashData($bytes)).ToLowerInvariant()
}

function Initialize-DockerMode {
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        & docker info *> $null
        if ($LASTEXITCODE -eq 0) { return }
    }
    if (Get-Command wsl.exe -ErrorAction SilentlyContinue) {
        & wsl.exe --distribution $Distribution --exec docker info *> $null
        if ($LASTEXITCODE -eq 0) { $script:UseWsl = $true; return }
    }
    throw 'Docker is not available. Install and start Docker (Docker Desktop, or Docker Engine in WSL distribution ''' + $Distribution + ''') and run this script again.'
}

function Invoke-Compose([String[]] $Arguments, [String] $Stdin) {
    if ($script:UseWsl) {
        $command = { & wsl.exe --distribution $Distribution --cd $root --exec docker compose --project-name $ProjectName @Arguments }
    } else {
        $command = { & docker compose --project-name $ProjectName --project-directory $root @Arguments }
    }
    if ($PSBoundParameters.ContainsKey('Stdin')) { $Stdin | & $command } else { & $command }
    if ($LASTEXITCODE -ne 0) { throw "docker compose $($Arguments -join ' ') failed (exit code $LASTEXITCODE)." }
}

# --- prerequisites -----------------------------------------------------------------------------
Write-Step 'Checking prerequisites'
if (-not (Get-Command dotnet -ErrorAction SilentlyContinue)) {
    throw '.NET SDK 10 is required but ''dotnet'' was not found. Install it from https://dotnet.microsoft.com/download and run this script again.'
}
Initialize-DockerMode
Write-Host ("Docker: " + ($script:UseWsl ? "WSL ($Distribution)" : 'native'))

# --- .env ---------------------------------------------------------------------------------------
Write-Step 'Preparing .env'
$values = [Ordered]@{}
if (Test-Path -LiteralPath $envFile) {
    foreach ($line in Get-Content -LiteralPath $envFile) {
        if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)$') { $values[$Matches[1]] = $Matches[2] }
    }
}
$created = @()
foreach ($key in 'MARIADB_PASSWORD', 'MARIADB_ROOT_PASSWORD') {
    if (-not $values.Contains($key) -or [String]::IsNullOrWhiteSpace($values[$key])) {
        $values[$key] = New-Secret
        $created += $key
    }
}
if ($created.Count -gt 0 -or -not (Test-Path -LiteralPath $envFile)) {
    $text = (($values.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join "`n") + "`n"
    [System.IO.File]::WriteAllText($envFile, $text, [System.Text.UTF8Encoding]::new($false))
    if (-not $IsWindows) { & chmod 600 $envFile }
    Write-Host ("Wrote .env (generated: " + ($created -join ', ') + ')')
} else {
    Write-Host '.env already complete - existing credentials kept.'
}

# --- database -----------------------------------------------------------------------------------
Write-Step 'Starting MariaDB'
Invoke-Compose @('up', '-d', '--wait')

Write-Step 'Applying database scripts'
$previousEncoding = $OutputEncoding
try {
    $OutputEncoding = [System.Text.UTF8Encoding]::new($false)
    $files = Get-ChildItem -LiteralPath (Join-Path $root 'database') -Filter '*.sql' | Sort-Object Name
    # Schema first, then the incremental upgrades, and the sample-data seed (002) last.
    $ordered = @($files | Where-Object Name -Like '001-*') +
               @($files | Where-Object { $_.Name -notlike '001-*' -and $_.Name -notlike '002-*' }) +
               @($files | Where-Object Name -Like '002-*')
    foreach ($file in $ordered) {
        Write-Host "Applying $($file.Name)..."
        $sql = Get-Content -LiteralPath $file.FullName -Raw -Encoding UTF8
        try {
            Invoke-Compose @('exec', '-T', 'mariadb', 'sh', '-c',
                'MYSQL_PWD="$MARIADB_PASSWORD" exec mariadb --default-character-set=utf8mb4 --user="$MARIADB_USER" "$MARIADB_DATABASE"') -Stdin $sql
        } catch {
            throw "$($file.Name) failed. If the database volume was created with different passwords, run 'docker compose down -v' (this deletes its data) and re-run the setup. $_"
        }
    }
} finally {
    $OutputEncoding = $previousEncoding
}

# --- connection string --------------------------------------------------------------------------
Write-Step 'Configuring WebAPI connection string (.NET user secrets)'
$connectionString = "Server=127.0.0.1;Port=3306;Database=aed4life;User ID=aed4life;Password=$($values['MARIADB_PASSWORD']);"
& dotnet user-secrets set 'ConnectionStrings:AED4Life' $connectionString --project $apiProject | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'dotnet user-secrets failed.' }
Write-Host 'ConnectionStrings:AED4Life stored in user secrets.'

# --- run ----------------------------------------------------------------------------------------
Write-Step 'Setup complete'
if ($NoRun) {
    Write-Host 'Start the API later with:  dotnet run --project src/AED4Life --launch-profile https'
    return
}

try {
    & dotnet dev-certs https | Out-Null
    if ($IsWindows) { & dotnet dev-certs https --trust | Out-Null }
} catch { Write-Warning "Could not prepare the HTTPS development certificate: $_" }

Write-Host 'Starting the WebAPI:  https://localhost:7231/scalar   (Ctrl+C to stop)' -ForegroundColor Green
& dotnet run --project $apiProject --launch-profile https
