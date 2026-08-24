#!/bin/sh
set -eu

mode=${1:-}
migration_directory=${MIGRATION_DIRECTORY:-/migrations}

if [ "$mode" != "apply" ] && [ "$mode" != "baseline" ]; then
    echo "usage: postgres_migrate.sh apply|baseline" >&2
    exit 2
fi

psql_run() {
    if [ -n "${DATABASE_URL:-}" ]; then
        psql "$DATABASE_URL" --set=ON_ERROR_STOP=1 "$@"
        return
    fi
    psql \
        --host="${PGHOST:?PGHOST or DATABASE_URL is required}" \
        --port="${PGPORT:?PGPORT is required}" \
        --username="${PGUSER:?PGUSER is required}" \
        --dbname="${PGDATABASE:?PGDATABASE is required}" \
        --set=ON_ERROR_STOP=1 "$@"
}

psql_run <<'SQL'
create table if not exists public.schema_migrations (
    version text primary key,
    filename text not null unique,
    checksum_sha256 text not null,
    status text not null default 'APPLIED',
    applied_at timestamptz not null default now(),
    constraint schema_migrations_version_format check (version ~ '^[0-9]{4}$'),
    constraint schema_migrations_filename_format
        check (filename ~ '^[0-9]{4}_[a-z0-9_]+[.]sql$'),
    constraint schema_migrations_checksum_format check (checksum_sha256 ~ '^[0-9a-f]{64}$'),
    constraint schema_migrations_status_check check (status in ('APPLYING', 'APPLIED'))
);
SQL

ledger_records=$(psql_run --tuples-only --no-align --field-separator='|' <<'SQL'
select filename, checksum_sha256, status
from public.schema_migrations
order by version;
SQL
)

for migration in "$migration_directory"/*.sql; do
    filename=$(basename "$migration")
    printf '%s\n' "$filename" | grep -Eq '^[0-9]{4}_[a-z0-9_]+[.]sql$' || {
        echo "invalid migration filename: $filename" >&2
        exit 2
    }
    version=${filename%%_*}
    checksum=$(sha256sum "$migration" | cut -d ' ' -f 1)
    record=$(printf '%s\n' "$ledger_records" | awk -F '|' -v filename="$filename" \
        '$1 == filename { print $2 "|" $3 }')
    record=$(printf '%s' "$record" | tr -d '[:space:]')

    if [ -n "$record" ]; then
        recorded_checksum=${record%%|*}
        recorded_status=${record#*|}
        if [ "$recorded_checksum" != "$checksum" ]; then
            echo "checksum mismatch for $filename" >&2
            exit 1
        fi
        if [ "$recorded_status" != "APPLIED" ]; then
            echo "migration requires operator recovery: $filename is $recorded_status" >&2
            exit 1
        fi
        echo "Skipping $filename (already applied)"
        continue
    fi

    if [ "$mode" = "baseline" ]; then
        psql_run --set="migration_version=$version" --set="migration_filename=$filename" \
            --set="migration_checksum=$checksum" <<'SQL'
insert into public.schema_migrations (version, filename, checksum_sha256)
values (:'migration_version', :'migration_filename', :'migration_checksum');
SQL
        ledger_records="${ledger_records}${ledger_records:+
}${filename}|${checksum}|APPLIED"
        echo "Baselined $filename"
        continue
    fi

    psql_run --set="migration_version=$version" --set="migration_filename=$filename" \
        --set="migration_checksum=$checksum" <<'SQL'
insert into public.schema_migrations (version, filename, checksum_sha256, status)
values (:'migration_version', :'migration_filename', :'migration_checksum', 'APPLYING');
SQL
    echo "Applying $filename"
    psql_run --file="$migration"
    psql_run --set="migration_filename=$filename" <<'SQL'
update public.schema_migrations
set status = 'APPLIED', applied_at = now()
where filename = :'migration_filename' and status = 'APPLYING';
SQL
    ledger_records="${ledger_records}${ledger_records:+
}${filename}|${checksum}|APPLIED"
done
