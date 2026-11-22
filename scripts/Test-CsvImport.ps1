#requires -Version 7.0
[CmdletBinding()]
param([String] $Distribution = 'Ubuntu')

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$projectDirectory = Split-Path -Parent $PSScriptRoot
$container = 'aed4life-import-test-' + [Guid]::NewGuid().ToString('N').Substring(0, 12)
$password = [Guid]::NewGuid().ToString('N')
$app = $null
$client = $null
$created = $false
$previousOutputEncoding = $OutputEncoding

function Assert([Boolean] $Condition, [String] $Message) {
    if (-not $Condition) { throw $Message }
}

function Invoke-TestSql([String] $Sql) {
    $result = $Sql | & wsl.exe --distribution $Distribution --exec docker exec -i $container sh -c `
        'MYSQL_PWD="$MARIADB_ROOT_PASSWORD" exec mariadb --default-character-set=utf8mb4 --batch --skip-column-names --user=root checks'
    if ($LASTEXITCODE -ne 0) { throw 'Test SQL failed.' }
    return ($result -join "`n")
}

function Get-DataSnapshot {
    return Invoke-TestSql ((@('Cities', 'Streets', 'PostalCodes', 'Addresses', 'AEDOwners', 'AEDs') |
        ForEach-Object { "SELECT * FROM ``$_`` ORDER BY Id;" }) -join "`n")
}

function New-TestProfile([String] $Name, [Object[]] $Mappings) {
    $units = foreach ($mapping in $Mappings) {
        @{ fromColumn = $mapping[0]; fromType = $mapping[1]; toColumn = $mapping[2]; toType = $mapping[3] }
    }
    $body = @{ name = $Name; transporter = @{ transporterUnits = @($units) } } | ConvertTo-Json -Depth 6
    return Invoke-RestMethod "$base/api/translations/profiles" -Method Post `
        -ContentType 'application/json; charset=utf-8' -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
}

function Invoke-Import([String] $Name, [String] $Csv, [Int32] $ExpectedStatus = 200,
    [String] $FileName = 'input.csv', [Byte[]] $Bytes = $null) {
    if ($null -eq $Bytes) { $Bytes = [System.Text.Encoding]::UTF8.GetBytes($Csv) }
    $form = [System.Net.Http.MultipartFormDataContent]::new()
    try {
        $content = [System.Net.Http.ByteArrayContent]::new($Bytes)
        $content.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::new('text/csv')
        $form.Add($content, 'file', $FileName)
        $response = $client.PostAsync("$base/api/translations/profiles($([Uri]::EscapeDataString($Name)))/import", $form).GetAwaiter().GetResult()
        try {
            $body = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
            Assert ([Int32] $response.StatusCode -eq $ExpectedStatus) "Expected $ExpectedStatus, received $([Int32] $response.StatusCode): $body"
            return $body | ConvertFrom-Json
        } finally {
            $response.Dispose()
        }
    } finally {
        $form.Dispose()
    }
}

function Invoke-Nearest([String] $Query, [Int32] $ExpectedStatus = 200) {
    $response = $client.GetAsync("$base/api/aed/nearest?$Query").GetAwaiter().GetResult()
    try {
        $body = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
        Assert ([Int32] $response.StatusCode -eq $ExpectedStatus) "Expected $ExpectedStatus, received $([Int32] $response.StatusCode): $body"
        if ($ExpectedStatus -eq 200) { return $body | ConvertFrom-Json }
        return $body
    } finally { $response.Dispose() }
}

try {
    $OutputEncoding = [System.Text.UTF8Encoding]::new($false)
    dotnet build (Join-Path $projectDirectory 'src\AED4Life.slnx') --nologo --verbosity quiet
    Assert ($LASTEXITCODE -eq 0) 'Application build failed.'
    & wsl.exe --distribution $Distribution --exec docker run --detach --name $container --publish '127.0.0.1::3306' `
        --env "MARIADB_ROOT_PASSWORD=$password" --env MARIADB_DATABASE=checks mariadb:12.3.3 | Out-Null
    Assert ($LASTEXITCODE -eq 0) 'Could not start the isolated MariaDB container.'
    $created = $true
    $ready = $false
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        & wsl.exe --distribution $Distribution --exec docker exec $container healthcheck.sh --connect --innodb_initialized *> $null
        if ($LASTEXITCODE -eq 0) { $ready = $true; break }
        Start-Sleep -Seconds 1
    }
    Assert $ready 'MariaDB did not become ready.'
    foreach ($sqlFile in Get-ChildItem (Join-Path $projectDirectory 'database') -Filter '*.sql' | Sort-Object Name) {
        Invoke-TestSql (Get-Content -LiteralPath $sqlFile.FullName -Raw -Encoding UTF8) | Out-Null
    }
    $before = Get-DataSnapshot
    Invoke-TestSql @'
ALTER TABLE Cities MODIFY COLUMN Name LONGTEXT NOT NULL;
ALTER TABLE Streets MODIFY COLUMN Name LONGTEXT NOT NULL;
ALTER TABLE PostalCodes MODIFY COLUMN Code VARCHAR(6) NOT NULL;
ALTER TABLE Addresses MODIFY COLUMN StreetId BIGINT NOT NULL, MODIFY COLUMN CityId BIGINT NOT NULL,
    MODIFY COLUMN PostalCodeId INT NOT NULL, MODIFY COLUMN BuildingNumber INT NOT NULL;
ALTER TABLE AEDOwners MODIFY COLUMN RegonNumber VARCHAR(14) NOT NULL, MODIFY COLUMN IsPublic TINYINT(1) NOT NULL,
    MODIFY COLUMN Name LONGTEXT NOT NULL, MODIFY COLUMN CityId BIGINT NOT NULL, MODIFY COLUMN StreetId BIGINT NOT NULL;
