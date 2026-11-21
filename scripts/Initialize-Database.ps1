[CmdletBinding()]
param(
    [String] $Distribution = 'Ubuntu',
    [String] $ProjectName = 'aed4life'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$projectDirectory = Split-Path -Parent $PSScriptRoot
$previousOutputEncoding = $OutputEncoding

try {
    $OutputEncoding = [System.Text.UTF8Encoding]::new($false)

    foreach ($fileName in @('001-initial-schema.sql', '003-unique-owner-regon.sql', '004-translation-profiles.sql', '005-aed-availability.sql', '002-populate-tables.sql')) {
        $sqlPath = Join-Path $projectDirectory "database\$fileName"
        $sql = Get-Content -LiteralPath $sqlPath -Raw -Encoding UTF8
        Write-Host "Applying $fileName..."

        $sql | & wsl.exe --distribution $Distribution --cd $projectDirectory --exec docker compose `
            --project-name $ProjectName exec -T mariadb sh -c `
            'MYSQL_PWD="$MARIADB_PASSWORD" exec mariadb --default-character-set=utf8mb4 --user="$MARIADB_USER" "$MARIADB_DATABASE"'

        if ($LASTEXITCODE -ne 0) {
            throw "$fileName failed. Resolve the database error above before retrying."
        }
    }

    Write-Host 'Database initialized. Nonempty tables were preserved.'
} finally {
    $OutputEncoding = $previousOutputEncoding
}
