# AED4Life database

Run the following Docker commands in Ubuntu WSL, from this project directory.
Docker Engine and the Compose plugin must be running in that distribution.

## Configuration

The official image is pinned to `mariadb:12.3.3`, the patch currently published
under the official image's LTS series when this configuration was created.
This is suitable for the installed Ubuntu 26.04 LTS / WSL 2 host; the container
supplies its own userspace, so MariaDB does not need to match Ubuntu's packaged
version. See the [official image catalog](https://github.com/docker-library/official-images/blob/master/library/mariadb).
The server release page may list newer patches before Docker images are published;
check for an available image and review release notes before updating this pin.

If `.env` does not already exist, copy `.env.example` to `.env` and replace both
password placeholders with different strong passwords. `.env` is ignored by Git.
If setup has already generated `.env`, keep its existing credentials.

```sh
docker compose up -d --wait
docker compose ps
```

Connect using host `127.0.0.1`, port `3306`, database `aed4life`, user `aed4life`,
and `MARIADB_PASSWORD` from `.env`. The port is bound only to the WSL host's
loopback interface, not all network interfaces. Windows applications can normally
use WSL's localhost forwarding. Other containers on this Compose network use
host `mariadb` and port `3306`. Root access is restricted to inside the container.

For an interactive application-user SQL session:

```sh
docker compose exec mariadb mariadb -u aed4life -p aed4life
```

## Application connection

The .NET 10 application uses EF Core 9.0.23 with Pomelo 9.0.0, the stable
MariaDB-compatible provider currently available. EF Core's major version must
match the provider, not the application's target framework. MySqlConnector is
pinned separately to a patched version instead of the provider's older default.

From Windows PowerShell, configure the development connection using .NET user
secrets. Replace `<MARIADB_PASSWORD>` with the value from `.env`:

```powershell
dotnet user-secrets set "ConnectionStrings:AED4Life" "Server=127.0.0.1;Port=3306;Database=aed4life;User ID=aed4life;Password=<MARIADB_PASSWORD>;" --project .\src\AED4Life
dotnet run --project .\src\AED4Life
```

Compose's `.env` is not automatically loaded by ASP.NET Core. For deployment,
provide the complete connection string as the `ConnectionStrings__AED4Life`
environment variable instead. Never commit passwords to `appsettings.json`.
Code accessing the database can inject `AED4Life.DataModel.AED4LifeDbContext`.

## Interactive API documentation

When running in Development (the default launch profiles), open
`https://localhost:7231/scalar` for Scalar API documentation. The OpenAPI document
is available at `https://localhost:7231/openapi/v1.json`.

All current endpoints include descriptions and response examples:
`GET /api/aed/owners`, `GET /api/aed/nearest`, `GET /api/aed/nearest({count})`, `GET /api/translations/profiles`,
`GET /api/translations/profiles({name})`, `POST /api/translations/profiles`,
`POST /api/translations/profiles({name})/import`, and
`GET /weatherforecast`. The profile endpoint also includes an editable JSON
request example and examples of `400` validation and `409` duplicate-name errors.
Scalar generates request snippets and lets you send requests to the running app;
POST requests create real database records, so use a new profile name for each
successful request.

Scalar and the OpenAPI document are not exposed outside Development.

## Initial schema

`database\001-initial-schema.sql` creates `Cities`, `Streets`, `PostalCodes`,
`Addresses`, `AEDs`, and `AEDOwners`. Compose mounts this directory read-only into MariaDB's startup
initialization directory. MariaDB runs it automatically **only when initializing
an empty data volume**.

For an existing volume (including the database created before this script was
added), run this command once from Ubuntu WSL, in the project directory:

```sh
docker compose exec -T mariadb sh -c 'MYSQL_PWD="$MARIADB_PASSWORD" exec mariadb --user="$MARIADB_USER" "$MARIADB_DATABASE"' < database/001-initial-schema.sql
```

The script uses `CREATE TABLE IF NOT EXISTS`: it can be rerun without deleting
rows, but it does not migrate or repair pre-existing tables. Future model changes
need matching schema changes; the application does not automatically call
`EnsureCreated` or apply migrations. In particular, databases using the old
`Cities.PostalCode` and `AEDs.CityId`/`StreetId`/`HouseNumber` layout require a
separate data migration before using this version. The initialization scripts
do not migrate that layout; do not delete a populated volume to upgrade it.

Entity fields are mapped as public properties. `AED`, `Address`, `City`,
`Street`, and `AEDOwner` have auto-generated `Int64` IDs; `PostalCode` has an
auto-generated `Int32` ID and a nullable `Code` of at most six characters.
`AEDOwner.RegonNumber` is a nullable,
unique string of at most 14 characters, preserving leading zeros (multiple
unknown REGONs are allowed). The owner
endpoint returns REGON as a JSON string with the owner's name, public flag,
city name, and street name, without exposing IDs. It no longer returns a postal
code: owners still reference cities and streets directly, and a city does not
identify a single postal code.
`AED.AddressId` references `Addresses`; each address contains `CityId`,
`StreetId`, `PostalCodeId`, and an integer `BuildingNumber`. All these foreign
keys restrict deletion while referenced. `AED.OwnerId` optionally references
`AEDOwners`, also with restricted deletion. AED/location/owner business-data fields, including names, serial numbers, address parts,
foreign keys, public flags, and ratings, are nullable. City/street names, owner
names, and serial numbers use `LONGTEXT`; timestamps are supplied by application
code, with microsecond database precision.
Generated IDs and operational timestamps remain nonnullable, as do translation
profile names and mapping definitions. The owner endpoint includes owners whose
city or street is unknown and returns unknown fields as JSON `null`.

## Users and AED reports

`Users` contains an auto-generated `Int64` `Id`, a required unique `Username`
(up to 255 characters), required `FirstName`, `LastName`, `BirthDate` (`DATE`,
mapped to `DateOnly`), required residence `AddressId` referencing `Addresses`,
and required `Type`. Types are stored as integers: `Admin=0`, `Normal=1`,
`PublicRepresentative=2`, `Maintainer=3`. New C# users default to `Normal`;
SQL inserts must specify the type. Usernames follow the database's
case-insensitive collation.

`PasswordHash` is required (`VARCHAR(512)`, nonempty) and excluded from JSON.
Store only the output of the registered `IPasswordHasher<User>`, never a
plaintext password or reversible encryption. It uses ASP.NET Core Identity V3
PBKDF2-HMAC-SHA512 with 210,000 iterations and a separate random salt per hash;
the format includes the version, algorithm, iteration count, salt, and subkey.
The framework password hasher is registered for future registration/login
handlers; those endpoints are not implemented yet.

Before saving a newly registered user, hash the password supplied in a separate
registration request DTO:

```csharp
user.PasswordHash = passwordHasher.HashPassword(user, providedPassword);
```

Verify passwords using `VerifyHashedPassword(user, user.PasswordHash, providedPassword)`,
not string comparison or by hashing again. Treat `Failed` as a failed login;
when verification returns `SuccessRehashNeeded`, generate and save a new hash.
Never return password hashes in API responses or log plaintext passwords.

`010-user-password-hash.sql` upgrades existing databases. If any existing user
lacks a hash, initialization **stops** with an explicit error. The upgrade
leaves a temporary nullable `PasswordHash` column so an operator can provision
each user's hash through trusted code using the application password hasher.
Rerun initialization after provisioning all users; it enforces `NOT NULL` and
rejects empty hashes without modifying supplied hashes. Do not assign a shared
default password or use SQL `MD5`/`SHA` functions for password storage.
Initialization creates a bootstrap `admin` account (`Type=Admin`) whenever
that username is absent, even when other users already exist. Its dummy profile
is Jan Kowalski, born 1980-01-01, linked to the first existing address.
The requested initial password is stored only as an Identity V3 hash. This is
a publicly known, weak bootstrap credential: change it before exposing the app.
An existing `admin` account is never overwritten, including its password,
profile, and type. Other demo users have hashes of discarded random passwords.
Registration/login endpoints are still not implemented by this seed.

`AEDReports` contains an auto-generated `Int64` `Id`, required author `UserId`
referencing `Users`, optional `AEDId` referencing `AEDs`, optional `PhotoUrl`
(a URL or file path, not image bytes), required `Created` and `LastUpdated`
timestamps, and required `Status`: `Submitted=0`, `UnderReview=1`,
`Confirmed=2`, `Rejected=3`. A report may concern an AED not yet in the database.
Photo storage/upload is not implemented; example photo paths are placeholders.
As with AED timestamps, application code supplies and updates report timestamps
in UTC, with microsecond database precision.

Foreign keys restrict deletion of referenced users, AEDs, and residence
addresses. SQL checks reject undefined user types and report statuses. These
tables and their EF entities do not add authentication, authorization, or
user/report endpoints.

For an existing database, run either initializer below to apply
`009-users-and-aed-reports.sql` and `010-user-password-hash.sql`, then seed empty tables without replacing
existing records.

## Fill empty tables

Start the database, then run this command from Windows PowerShell in the project
directory:

```powershell
.\scripts\Initialize-Database.ps1
```

The script uses the running Compose container and its environment credentials;
it does not read or print passwords. Optional `-Distribution` and `-ProjectName`
parameters select another WSL distribution or Compose project.

On Linux, macOS, or inside WSL, use the Bash equivalent:

```bash
bash ./scripts/Initialize-Database.sh
```

Use `--project-name NAME` to select another Compose project (default: `aed4life`).
The Bash script uses Docker directly and can be invoked from any working
directory by providing its path.

Both scripts create missing tables, apply `003-unique-owner-regon.sql`,
`004-translation-profiles.sql`, `005-aed-availability.sql`,
`006-aed-coordinates.sql`, `007-nullable-import-data.sql`,
`008-aed-owner.sql`, `009-users-and-aed-reports.sql`, and
`010-user-password-hash.sql`, then execute
`002-populate-tables.sql`.
Each location/AED/owner/user/report sample-data table receives rows only when completely
empty; partially populated tables are left unchanged except that a missing
bootstrap `admin` user is added. Sample addresses use
actual existing city/street/postal-code IDs in ascending order, cycling through
available lookup rows. AEDs similarly use actual address and owner IDs, and owners use
actual city/street IDs. Seeded ownership associations and locations are
demonstration data, not verified addresses.

An empty database receives six cities, four streets, six postal codes, six
addresses, five owners, six AEDs, four users, and four reports. Sample users
cover all four types, and sample reports cover all four statuses, including
a report without an AED reference. `004` also seeds two sample translation
profiles with nine ordered units only when there are no profiles; existing
profiles and their units are preserved.

Location/AED/owner/user/report population and translation-profile population each run in
their own transaction. Repeating the script does not add rows to
nonempty tables, apart from creating a missing bootstrap `admin` account.
The REGON upgrade supports the original numeric REGON primary
key by adding an owner ID and converting REGON to a string. Existing duplicate
REGONs or values longer than 14 characters cause the upgrade to fail rather than
silently delete or truncate data; resolve those values and rerun. Schema upgrades
are separate from the seed transaction.

On an empty Docker volume, MariaDB runs all SQL files in filename order.

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

## Find the nearest available AED

```powershell
curl.exe "https://localhost:7231/api/aed/nearest?latitude=52.229676&longitude=21.012229"
```

Both query coordinates are required, finite decimal degrees within latitude
[-90, 90] and longitude [-180, 180]. The database ranks eligible AEDs by
great-circle (straight-line, not walking/driving) distance; it does not load all
AEDs into application memory. Equal distances choose the lowest AED ID.

An eligible AED has both coordinates, is not marked `Private`, and is not known
to be closed. `Open`, `Emergency`, and unknown access are included. Complete
daily opening hours are checked against the current **Europe/Warsaw** time,
including daylight-saving changes. Opening is inclusive and closing exclusive;
overnight ranges such as 22 to 6 work across midnight. If either hour is
unknown, availability is treated as unknown and the AED is included. Ratings
and an owner's public/private flag do not override these access rules.

Example response:

```json
{
  "id": 1,
  "latitude": 52.229676,
  "longitude": 21.012229,
  "ownerName": "Example operator",
  "cityName": "Warszawa",
  "streetName": "Example Street",
  "postalCode": "00-001",
  "buildingNumber": 10
}
```

Unknown or blank owner/address text, and unknown building numbers, are omitted
from the response. An AED without an owner or address still returns its ID and
coordinates. Invalid query coordinates return `400`; no eligible AED returns
`404`.

To request multiple nearest available AEDs, pass a positive 32-bit integer in
parentheses in the route (not as a query parameter):

```powershell
curl.exe "https://localhost:7231/api/aed/nearest(5)?latitude=52.229676&longitude=21.012229"
```

This returns an array of up to five AEDs, closest first, using the same
availability and metadata rules. Ties use AED ID. The limit is applied in the
database. If fewer AEDs are available, all eligible AEDs are returned; if none
are available, the response is `200` with `[]`. Invalid counts or coordinates
return `400`. The existing single-AED endpoint is unchanged.

For an existing database, run `.\scripts\Initialize-Database.ps1` to apply
`008-aed-owner.sql`. Existing AEDs retain unknown ownership (`NULL`); no
historical owner is inferred from location. Reimport CSV data with owner
mappings, such as `openaedmap-2`, to populate these explicit links.

## AED access, hours, and rating

The `AED` entity and `AEDs` table include:

| Field | Values |
| --- | --- |
| `Access` | `AEDAccess.Open` (0), `Emergency` (1), `Private` (2), or `NULL` for unknown |
| `AvailabilityStartHour` | Whole hour, 0-23, or `NULL` |
| `AvailabilityEndHour` | Whole hour, 0-24, or `NULL` |
| `Rating` | `AEDRating.MissingData` (0), `Fine` (1), or `NULL` for unknown |

Availability hours may independently be unknown (`NULL`).
Equal known hours are invalid. `0` to `24` means all-day availability; overnight ranges
such as `22` to `6` are allowed. Enums are stored as checked integers and serialize
to their names when used in JSON.

The initial schema and sample AED rows include these fields. For an existing
database, run this from Ubuntu WSL in the project directory:

```sh
docker compose exec -T mariadb sh -c 'MYSQL_PWD="$MARIADB_PASSWORD" exec mariadb --user="$MARIADB_USER" "$MARIADB_DATABASE"' < database/005-aed-availability.sql
```

The upgrade is safe to rerun. Existing AEDs retain their original data and gain
unknown access/hours/rating; no access or availability is
inferred from existing rows.

## AED GPS coordinates

`AED.Latitude` and `AED.Longitude` use nullable .NET `Double` properties and
MariaDB `DOUBLE` columns. Double precision is more than sufficient for GPS
coordinates. Values are decimal degrees: latitude ranges from -90 to 90 and
longitude from -180 to 180, inclusive. `NULL` means unknown; zero is a valid
coordinate. Both EF mappings and SQL define matching range constraints.

The six dummy AED rows include demonstration coordinates, not verified device
locations. Existing AEDs are not assigned invented coordinates. To add the
columns to an existing database, run `.\scripts\Initialize-Database.ps1`, or apply
`database\006-aed-coordinates.sql` directly. The upgrade preserves existing
records, leaves previously unknown coordinates `NULL`, and is safe to rerun.

CSV profiles can map `AEDs.Latitude` and `AEDs.Longitude` with `toType: "DOUBLE"`.
Use `fromType: "DOUBLE"` for numeric input, or `"STRING"` to convert text.
Empty mapped cells become `NULL`; unmapped coordinates remain unchanged.
Nonfinite and out-of-range values are rejected and roll back the file.

## Persistent storage

The named volume `aed4life_mariadb_data` holds the database files outside the
container, in Docker's storage on the WSL Linux filesystem. It is not stored in
the Windows project directory. Recreating the container preserves the data.
Inspect its location with:

```sh
docker volume inspect aed4life_mariadb_data
```

Stop and remove the container while keeping the database:

```sh
docker compose down
```

**Do not use `docker compose down -v` or delete the volume unless you intend to
permanently erase the database.** A volume is persistence, not a backup.
Database/user/password environment settings only initialize an empty volume;
changing `.env` later does not change existing database credentials.