ALTER TABLE AEDs MODIFY COLUMN AddressId BIGINT NOT NULL, MODIFY COLUMN SerialNumber LONGTEXT NOT NULL,
    MODIFY COLUMN Rating INT NOT NULL DEFAULT 0;
'@ | Out-Null
    $nullableUpgrade = Get-Content -LiteralPath (Join-Path $projectDirectory 'database\007-nullable-import-data.sql') -Raw -Encoding UTF8
    Invoke-TestSql ($nullableUpgrade + "`n" + $nullableUpgrade) | Out-Null
    Assert ((Get-DataSnapshot) -ceq $before) 'Nullable upgrade did not preserve existing data from the old nonnullable schema.'
    $ownerUpgrade = Get-Content -LiteralPath (Join-Path $projectDirectory 'database\008-aed-owner.sql') -Raw -Encoding UTF8
    Invoke-TestSql @"
CREATE DATABASE checks_owner_upgrade;
CREATE TABLE checks_owner_upgrade.AEDOwners LIKE AEDOwners;
INSERT INTO checks_owner_upgrade.AEDOwners SELECT * FROM AEDOwners;
CREATE TABLE checks_owner_upgrade.AEDs LIKE AEDs;
INSERT INTO checks_owner_upgrade.AEDs SELECT * FROM AEDs;
ALTER TABLE checks_owner_upgrade.AEDs DROP INDEX IX_AEDs_OwnerId, DROP COLUMN OwnerId;
USE checks_owner_upgrade;
$ownerUpgrade
$ownerUpgrade
"@ | Out-Null
    Assert ((Invoke-TestSql 'SELECT COUNT(*) FROM checks_owner_upgrade.AEDs WHERE OwnerId IS NULL;') -eq '6') 'Owner upgrade guessed ownership or lost existing AEDs.'
    Assert ((Invoke-TestSql @'
SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='checks'
AND TABLE_NAME IN ('Cities','Streets','PostalCodes','Addresses','AEDOwners','AEDs')
AND COLUMN_NAME NOT IN ('Id','Created','LastUpdated') AND IS_NULLABLE='NO';
'@) -eq '0') 'Nullable upgrade left old required business-data columns in place.'
    Assert ((Invoke-TestSql 'SELECT COUNT(*) FROM AEDs WHERE Latitude BETWEEN -90 AND 90 AND Longitude BETWEEN -180 AND 180;') -eq '6') 'Dummy AED coordinates are missing or invalid.'
    $upgradeSql = Get-Content -LiteralPath (Join-Path $projectDirectory 'database\006-aed-coordinates.sql') -Raw -Encoding UTF8
    Invoke-TestSql @"
CREATE DATABASE checks_coordinates_upgrade;
CREATE TABLE checks_coordinates_upgrade.AEDs LIKE AEDs;
INSERT INTO checks_coordinates_upgrade.AEDs SELECT * FROM AEDs;
ALTER TABLE checks_coordinates_upgrade.AEDs
    DROP CONSTRAINT CK_AEDs_Latitude, DROP CONSTRAINT CK_AEDs_Longitude,
    DROP COLUMN Latitude, DROP COLUMN Longitude;
USE checks_coordinates_upgrade;
$upgradeSql
$upgradeSql
"@ | Out-Null
    Assert ((Invoke-TestSql @'
SELECT COUNT(*) FROM checks_coordinates_upgrade.AEDs u JOIN AEDs a ON u.Id=a.Id
WHERE u.SerialNumber=a.SerialNumber AND u.AddressId=a.AddressId AND u.Created=a.Created
AND u.Rating=a.Rating AND u.Latitude IS NULL AND u.Longitude IS NULL;
'@) -eq '6') 'Coordinate upgrade did not preserve existing AEDs with unknown coordinates.'
    $rejected = Invoke-TestSql @'
SET @RejectedCoordinates = 0;
DELIMITER //
BEGIN NOT ATOMIC
    DECLARE CONTINUE HANDLER FOR 4025 SET @RejectedCoordinates = @RejectedCoordinates + 1;
    UPDATE AEDs SET Latitude=91 WHERE SerialNumber='AED-7F3A9C21';
    UPDATE AEDs SET Longitude=-181 WHERE SerialNumber='AED-7F3A9C21';
END//
DELIMITER ;
SELECT @RejectedCoordinates;
'@
    Assert ($rejected -eq '2') 'SQL did not enforce coordinate ranges.'
    Write-Host 'PASS: Dummy coordinates, repeatable legacy-table upgrade, and SQL coordinate range constraints.'
    $binding = (& wsl.exe --distribution $Distribution --exec docker port $container 3306).Trim()
    $databasePort = $binding.Split(':')[-1]
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
    $listener.Start()
    $port = $listener.LocalEndpoint.Port
    $listener.Stop()
    $base = "http://127.0.0.1:$port"
    $start = [System.Diagnostics.ProcessStartInfo]::new('dotnet')
    $start.ArgumentList.Add((Join-Path $projectDirectory 'src\AED4Life\bin\Debug\net10.0\AED4Life.dll'))
    $start.ArgumentList.Add('--urls')
    $start.ArgumentList.Add($base)
    $start.Environment['ASPNETCORE_ENVIRONMENT'] = 'Development'
    $start.Environment['ConnectionStrings__AED4Life'] = "Server=127.0.0.1;Port=$databasePort;User ID=root;Password=$password;Database=checks;Pooling=false;"
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    $app = [System.Diagnostics.Process]::Start($start)
    $appOutput = $app.StandardOutput.ReadToEndAsync()
    $appErrors = $app.StandardError.ReadToEndAsync()
    $client = [System.Net.Http.HttpClient]::new()
    $client.Timeout = [TimeSpan]::FromSeconds(30)
    $ready = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        if ($app.HasExited) { throw "API exited: $($appOutput.Result) $($appErrors.Result)" }
        try {
            Invoke-RestMethod "$base/api/translations/profiles" | Out-Null
            $ready = $true
            break
        } catch [System.Net.Http.HttpRequestException] {
            Start-Sleep -Milliseconds 500
        }
    }
    Assert $ready 'API did not become ready.'

    $mappings = @(
        @('city', 'STRING', 'Cities.Name', 'STRING'),
        @('street', 'STRING', 'Streets.Name', 'STRING'),
        @('postal', 'STRING', 'PostalCodes.Code', 'STRING'),
        @('building', 'DOUBLE', 'Addresses.BuildingNumber', 'INTEGER'),
        @('serial', 'STRING', 'AEDs.SerialNumber', 'STRING'),
        @('access', 'INTEGER', 'AEDs.Access', 'INTEGER'),
        @('start', 'INTEGER', 'AEDs.AvailabilityStartHour', 'INTEGER'),
        @('end', 'INTEGER', 'AEDs.AvailabilityEndHour', 'INTEGER'),
        @('rating', 'INTEGER', 'AEDs.Rating', 'INTEGER'),
        @('regon', 'STRING', 'AEDOwners.RegonNumber', 'STRING'),
        @('owner', 'STRING', 'AEDOwners.Name', 'STRING'),
        @('public', 'BOOLEAN', 'AEDOwners.IsPublic', 'BOOLEAN')
    )
    New-TestProfile 'Linked import' $mappings | Out-Null
    $csv = @'
city,street,postal,building,serial,access,start,end,rating,regon,owner,public
"Import City, North","Main ""Test"" Street",00-901,10.0,IMPORT-001,0,0,24,1,000001234,"School
North",true
'@
    $result = Invoke-Import 'lInKeD iMpOrT' ([String][Char]0xFEFF + $csv)
    Assert ($result.rowsProcessed -eq 1) 'Incorrect processed-row count.'
    foreach ($table in @('Cities', 'Streets', 'PostalCodes', 'Addresses', 'AEDOwners', 'AEDs')) {
        Assert ($result.tables.$table.inserted -eq 1 -and $result.tables.$table.updated -eq 0) "Incorrect insert counts for $table."
    }
    $related = Invoke-TestSql @'
SELECT COUNT(*) FROM AEDs a JOIN Addresses d ON a.AddressId=d.Id
JOIN Cities c ON d.CityId=c.Id JOIN Streets s ON d.StreetId=s.Id JOIN PostalCodes p ON d.PostalCodeId=p.Id
JOIN AEDOwners o ON a.OwnerId=o.Id
WHERE a.SerialNumber='IMPORT-001' AND c.Name='Import City, North' AND s.Name='Main "Test" Street'
AND p.Code='00-901' AND d.BuildingNumber=10 AND o.RegonNumber='000001234' AND o.IsPublic=1
AND o.Name LIKE 'School%North' AND a.Access=0 AND a.Rating=1 AND a.AvailabilityEndHour=24;
'@
    Assert ($related -eq '1') 'Imported relationships, quoted values, leading zeros, or typed values are incorrect.'
    $before = Get-DataSnapshot
    $result = Invoke-Import 'Linked import' $csv
    Assert ((Get-DataSnapshot) -ceq $before) 'Identical reimport changed stored data.'
    foreach ($table in $result.tables.PSObject.Properties) {
        Assert ($table.Value.inserted -eq 0 -and $table.Value.updated -eq 0) 'Identical reimport reported changes.'
    }
    Write-Host 'PASS: Typed multi-table insert, links, UTF-8 BOM, CSV quoting/newlines, and idempotent reimport.'

    New-TestProfile 'Owner update' @(
        @('regon', 'STRING', 'AEDOwners.RegonNumber', 'STRING'),
        @('owner', 'STRING', 'AEDOwners.Name', 'STRING')
    ) | Out-Null
    $result = Invoke-Import 'Owner update' "regon,owner`n000001234,Renamed school"
    Assert ($result.tables.AEDOwners.updated -eq 1) 'Existing owner was not updated.'
    Assert ((Invoke-TestSql "SELECT COUNT(*) FROM AEDOwners WHERE RegonNumber='000001234' AND Name='Renamed school' AND IsPublic=1 AND CityId>0 AND StreetId>0;") -eq '1') 'Unmapped owner fields were not preserved.'
    $before = Get-DataSnapshot
    $invalidLaterRow = @'
city,street,postal,building,serial,access,start,end,rating,regon,owner,public
Rollback City,Rollback Street,00-902,30,IMPORT-001,1,,,0,000001234,Must roll back,false
Other City,Other Street,00-903,10.5,IMPORT-BAD,1,,,0,000009999,Invalid row,true
'@
    $failure = Invoke-Import 'Linked import' $invalidLaterRow 400
    Assert ($null -ne $failure.errors.'rows[3].Addresses.BuildingNumber') 'Numeric conversion error lacks row/column context.'
    Assert ((Get-DataSnapshot) -ceq $before) 'A later-row failure did not roll back earlier inserts and updates.'
    Write-Host 'PASS: Natural-key updates preserve unmapped fields; later-row errors roll back the entire file.'

    New-TestProfile 'AED update' @(
        @('serial', 'STRING', 'AEDs.SerialNumber', 'STRING'),
        @('rating', 'STRING', 'AEDs.Rating', 'INTEGER'),
        @('access', 'INTEGER', 'AEDs.Access', 'INTEGER'),
        @('start', 'INTEGER', 'AEDs.AvailabilityStartHour', 'INTEGER'),
        @('end', 'INTEGER', 'AEDs.AvailabilityEndHour', 'INTEGER')
    ) | Out-Null
    $createdBefore = Invoke-TestSql "SELECT Created FROM AEDs WHERE SerialNumber='IMPORT-001';"
    $result = Invoke-Import 'AED update' "serial,rating,access,start,end`nIMPORT-001,0,,,"
    Assert ($result.tables.AEDs.updated -eq 1) 'Existing AED was not updated.'
    Assert ((Invoke-TestSql "SELECT COUNT(*) FROM AEDs WHERE SerialNumber='IMPORT-001' AND Rating=0 AND Access IS NULL AND AvailabilityStartHour IS NULL AND AvailabilityEndHour IS NULL;") -eq '1') 'Nullable fields did not become NULL.'
    Assert ((Invoke-TestSql "SELECT Created FROM AEDs WHERE SerialNumber='IMPORT-001';") -ceq $createdBefore) 'AED Created timestamp was overwritten.'
    $before = Get-DataSnapshot
    Invoke-Import 'AED update' "serial,rating,access,start,end`nIMPORT-001,1,,0,0" 400 | Out-Null
    Assert ((Get-DataSnapshot) -ceq $before) 'Invalid availability hours changed existing records.'
    Invoke-Import 'Owner update' "regon,owner`n000009999,Unknown location" | Out-Null
    Assert ((Invoke-TestSql "SELECT COUNT(*) FROM AEDOwners WHERE RegonNumber='000009999' AND Name='Unknown location' AND CityId IS NULL AND StreetId IS NULL AND IsPublic IS NULL;") -eq '1') 'Missing optional owner data did not become NULL.'
    $before = Get-DataSnapshot

    New-TestProfile 'Foreign keys' @(
        @('regon', 'STRING', 'AEDOwners.RegonNumber', 'STRING'),
        @('owner', 'STRING', 'AEDOwners.Name', 'STRING'),
        @('public', 'BOOLEAN', 'AEDOwners.IsPublic', 'BOOLEAN'),
        @('city', 'INTEGER', 'AEDOwners.CityId', 'INTEGER'),
        @('street', 'INTEGER', 'AEDOwners.StreetId', 'INTEGER')
    ) | Out-Null
    Invoke-Import 'Foreign keys' "regon,owner,public,city,street`n000001234,Must roll back,false,1,1`n000001235,Invalid references,true,999999,999999" 409 | Out-Null
    Assert ((Get-DataSnapshot) -ceq $before) 'Foreign-key conflict did not roll back earlier updates.'

    Invoke-Import 'Linked import' "city,street`nExample,Street" 400 | Out-Null
    Invoke-Import 'Linked import' "city,city`nA,B" 400 | Out-Null
    Invoke-Import 'Linked import' ($csv.Split("`n")[0]) 400 | Out-Null
    Invoke-Import 'Linked import' '' 400 | Out-Null
    Invoke-Import 'Linked import' "city,street`nA" 400 | Out-Null
    Invoke-Import 'Linked import' $csv 415 'input.json' | Out-Null
    Invoke-Import 'Unknown profile' $csv 404 | Out-Null
    Invoke-Import 'Linked import' '' 400 'input.csv' ([Byte[]]@(0xFF, 0xFE)) | Out-Null
    Invoke-Import 'Owner update' "regon,owner`n000001234,Valid first row`n000001235,`"Unclosed" 400 | Out-Null
    Assert ((Get-DataSnapshot) -ceq $before) 'Malformed CSV changed stored data.'
    Write-Host 'PASS: Nullable values, field preservation, required columns, constraints, encoding, headers, malformed CSV, and error responses.'

    New-TestProfile 'Minimal AED' @(
        @('city', 'STRING', 'Cities.Name', 'STRING'),
        @('street', 'STRING', 'Streets.Name', 'STRING'),
        @('postal', 'STRING', 'PostalCodes.Code', 'STRING'),
        @('building', 'INTEGER', 'Addresses.BuildingNumber', 'INTEGER'),
        @('serial', 'STRING', 'AEDs.SerialNumber', 'STRING')
    ) | Out-Null
    Invoke-Import 'Minimal AED' "city,street,postal,building,serial`nMinimal City,Minimal Street,00-905,1,IMPORT-MINIMAL" | Out-Null
    Assert ((Invoke-TestSql "SELECT COUNT(*) FROM AEDs WHERE SerialNumber='IMPORT-MINIMAL' AND Rating IS NULL AND Access IS NULL AND Latitude IS NULL AND Longitude IS NULL AND Created>=CURRENT_DATE AND LastUpdated>=CURRENT_DATE;") -eq '1') 'Default AED fields were not supplied.'
    New-TestProfile 'GPS update' @(
        @('serial', 'STRING', 'AEDs.SerialNumber', 'STRING'),
        @('latitude', 'DOUBLE', 'AEDs.Latitude', 'DOUBLE'),
        @('longitude', 'STRING', 'AEDs.Longitude', 'DOUBLE')
    ) | Out-Null
    Invoke-Import 'GPS update' "serial,latitude,longitude`nIMPORT-001,-33.868820,151.209296" | Out-Null
    Assert ((Invoke-TestSql "SELECT COUNT(*) FROM AEDs WHERE SerialNumber='IMPORT-001' AND ABS(Latitude+33.868820)<0.000000001 AND ABS(Longitude-151.209296)<0.000000001;") -eq '1') 'Double GPS coordinates lost precision or were not persisted.'
    Invoke-Import 'GPS update' "serial,latitude,longitude`nIMPORT-001,-90,-180`nIMPORT-MINIMAL,90,180" | Out-Null
    Assert ((Invoke-TestSql "SELECT COUNT(*) FROM AEDs WHERE (SerialNumber='IMPORT-001' AND Latitude=-90 AND Longitude=-180) OR (SerialNumber='IMPORT-MINIMAL' AND Latitude=90 AND Longitude=180);") -eq '2') 'Coordinate boundary values were rejected.'
    $before = Get-DataSnapshot
    $failure = Invoke-Import 'GPS update' "serial,latitude,longitude`nIMPORT-001,0,0`nIMPORT-MINIMAL,90.000001,180" 400
    Assert ($null -ne $failure.errors.'rows[3].AEDs.Latitude') 'Invalid latitude lacks row/column context.'
    Invoke-Import 'GPS update' "serial,latitude,longitude`nIMPORT-001,0,180.000001" 400 | Out-Null
    Invoke-Import 'GPS update' "serial,latitude,longitude`nIMPORT-001,NaN,0" 400 | Out-Null
    Invoke-Import 'GPS update' "serial,latitude,longitude`nIMPORT-001,0,Infinity" 400 | Out-Null
    Assert ((Get-DataSnapshot) -ceq $before) 'Invalid GPS data did not roll back coordinate updates.'
    Invoke-Import 'GPS update' "serial,latitude,longitude`nIMPORT-001,," | Out-Null
    Assert ((Invoke-TestSql "SELECT COUNT(*) FROM AEDs WHERE SerialNumber='IMPORT-001' AND Latitude IS NULL AND Longitude IS NULL;") -eq '1') 'Empty GPS fields did not become NULL.'
    Write-Host 'PASS: GPS double conversion/precision, inclusive bounds, nonfinite/range rejection, NULLs, and full rollback.'
    $before = Get-DataSnapshot
    New-TestProfile 'Explicit link' @(
        @('city', 'STRING', 'Cities.Name', 'STRING'),
        @('city_id', 'INTEGER', 'Addresses.CityId', 'INTEGER'),
        @('street_id', 'INTEGER', 'Addresses.StreetId', 'INTEGER'),
        @('postal_id', 'INTEGER', 'Addresses.PostalCodeId', 'INTEGER'),
        @('building', 'INTEGER', 'Addresses.BuildingNumber', 'INTEGER')
    ) | Out-Null
    Invoke-Import 'Explicit link' "city,city_id,street_id,postal_id,building`nConflicting City,1,1,1,1" 400 | Out-Null
    Assert ((Get-DataSnapshot) -ceq $before) 'A conflicting explicit foreign key did not roll back inferred lookup records.'

    $concurrentForms = @()
    $requests = @()
    try {
        for ($index = 0; $index -lt 2; $index++) {
            $form = [System.Net.Http.MultipartFormDataContent]::new()
            $content = [System.Net.Http.ByteArrayContent]::new([System.Text.Encoding]::UTF8.GetBytes(
                "city,street,postal,building,serial`nConcurrent City,Concurrent Street,00-906,1,IMPORT-CONCURRENT"))
            $form.Add($content, 'file', 'concurrent.csv')
            $concurrentForms += $form
            $requests += $client.PostAsync("$base/api/translations/profiles(Minimal%20AED)/import", $form)
        }
        $successes = 0
        foreach ($request in $requests) {
            $response = $request.GetAwaiter().GetResult()
            try {
                $body = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
                Assert ([Int32] $response.StatusCode -in @(200, 409)) "Concurrent import returned $([Int32] $response.StatusCode): $body"
                if ([Int32] $response.StatusCode -eq 200) { $successes++ }
            } finally { $response.Dispose() }
        }
        Assert ($successes -ge 1) 'No concurrent import succeeded.'
        Assert ((Invoke-TestSql "SELECT COUNT(*) FROM AEDs WHERE SerialNumber='IMPORT-CONCURRENT';") -eq '1') 'Concurrent imports created duplicate AEDs.'
        Assert ((Invoke-TestSql "SELECT COUNT(*) FROM Cities WHERE Name='Concurrent City';") -eq '1') 'Concurrent imports created duplicate natural keys.'
    } finally {
        foreach ($form in $concurrentForms) { $form.Dispose() }
    }
    Write-Host 'PASS: New-AED defaults, explicit/inferred key conflicts, and serializable concurrent upserts.'

    New-TestProfile 'Forbidden target' (,@('name', 'STRING', 'TranslationProfiles.Name', 'STRING')) | Out-Null
    Invoke-Import 'Forbidden target' "name`nDisallowed" 400 | Out-Null
    New-TestProfile 'Generated ID' (,@('id', 'INTEGER', 'Cities.Id', 'INTEGER')) | Out-Null
    Invoke-Import 'Generated ID' "id`n1" 400 | Out-Null
    New-TestProfile 'Duplicate destination' @(
        @('a', 'STRING', 'Cities.Name', 'STRING'),
        @('b', 'STRING', 'Cities.Name', 'STRING')
    ) | Out-Null
    Invoke-Import 'Duplicate destination' "a,b`nOne,Two" 400 | Out-Null
    Invoke-TestSql "INSERT INTO Cities (Name) VALUES ('Ambiguous import key'), ('Ambiguous import key');" | Out-Null
    New-TestProfile 'Ambiguous key' (,@('name', 'STRING', 'Cities.Name', 'STRING')) | Out-Null
    Invoke-Import 'Ambiguous key' "name`nAmbiguous import key" 400 | Out-Null

    New-TestProfile 'openaedmap-2' @(
        @('addr:city', 'STRING', 'Cities.Name', 'STRING'),
        @('addr:street', 'STRING', 'Streets.Name', 'STRING'),
        @('addr:postcode', 'STRING', 'PostalCodes.Code', 'STRING'),
        @('lat', 'DOUBLE', 'AEDs.Latitude', 'DOUBLE'),
        @('lon', 'DOUBLE', 'AEDs.Longitude', 'DOUBLE'),
        @('operator', 'STRING', 'AEDOwners.Name', 'STRING')
    ) | Out-Null
    $openAedCsv = "addr:city,addr:street,addr:postcode,lat,lon,operator`nOpenAED City,OpenAED Street,00-981,52.123456,21.123456,OpenAED Operator"
    $result = Invoke-Import 'openaedmap-2' $openAedCsv
    Assert ($result.tables.AEDs.inserted -eq 1 -and $result.tables.Addresses.inserted -eq 1 -and $result.tables.AEDOwners.inserted -eq 1) 'The exact OpenAEDMap profile did not create its inferred records.'
    Assert ((Invoke-TestSql @'
SELECT COUNT(*) FROM AEDs a JOIN Addresses d ON a.AddressId=d.Id
JOIN Cities c ON d.CityId=c.Id JOIN Streets s ON d.StreetId=s.Id JOIN PostalCodes p ON d.PostalCodeId=p.Id
JOIN AEDOwners o ON a.OwnerId=o.Id
WHERE c.Name='OpenAED City' AND s.Name='OpenAED Street' AND p.Code='00-981'
AND d.BuildingNumber IS NULL AND a.SerialNumber IS NULL AND a.Rating IS NULL
AND o.Name='OpenAED Operator' AND o.RegonNumber IS NULL AND o.IsPublic IS NULL;
'@) -eq '1') 'Sparse OpenAEDMap relationships or nullable values are incorrect.'
    $before = Get-DataSnapshot
    $result = Invoke-Import 'openaedmap-2' $openAedCsv
    Assert ((Get-DataSnapshot) -ceq $before) 'Fallback-key reimport changed or duplicated existing records.'
    Assert ($result.tables.AEDs.inserted -eq 0 -and $result.tables.AEDOwners.inserted -eq 0) 'Fallback keys did not match existing records.'
    Invoke-Import 'openaedmap-2' ($openAedCsv.Replace('OpenAED Operator', '')) | Out-Null
    Assert ((Invoke-TestSql "SELECT COUNT(*) FROM AEDs a JOIN Addresses d ON a.AddressId=d.Id JOIN Cities c ON d.CityId=c.Id WHERE c.Name='OpenAED City' AND a.OwnerId IS NULL;") -eq '1') 'An empty mapped operator did not clear the AED owner link.'
    Invoke-Import 'openaedmap-2' $openAedCsv | Out-Null
    Invoke-Import 'openaedmap-2' ($openAedCsv.Replace('OpenAED City,', 'Another OpenAED City,')) | Out-Null
    Assert ((Invoke-TestSql "SELECT COUNT(*) FROM AEDOwners WHERE Name='OpenAED Operator' AND RegonNumber IS NULL;") -eq '2') 'Owner fallback matching merged different locations.'
    Assert ((Invoke-TestSql "SELECT COUNT(*) FROM AEDs WHERE SerialNumber IS NULL AND ABS(Latitude-52.123456)<0.000000001 AND ABS(Longitude-21.123456)<0.000000001;") -eq '2') 'AED fallback matching ignored the address.'
    $nullCsv = @'
addr:city,addr:street,addr:postcode,lat,lon,operator
,,,,,
null, \N, ,NULL,\N,NuLl
Partial OpenAED City,\N,NULL, ,21.5,Partial OpenAED Operator
'@
    $result = Invoke-Import 'openaedmap-2' $nullCsv
    Assert ($result.rowsProcessed -eq 3 -and $result.tables.AEDs.inserted -eq 3) 'Null-heavy CSV rows were not imported.'
    Assert ($result.tables.Cities.inserted -eq 1 -and $result.tables.Streets.inserted -eq 0 -and $result.tables.PostalCodes.inserted -eq 0) 'Empty lookup cells created unnamed lookup records.'
    Assert ($result.tables.AEDOwners.inserted -eq 1 -and $result.tables.Addresses.inserted -eq 1) 'Wholly empty owners or addresses were created.'
    Assert ((Invoke-TestSql @'
SELECT COUNT(*) FROM AEDs a JOIN Addresses d ON a.AddressId=d.Id JOIN Cities c ON d.CityId=c.Id
WHERE c.Name='Partial OpenAED City' AND d.StreetId IS NULL AND d.PostalCodeId IS NULL AND d.BuildingNumber IS NULL
AND a.SerialNumber IS NULL AND a.Latitude IS NULL AND a.Longitude=21.5;
'@) -eq '1') 'Partial address or numeric NULL values were not stored correctly.'
    Assert ((Invoke-TestSql 'SELECT COUNT(*) FROM AEDs WHERE SerialNumber IS NULL AND AddressId IS NULL AND Latitude IS NULL AND Longitude IS NULL AND Rating IS NULL;') -eq '2') 'Anonymous rows should contain NULLs, not invented identifiers.'
    $result = Invoke-Import 'openaedmap-2' $nullCsv
    Assert ($result.tables.AEDs.inserted -eq 3 -and $result.tables.AEDOwners.inserted -eq 0) 'Records without a reliable AED identity were incorrectly merged.'

    Invoke-Import 'Foreign keys' "regon,owner,public,city,street`n000001234,NULL,\N, ,NULL" | Out-Null
    $owners = Invoke-RestMethod "$base/api/aed/owners"
    $nullableOwner = @($owners | Where-Object regonNumber -eq '000001234')
    Assert ($nullableOwner.Count -eq 1) 'Owner API hid a record with unknown location.'
    Assert ($null -eq $nullableOwner[0].name -and $null -eq $nullableOwner[0].isPublic -and $null -eq $nullableOwner[0].cityName -and $null -eq $nullableOwner[0].streetName) 'Owner API did not return nullable fields as NULL.'
    Invoke-Import 'AED update' "serial,rating,access,start,end`nIMPORT-001,NULL,\N,7," | Out-Null
    Assert ((Invoke-TestSql "SELECT COUNT(*) FROM AEDs WHERE SerialNumber='IMPORT-001' AND Rating IS NULL AND Access IS NULL AND AvailabilityStartHour=7 AND AvailabilityEndHour IS NULL;") -eq '1') 'Independent unknown availability hours were rejected.'
    New-TestProfile 'Optional timestamps' @(
        @('serial', 'STRING', 'AEDs.SerialNumber', 'STRING'),
        @('created', 'STRING', 'AEDs.Created', 'STRING'),
        @('updated', 'STRING', 'AEDs.LastUpdated', 'STRING')
    ) | Out-Null
    Invoke-Import 'Optional timestamps' "serial,created,updated`nIMPORT-TIMESTAMPS,NULL,\N" | Out-Null
    Assert ((Invoke-TestSql "SELECT COUNT(*) FROM AEDs WHERE SerialNumber='IMPORT-TIMESTAMPS' AND Created>=CURRENT_DATE AND LastUpdated>=CURRENT_DATE;") -eq '1') 'Unknown operational timestamps were not generated.'
    $before = Get-DataSnapshot
    foreach ($sqlFile in Get-ChildItem (Join-Path $projectDirectory 'database') -Filter '*.sql' | Sort-Object Name) {
        Invoke-TestSql (Get-Content -LiteralPath $sqlFile.FullName -Raw -Encoding UTF8) | Out-Null
    }
    Assert ((Get-DataSnapshot) -ceq $before) 'Reinitialization failed to preserve NULL data and partial hours.'
    Assert ((Invoke-TestSql @'
SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='checks'
AND TABLE_NAME IN ('Cities','Streets','PostalCodes','Addresses','AEDOwners','AEDs')
AND COLUMN_NAME NOT IN ('Id','Created','LastUpdated') AND IS_NULLABLE='NO';
'@) -eq '0') 'An imported business-data column is still nonnullable.'
    Write-Host 'PASS: Exact OpenAEDMap profile, partial inferred addresses, fallback identity, NULL tokens, sparse owners/API results, optional hours, and upgrade reruns.'

    $warsawHour = [TimeZoneInfo]::ConvertTime([DateTimeOffset]::UtcNow, [TimeZoneInfo]::FindSystemTimeZoneById('Europe/Warsaw')).Hour
    $closedStart = ($warsawHour + 12) % 24
    $closedEnd = ($warsawHour + 13) % 24
    Invoke-TestSql @"
UPDATE AEDs SET Access=2;
INSERT INTO Cities (Name) VALUES ('Nearest City'); SET @City=LAST_INSERT_ID();
INSERT INTO Streets (Name) VALUES ('Nearest Street'); SET @Street=LAST_INSERT_ID();
INSERT INTO PostalCodes (Code) VALUES ('00-999'); SET @Postal=LAST_INSERT_ID();
INSERT INTO Addresses (CityId,StreetId,PostalCodeId,BuildingNumber) VALUES (@City,@Street,@Postal,10); SET @Address=LAST_INSERT_ID();
INSERT INTO AEDOwners (Name,CityId,StreetId) VALUES ('Nearest Owner',@City,@Street); SET @Owner=LAST_INSERT_ID();
INSERT INTO AEDs (SerialNumber,Latitude,Longitude,OwnerId,AddressId,Access,AvailabilityStartHour,AvailabilityEndHour,Created,LastUpdated) VALUES
('NEAR-PRIVATE',0,0,@Owner,@Address,2,NULL,NULL,NOW(6),NOW(6)),
('NEAR-CLOSED',0,0.0001,@Owner,@Address,0,$closedStart,$closedEnd,NOW(6),NOW(6)),
('NEAR-OPEN',0,0.001,@Owner,@Address,0,0,24,NOW(6),NOW(6)),
('NEAR-FAR',0,0.01,NULL,NULL,1,0,24,NOW(6),NOW(6)),
('NEAR-NO-LAT',NULL,0,NULL,NULL,0,NULL,NULL,NOW(6),NOW(6)),
('NEAR-NO-LON',0,NULL,NULL,NULL,0,NULL,NULL,NOW(6),NOW(6));
"@ | Out-Null
    $nearest = Invoke-Nearest 'latitude=0&longitude=0'
    Assert ($nearest.longitude -eq 0.001 -and $nearest.latitude -eq 0 -and $nearest.ownerName -eq 'Nearest Owner') 'Nearest available AED did not exclude private/closed/missing-coordinate candidates.'
    Assert ($nearest.cityName -eq 'Nearest City' -and $nearest.streetName -eq 'Nearest Street' -and $nearest.postalCode -eq '00-999' -and $nearest.buildingNumber -eq 10) 'Nearest AED omitted known address metadata.'
    Invoke-TestSql "INSERT INTO AEDs (SerialNumber,Latitude,Longitude,Created,LastUpdated) VALUES ('NEAR-UNKNOWN',0,0.0005,NOW(6),NOW(6));" | Out-Null
    $nearest = Invoke-Nearest 'latitude=0&longitude=0'
    Assert ($nearest.longitude -eq 0.0005) 'Unknown access/hours were not allowed.'
    Assert (($nearest.PSObject.Properties.Name -join '|') -eq 'id|latitude|longitude') 'Unknown metadata was returned instead of omitted.'
    Invoke-TestSql @'
INSERT INTO Streets (Name) VALUES ('  '); SET @BlankStreet=LAST_INSERT_ID();
INSERT INTO Addresses (CityId,StreetId) SELECT Id,@BlankStreet FROM Cities WHERE Name='Nearest City';
SET @PartialAddress=LAST_INSERT_ID();
INSERT INTO AEDOwners (Name) VALUES (' '); SET @BlankOwner=LAST_INSERT_ID();
UPDATE AEDs SET AddressId=@PartialAddress,OwnerId=@BlankOwner WHERE SerialNumber='NEAR-UNKNOWN';
'@ | Out-Null
    $nearest = Invoke-Nearest 'latitude=0&longitude=0'
    Assert ($nearest.cityName -eq 'Nearest City' -and @($nearest.PSObject.Properties).Count -eq 4) 'Partial metadata or blank text was not handled correctly.'
    Invoke-TestSql 'UPDATE AEDs SET Access=2;' | Out-Null
    Invoke-Nearest 'latitude=0&longitude=0' 404 | Out-Null
    foreach ($query in @('latitude=91&longitude=0', 'latitude=0&longitude=-181', 'latitude=NaN&longitude=0',
        'latitude=0&longitude=Infinity', 'longitude=0', 'latitude=0&longitude=invalid')) {
        Invoke-Nearest $query 400 | Out-Null
    }

    $warsawHour = [TimeZoneInfo]::ConvertTime([DateTimeOffset]::UtcNow, [TimeZoneInfo]::FindSystemTimeZoneById('Europe/Warsaw')).Hour
    $openEnd = ($warsawHour + 2) % 24
    Invoke-TestSql "UPDATE AEDs SET Access=1,AvailabilityStartHour=$warsawHour,AvailabilityEndHour=$openEnd WHERE SerialNumber='NEAR-OPEN';" | Out-Null
    $nearest = Invoke-Nearest 'latitude=0&longitude=0'
    Assert ($nearest.longitude -eq 0.001) 'Emergency access or inclusive Warsaw opening hour was rejected.'
    $priorHour = ($warsawHour + 22) % 24
    Invoke-TestSql "UPDATE AEDs SET AvailabilityStartHour=$priorHour,AvailabilityEndHour=$warsawHour WHERE SerialNumber='NEAR-OPEN';" | Out-Null
    Invoke-Nearest 'latitude=0&longitude=0' 404 | Out-Null
    Invoke-TestSql "UPDATE AEDs SET AvailabilityStartHour=22,AvailabilityEndHour=6 WHERE SerialNumber='NEAR-OPEN';" | Out-Null
    $overnightStatus = if ($warsawHour -ge 22 -or $warsawHour -lt 6) { 200 } else { 404 }
    Invoke-Nearest 'latitude=0&longitude=0' $overnightStatus | Out-Null
    Invoke-TestSql "UPDATE AEDs SET AvailabilityStartHour=23,AvailabilityEndHour=NULL WHERE SerialNumber='NEAR-OPEN';" | Out-Null
    Invoke-Nearest 'latitude=0&longitude=0' | Out-Null
    Write-Host 'PASS: Nearest filtering, linked owner/address metadata, omission, query validation, Warsaw hours, overnight and partial hours.'

    Invoke-TestSql @'
UPDATE AEDs SET Access=2;
INSERT INTO AEDs (SerialNumber,Latitude,Longitude,Access,Created,LastUpdated) VALUES
('DATELINE-WRAP',0,-179.9,0,NOW(6),NOW(6)), ('DATELINE-FAR',0,179,0,NOW(6),NOW(6));
'@ | Out-Null
    $nearest = Invoke-Nearest 'latitude=0&longitude=179.9'
    Assert ($nearest.longitude -eq -179.9) 'Distance ranking did not wrap across the antimeridian.'
    Invoke-TestSql @'
UPDATE AEDs SET Access=2;
INSERT INTO AEDs (SerialNumber,Latitude,Longitude,Access,Created,LastUpdated) VALUES
('POLAR-NEAR',89.9,180,0,NOW(6),NOW(6)), ('POLAR-FAR',89,0,0,NOW(6),NOW(6));
'@ | Out-Null
    $nearest = Invoke-Nearest 'latitude=89.9&longitude=0'
    Assert ($nearest.longitude -eq 180 -and $nearest.latitude -eq 89.9) 'Distance ranking ignored polar geometry.'
    Invoke-TestSql @'
UPDATE AEDs SET Access=2;
INSERT INTO AEDs (SerialNumber,Latitude,Longitude,Created,LastUpdated) VALUES
('TIE-A',1,1,NOW(6),NOW(6)), ('TIE-B',1,1,NOW(6),NOW(6));
'@ | Out-Null
    $nearest = Invoke-Nearest 'latitude=1&longitude=1'
    Assert ($nearest.id -eq [Int64](Invoke-TestSql "SELECT MIN(Id) FROM AEDs WHERE SerialNumber IN ('TIE-A','TIE-B');")) 'Distance ties were not resolved deterministically.'
    Write-Host 'PASS: Server-side great-circle nearest selection at the antimeridian and poles, and deterministic ties.'

    $spec = Invoke-RestMethod "$base/openapi/v1.json"
    $operation = $spec.paths.'/api/translations/profiles({name})/import'.post
    Assert ($operation.operationId -eq 'ImportTranslationCsv') 'Import OpenAPI route is missing.'
    Assert ($null -ne $operation.requestBody.content.'multipart/form-data') 'File upload is not documented as multipart.'
    $nearestOperation = $spec.paths.'/api/aed/nearest'.get
    Assert ($nearestOperation.operationId -eq 'GetNearestAvailableAED') 'Nearest AED endpoint is not documented.'
    Assert ($nearestOperation.parameters.Count -eq 2) 'Nearest AED query parameters are not documented.'
    $minimalExample = $nearestOperation.responses.'200'.content.'application/json'.examples.coordinatesOnly.value
    Assert (($minimalExample.PSObject.Properties.Name -join '|') -eq 'id|latitude|longitude') 'Nearest AED documentation exposes unknown metadata.'
    foreach ($status in @('200', '400', '404', '409', '415')) {
        Assert ($null -ne $operation.responses.$status) "Import response $status is missing from OpenAPI."
    }
    $savedProfile = Invoke-RestMethod "$base/api/translations/profiles(Linked%20import)"
    Assert ($savedProfile.transporter.transporterUnits.Count -eq 12) 'Existing profile GET behavior regressed.'
    Write-Host 'PASS: Destination allowlist, generated IDs, duplicate mappings, ambiguous matches, and OpenAPI upload metadata.'
} finally {
    if ($null -ne $client) { $client.Dispose() }
    if ($null -ne $app) {
        if (-not $app.HasExited) { $app.Kill($true) }
        $app.WaitForExit()
        $app.Dispose()
    }
    if ($created) {
        & wsl.exe --distribution $Distribution --exec docker rm --force --volumes $container | Out-Null
        if ($LASTEXITCODE -ne 0) { Write-Warning "Could not remove test container $container." }
    }
    $OutputEncoding = $previousOutputEncoding
}
