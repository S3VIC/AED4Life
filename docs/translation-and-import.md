# Translation profiles and CSV import

## Translation profiles

`GET /api/translations/profiles` returns all profiles ordered by name, or an
empty array if there are none. `GET /api/translations/profiles({name})` returns
one profile using the database's case-insensitive name comparison, or a `404`
problem response if it does not exist. URL-encode the name inside parentheses,
for example `/api/translations/profiles(Owner%20import)`. Both GET endpoints
return the same `id`, `name`, and `transporter` shape as POST, with mapping units
in stored position order.

`POST /api/translations/profiles` creates a named mapping using `Transporter` and
its ordered `TransporterUnits` array:

```json
{
  "name": "Owner import",
  "transporter": {
    "transporterUnits": [
      {
        "fromColumn": "owner_name",
        "fromType": "STRING",
        "toColumn": "AEDOwners.Name",
        "toType": "STRING"
      },
      {
        "fromColumn": "regon",
        "fromType": "STRING",
        "toColumn": "AEDOwners.RegonNumber",
        "toType": "STRING"
      },
      {
        "fromColumn": "is_public",
        "fromType": "BOOLEAN",
        "toColumn": "AEDOwners.IsPublic",
        "toType": "BOOLEAN"
      },
      {
        "fromColumn": "city_id",
        "fromType": "INTEGER",
        "toColumn": "AEDOwners.CityId",
        "toType": "INTEGER"
      },
      {
        "fromColumn": "street_id",
        "fromType": "INTEGER",
        "toColumn": "AEDOwners.StreetId",
        "toType": "INTEGER"
      }
    ]
  }
}
```

The endpoint returns `201` with the generated `id`, normalized `name`, and
`transporter`. Names are trimmed, limited to 255 characters, and unique under
the database's case-insensitive collation; duplicate names return `409`.
Invalid requests return `400`: a name, at least one unit, nonblank source and
destination columns, and both variable types are required. Supported types are
`INTEGER`, `DOUBLE`, `STRING`, and `BOOLEAN` (or their defined numeric enum values).

Profiles and all their units are inserted atomically. Unit positions preserve
array order. `TranslationProfiles` and `TranslationProfileUnits` are defined in
`database\004-translation-profiles.sql`; units reference their profile with
cascading deletion. This endpoint stores mapping configuration; it does not
execute translations.

For an existing database, or to apply only the translation tables, run the
following in Ubuntu WSL from the project directory:

```sh
docker compose exec -T mariadb sh -c 'MYSQL_PWD="$MARIADB_PASSWORD" exec mariadb --user="$MARIADB_USER" "$MARIADB_DATABASE"' < database/004-translation-profiles.sql
```

This script is safe to rerun and does not populate or modify existing AED data.

## Import CSV data

`POST /api/translations/profiles({name})/import` accepts one CSV upload in the
multipart field `file`. URL-encode the profile name inside parentheses.
For example, after creating the owner profile above:

```powershell
curl.exe --fail-with-body -F "file=@owners.csv;type=text/csv" "https://localhost:7231/api/translations/profiles(Owner%20import)/import"
```

```csv
owner_name,regon,is_public,city_id,street_id
"Example school, main building",001234567,true,1,1
```

Use actual existing city/street IDs in this example. Alternatively, map
`Cities.Name` and `Streets.Name` in the same profile to create or match those
records and supply the owner's foreign keys automatically.

Only UTF-8 comma-separated CSV is supported, with optional BOM, a required
header record, and standard quoting (including escaped quotes and embedded
newlines). Headers are case-sensitive and must be unique and nonblank.
Unmapped CSV columns are ignored, and blank lines are skipped. Missing mapped
headers, inconsistent field counts, malformed quoting, empty files, and
header-only files are rejected.

Import destinations must use exact, case-sensitive `Table.Column` names from
`Cities`, `Streets`, `PostalCodes`, `Addresses`, `AEDOwners`, or `AEDs`. Generated
`Id` columns and translation-configuration tables cannot be imported. Older
profiles with unqualified destinations such as `Name` must be replaced with
qualified mappings before importing; existing stored profiles are not rewritten.
Each destination may be mapped only once.

Each row is processed in dependency order and upserted using these keys:

| Table | Matching key |
| --- | --- |
| `Cities`, `Streets` | `Name` |
| `PostalCodes` | `Code` |
| `Addresses` | `CityId`, `StreetId`, `PostalCodeId`, `BuildingNumber` |
| `AEDOwners` | `RegonNumber` when known; otherwise `Name` + `CityId` + `StreetId` when the name is known |
| `AEDs` | `SerialNumber` when known; otherwise `Latitude` + `Longitude` + `AddressId` when both coordinates are known |

