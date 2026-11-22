#!/usr/bin/env bash
set -euo pipefail

project_name='aed4life'

usage() {
    printf 'Usage: bash %s [--project-name NAME]\n' "${BASH_SOURCE[0]}"
}

while (( $# > 0 )); do
    case "$1" in
        --project-name)
            if (( $# < 2 )) || [[ -z "$2" || "$2" == -* ]]; then
                printf 'Error: --project-name requires a name.\n' >&2
                exit 1
            fi
            project_name="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            printf 'Error: unknown argument: %s\n' "$1" >&2
            usage >&2
            exit 1
            ;;
    esac
done

project_directory="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd -- "$project_directory"

for file_name in \
    001-initial-schema.sql \
    003-unique-owner-regon.sql \
    004-translation-profiles.sql \
    005-aed-availability.sql \
    006-aed-coordinates.sql \
    007-nullable-import-data.sql \
    008-aed-owner.sql \
    009-users-and-aed-reports.sql \
    010-user-password-hash.sql \
    011-required-report-photo.sql \
    012-report-placement-metadata.sql \
    013-report-rating.sql \
    002-populate-tables.sql; do
    printf 'Applying %s...\n' "$file_name"
    if ! docker compose --project-name "$project_name" exec -T mariadb sh -c \
        'MYSQL_PWD="$MARIADB_PASSWORD" exec mariadb --default-character-set=utf8mb4 --user="$MARIADB_USER" "$MARIADB_DATABASE"' \
        < "$project_directory/database/$file_name"; then
        printf '%s failed. Resolve the database error above before retrying.\n' "$file_name" >&2
        exit 1
    fi
done

printf 'Database initialized. Nonempty tables were preserved.\n'
