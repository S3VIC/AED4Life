# AED4Life

AED4Life is a MariaDB-backed ASP.NET Core WebAPI for AED (defibrillator) locations, owners, reports and
CSV imports, plus a mobile web GUI. This README covers **setup and initialisation**; everything about how the
API and data model work is in [docs/](docs/README.md).

## Quick start

Prerequisites: Docker (Docker Desktop, or Docker Engine in WSL), and the .NET 10 SDK.

**WebAPI and database, one step.** The script creates `.env` with random passwords (existing values are kept),
starts MariaDB, applies the SQL scripts from `database/`, stores `ConnectionStrings:AED4Life` in the API's .NET
user secrets and starts the API at `https://localhost:7231/scalar`. It is safe to re-run; add `-NoRun` /
`--no-run` to skip starting the API.

```powershell
pwsh ./scripts/Setup.ps1        # Windows (PowerShell 7)
```

```bash
bash scripts/setup.sh           # Linux / macOS / WSL
```

**GUI, no arguments.** Serves `gui/aplikacja` on the first free port from 8000 to 8020 and opens the browser:

```powershell
pwsh ./gui/Start-Gui.ps1
```

```bash
bash gui/start-gui.sh
```

To host the GUI on a VM (Caddy, HTTPS via sslip.io and the `/api4life` proxy to the API), run
`bash gui/start.sh` there. The checked-in sample CSV and its translation profile are in `sample-data/`
(see [docs/translation-and-import.md](docs/translation-and-import.md)).

## Requirements and manual setup

The steps below are what the setup script automates; use them to set things up by hand.

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
`004-translation-profiles.sql`, then `014-aed-data-rating.sql` before the older
availability/nullability upgrades so existing rating values are renamed first.
They then apply `005-aed-availability.sql`,
`006-aed-coordinates.sql`, `007-nullable-import-data.sql`,
`008-aed-owner.sql`, `009-users-and-aed-reports.sql`,
`010-user-password-hash.sql`, `011-required-report-photo.sql`, and
`012-report-placement-metadata.sql`, `013-report-rating.sql`, and `015-report-location.sql`, then execute
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

## Documentation

See [docs/README.md](docs/README.md) for the full index:

- [API reference and Scalar](docs/api-reference.md)
- [Authentication, roles and report review](docs/authentication-and-reports.md)
- [AED endpoints, statistics and validation](docs/aed-endpoints.md)
- [Users and AED reports](docs/users-and-reports.md)
- [Translation profiles and CSV import](docs/translation-and-import.md)
- [Database schema](docs/database-schema.md)