Name/code comparisons use the database collation. Multiple existing records
matching the same key cause a validation error rather than choosing an
arbitrary record. Address keys can include unknown parts, matched as SQL `NULL`.
When no reliable AED or owner key is available, a new record is inserted rather
than merging unrelated unknown records. In particular, reimporting AED rows
without serial numbers and without both coordinates creates new AEDs.
Only mapped values and automatically linked foreign keys are changed on
existing records. Missing business-data values default to `NULL`, including
rating. IDs are generated and AED timestamps default to UTC now. Empty mapped
timestamps use generated/preserved timestamps, not SQL `NULL`. AED updates
refresh `LastUpdated` unless explicitly supplied.

Mapped city/street records supply IDs to mapped addresses and owners; postal
codes supply IDs to mapped addresses; addresses supply IDs to mapped AEDs.
When an AED and city/street/postal-code lookups are mapped without an explicit
address, the importer automatically creates or matches a partial address.
Building numbers and any missing location components stay `NULL`.
Wholly empty lookup records, addresses, and owners are skipped instead of
creating unnamed placeholder rows. AED rows are still imported with generated
IDs and whatever data is available. Empty mapped related lookups clear their
inferred foreign keys; an explicitly supplied nonnull foreign key takes
precedence over an empty lookup.
Explicit foreign keys may instead refer to existing records. Supplying an
explicit ID that disagrees with a related mapped record is rejected.
A mapped owner in a CSV row supplies that row's `AEDs.OwnerId`; a wholly empty
mapped owner clears the link unless an explicit nonnull `OwnerId` is supplied.
Unmapped ownership is preserved. Ownership is never guessed from a shared
city/street address.

For example, a profile mapping the following five columns creates or matches
a complete AED location without any IDs in the CSV:

| CSV header | `fromType` | `toColumn` | `toType` |
| --- | --- | --- | --- |
| `city` | `STRING` | `Cities.Name` | `STRING` |
| `street` | `STRING` | `Streets.Name` | `STRING` |
| `postal_code` | `STRING` | `PostalCodes.Code` | `STRING` |
| `building` | `INTEGER` | `Addresses.BuildingNumber` | `INTEGER` |
| `serial` | `STRING` | `AEDs.SerialNumber` | `STRING` |

Values are parsed as `fromType`, then converted to `toType`. Use `STRING` for
text columns and timestamps, `INTEGER` for integer/enum columns, `DOUBLE` for
GPS coordinates, and `BOOLEAN` for `IsPublic`. Numbers use invariant culture; fractional values cannot be
converted to integers. Booleans accept `true`/`false` (case-insensitive) or `1`/`0`.
Empty/whitespace-only cells, case-insensitive literal `NULL`, and the literal
`\N` become SQL `NULL` before type conversion. Nonempty malformed values still
fail validation; column length and enum/range restrictions remain enforced. Keep REGON and
postal-code values as strings to preserve leading zeros.

### OpenAEDMap-compatible sparse imports

The `openaedmap-2` profile works unchanged with these mappings:

| CSV header | `fromType` | `toColumn` | `toType` |
| --- | --- | --- | --- |
| `addr:city` | `STRING` | `Cities.Name` | `STRING` |
| `addr:street` | `STRING` | `Streets.Name` | `STRING` |
| `addr:postcode` | `STRING` | `PostalCodes.Code` | `STRING` |
| `lat` | `DOUBLE` | `AEDs.Latitude` | `DOUBLE` |
| `lon` | `DOUBLE` | `AEDs.Longitude` | `DOUBLE` |
| `operator` | `STRING` | `AEDOwners.Name` | `STRING` |

```csv
addr:city,addr:street,addr:postcode,lat,lon,operator
Warszawa,Example Street,00-001,52.229676,21.012229,Example operator
,,,52.230000,21.013000,
NULL,\N,, ,21.014000,NULL
```

Upload to `/api/translations/profiles(openaedmap-2)/import`. No serial number,
REGON, public flag, or building number is required. The importer infers partial
addresses and uses the fallback matching keys described above. The row's
`operator` is linked to its AED through the nullable `OwnerId` foreign key.

Before importing into an existing database, run
`.\scripts\Initialize-Database.ps1` to apply
`database\007-nullable-import-data.sql` and `database\008-aed-owner.sql`. These upgrades preserve existing values;
it does not rewrite existing nonnull data or translation profiles.
Mapped headers must still exist, even if every cell beneath one is empty.

The entire file runs in one serializable transaction: invalid data or database
conflicts roll back inserts and updates, including related lookup records.
Successful imports return `200` with `profileName`, `rowsProcessed`, and
per-table `inserted`/`updated` operation counts. Unchanged matches do not count as
updates; repeated rows can update the same record more than once.
Validation errors return `400` with a row/column error when available, missing
profiles return `404`, database conflicts return `409`, and non-`.csv` uploads
return `415`. Retry a concurrency conflict after the other operation completes.
Existing ASP.NET Core request-size limits still apply.

Run the focused integration checks from PowerShell 7 with Docker running in WSL:

```powershell
.\scripts\Test-CsvImport.ps1
```

The checks create and remove an isolated MariaDB container and API process;
they do not modify the application's existing database.

