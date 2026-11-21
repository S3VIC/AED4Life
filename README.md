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
`GET /api/aed/owners`, `POST /api/translations/profiles`, and
`GET /weatherforecast`. The profile endpoint also includes an editable JSON
request example and examples of `400` validation and `409` duplicate-name errors.
Scalar generates request snippets and lets you send requests to the running app;
POST requests create real database records, so use a new profile name for each
successful request.

Scalar and the OpenAPI document are not exposed outside Development.

## Initial schema

`database\001-initial-schema.sql` creates `Cities`, `Streets`, `AEDs`, and
`AEDOwners`. Compose mounts this directory read-only into MariaDB's startup
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
`EnsureCreated` or apply migrations.

Entity fields are mapped as public properties. `AED`, `City`, `Street`, and
`AEDOwner` have auto-generated `Int64` IDs. `AEDOwner.RegonNumber` is a required,
unique string of at most 14 characters, preserving leading zeros. The owner
endpoint returns REGON as a JSON string and includes the owner's `id`, but does
not expose city or street IDs.
Both `AED` and `AEDOwner` reference cities and streets using `Int64` foreign
keys, with deletion restricted while referenced. No AED-to-owner relationship
has been invented. Strings other than REGON remain required and use `LONGTEXT`
because the entities do not specify length limits; timestamps are supplied by application
code, with microsecond database precision.

## Fill empty tables

Start the database, then run this command from Windows PowerShell in the project
directory:

```powershell
.\scripts\Initialize-Database.ps1
```

The script uses the running Compose container and its environment credentials;
it does not read or print passwords. Optional `-Distribution` and `-ProjectName`
parameters select another WSL distribution or Compose project.

It creates missing tables, applies `003-unique-owner-regon.sql`,
`004-translation-profiles.sql`, and `005-aed-availability.sql`, then executes
`002-populate-tables.sql`.
Each sample-data table receives rows only when completely
empty; partially populated tables are left unchanged. Sample owners and AEDs
use actual existing city/street IDs in ascending order, cycling through available
locations if there are fewer than the original samples. Their locations are
demonstration data, not verified addresses.

Population runs in one transaction. Repeating the script does not add rows to
nonempty tables. The upgrade also supports the original numeric REGON primary
key by adding an owner ID and converting REGON to a string. Existing duplicate
REGONs or values longer than 14 characters cause the upgrade to fail rather than
silently delete or truncate data; resolve those values and rerun. Schema upgrades
are separate from the seed transaction.

On an empty Docker volume, MariaDB runs all SQL files in filename order.

## Translation profiles

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
        "toColumn": "Name",
        "toType": "STRING"
      },
      {
        "fromColumn": "regon",
        "fromType": "STRING",
        "toColumn": "RegonNumber",
        "toType": "STRING"
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

## AED access, hours, and rating

The `AED` entity and `AEDs` table include:

| Field | Values |
| --- | --- |
| `Access` | `AEDAccess.Open` (0), `Emergency` (1), `Private` (2), or `NULL` for unknown |
| `AvailabilityStartHour` | Whole hour, 0-23, or `NULL` |
| `AvailabilityEndHour` | Whole hour, 0-24, or `NULL` |
| `Rating` | `AEDRating.MissingData` (0, default) or `Fine` (1) |

Availability hours must either both be unknown (`NULL`) or both be supplied.
Equal hours are invalid. `0` to `24` means all-day availability; overnight ranges
such as `22` to `6` are allowed. Enums are stored as checked integers and serialize
to their names when used in JSON.

The initial schema and sample AED rows include these fields. For an existing
database, run this from Ubuntu WSL in the project directory:

```sh
docker compose exec -T mariadb sh -c 'MYSQL_PWD="$MARIADB_PASSWORD" exec mariadb --user="$MARIADB_USER" "$MARIADB_DATABASE"' < database/005-aed-availability.sql
```

The upgrade is safe to rerun. Existing AEDs retain their original data and gain
unknown access/hours plus `MissingData` rating; no access or availability is
inferred from existing rows.

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
