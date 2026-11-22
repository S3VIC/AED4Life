#!/usr/bin/env bash
# One-step setup of the AED4Life WebAPI infrastructure (Linux / macOS / WSL).
#
#   1. Creates .env with random, hash-derived passwords (existing values are kept).
#   2. Starts the MariaDB container with Docker Compose and waits until it is healthy.
#   3. Applies the SQL schema/seed scripts from ./database (safe to re-run).
#   4. Stores ConnectionStrings:AED4Life in the WebAPI's .NET user secrets.
#   5. Starts the WebAPI (skip with --no-run).
#
# Run it with no arguments:  bash scripts/setup.sh
set -euo pipefail

PROJECT_NAME=aed4life
RUN_API=1
for arg in "$@"; do
    case "$arg" in
        --no-run) RUN_API=0 ;;
        -h|--help) sed -n '2,10p' "${BASH_SOURCE[0]}"; exit 0 ;;
        *) printf 'Unknown argument: %s\n' "$arg" >&2; exit 1 ;;
    esac
done

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT/.env"
API_PROJECT="$ROOT/src/AED4Life"
step() { printf '\n==> %s\n' "$*"; }

new_secret() { head -c 32 /dev/urandom | sha256sum | awk '{print $1}'; }   # CSPRNG bytes -> SHA-256 hex
env_get()    { [ -f "$ENV_FILE" ] && grep -E "^$1=" "$ENV_FILE" | head -n1 | cut -d= -f2- || true; }

# --- prerequisites ------------------------------------------------------------------------------
step "Checking prerequisites"
command -v dotnet >/dev/null || { echo ".NET SDK 10 is required but 'dotnet' was not found. Install it from https://dotnet.microsoft.com/download and re-run." >&2; exit 1; }
command -v docker >/dev/null || { echo "Docker is required but 'docker' was not found. Install Docker Engine + the Compose plugin and re-run." >&2; exit 1; }
DOCKER=(docker)
if ! docker info >/dev/null 2>&1; then
    if sudo -n docker info >/dev/null 2>&1; then DOCKER=(sudo docker)
    else echo "Cannot talk to the Docker daemon. Start it, or add your user to the 'docker' group, and re-run." >&2; exit 1; fi
fi
compose() { "${DOCKER[@]}" compose --project-name "$PROJECT_NAME" --project-directory "$ROOT" "$@"; }

# --- .env ---------------------------------------------------------------------------------------
step "Preparing .env"
MARIADB_PASSWORD="$(env_get MARIADB_PASSWORD)"
MARIADB_ROOT_PASSWORD="$(env_get MARIADB_ROOT_PASSWORD)"
if [ -z "$MARIADB_PASSWORD" ] || [ -z "$MARIADB_ROOT_PASSWORD" ]; then
    [ -n "$MARIADB_PASSWORD" ]      || MARIADB_PASSWORD="$(new_secret)"
    [ -n "$MARIADB_ROOT_PASSWORD" ] || MARIADB_ROOT_PASSWORD="$(new_secret)"
    old_umask="$(umask)"; umask 077
    {
        # keep any other variables that were already in the file
        [ -f "$ENV_FILE" ] && grep -vE '^(MARIADB_PASSWORD|MARIADB_ROOT_PASSWORD)=' "$ENV_FILE" || true
        printf 'MARIADB_PASSWORD=%s\nMARIADB_ROOT_PASSWORD=%s\n' "$MARIADB_PASSWORD" "$MARIADB_ROOT_PASSWORD"
    } > "$ENV_FILE.tmp"
    mv "$ENV_FILE.tmp" "$ENV_FILE"; chmod 600 "$ENV_FILE"; umask "$old_umask"
    echo "Wrote .env with generated passwords."
else
    echo ".env already complete - existing credentials kept."
fi

# --- database -----------------------------------------------------------------------------------
step "Starting MariaDB"
compose up -d --wait

step "Applying database scripts"
apply_sql() {
    printf 'Applying %s...\n' "$(basename "$1")"
    if ! compose exec -T mariadb sh -c \
        'MYSQL_PWD="$MARIADB_PASSWORD" exec mariadb --default-character-set=utf8mb4 --user="$MARIADB_USER" "$MARIADB_DATABASE"' < "$1"; then
        printf '%s failed. If the database volume was created with different passwords, run "docker compose down -v" (this deletes its data) and re-run the setup.\n' "$(basename "$1")" >&2
        exit 1
    fi
}
# Schema first, then incremental upgrades, and the sample-data seed (002) last.
for f in "$ROOT"/database/001-*.sql; do apply_sql "$f"; done
for f in "$ROOT"/database/*.sql; do
    case "$(basename "$f")" in 001-*|002-*) continue ;; esac
    apply_sql "$f"
done
for f in "$ROOT"/database/002-*.sql; do apply_sql "$f"; done

# --- connection string --------------------------------------------------------------------------
step "Configuring WebAPI connection string (.NET user secrets)"
CONNECTION_STRING="Server=127.0.0.1;Port=3306;Database=aed4life;User ID=aed4life;Password=${MARIADB_PASSWORD};"
dotnet user-secrets set "ConnectionStrings:AED4Life" "$CONNECTION_STRING" --project "$API_PROJECT" >/dev/null
echo "ConnectionStrings:AED4Life stored in user secrets."

# --- run ----------------------------------------------------------------------------------------
step "Setup complete"
if [ "$RUN_API" -eq 0 ]; then
    echo "Start the API later with:  dotnet run --project src/AED4Life --launch-profile https"
    exit 0
fi
dotnet dev-certs https >/dev/null 2>&1 || echo "Warning: could not create the HTTPS development certificate."
echo "Starting the WebAPI:  https://localhost:7231/scalar   (Ctrl+C to stop)"
exec dotnet run --project "$API_PROJECT" --launch-profile https
