# Database schema

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

## AED access, hours, and data rating

The `AED` entity and `AEDs` table include:

| Field | Values |
| --- | --- |
| `Access` | `AEDAccess.Open` (0), `Emergency` (1), `Private` (2), or `NULL` for unknown |
| `AvailabilityStartHour` | Whole hour, 0-23, or `NULL` |
| `AvailabilityEndHour` | Whole hour, 0-24, or `NULL` |
| `DataRating` | `AEDRating.MissingData` (0), `Fine` (1), or `NULL` for unknown |

Availability hours may independently be unknown (`NULL`).
Equal known hours are invalid. `0` to `24` means all-day availability; overnight ranges
such as `22` to `6` are allowed. Enums are stored as checked integers and serialize
to their names when used in JSON.

The initial schema and sample AED rows include these fields. For an existing
database, run either database initializer, for example from PowerShell:

```powershell
.\scripts\Initialize-Database.ps1
```

`014-aed-data-rating.sql` renames the old `AEDs.Rating` column to
`AEDs.DataRating` without changing values, enum meanings, or nullability.
Stored translation destinations are updated from `AEDs.Rating` to
`AEDs.DataRating`; new profiles must use the new destination name. CSV source
header names need not change. `AEDReports.Rating` remains a separate nullable
0-100 integer and is not renamed.

The upgrades are safe to rerun. Existing AEDs retain their original data and gain
unknown access/hours/data rating where fields were missing; no access or availability is
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

