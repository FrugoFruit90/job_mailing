#!/bin/bash

# put the url below
export DATABASE_URL=""

# Ensure DATABASE_URL is set
if [[ -z "$DATABASE_URL" ]]; then
    echo "Error: DATABASE_URL is not set."
    exit 1
fi

# Normalize prefix (some URLs use postgresql:// instead of postgres://)
DATABASE_URL="${DATABASE_URL/postgresql:\/\//postgres://}"

# Parse DATABASE_URL (Expected format: postgres://user:password@host:port/database)
if [[ $DATABASE_URL =~ postgres://([^:]+):([^@]+)@([^:]+):([0-9]+)/(.+) ]]; then
    export PGUSER="${BASH_REMATCH[1]}"
    export PGPASSWORD="${BASH_REMATCH[2]}"
    export PGHOST="${BASH_REMATCH[3]}"
    export PGPORT="${BASH_REMATCH[4]}"
    export PGDATABASE="${BASH_REMATCH[5]}"

    echo "PostgreSQL environment variables loaded:"
    echo "PGUSER=$PGUSER"
    echo "PGHOST=$PGHOST"
    echo "PGPORT=$PGPORT"
    echo "PGDATABASE=$PGDATABASE"
else
    echo "Error: Invalid DATABASE_URL format."
    exit 1
fi
