#!/bin/bash
# Creates the n8n database alongside the default litellm one.
# Note: during first-boot init the default database does not exist yet, so
# always connect explicitly to POSTGRES_DB.
set -euo pipefail
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
  SELECT 'CREATE DATABASE n8n'
  WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'n8n')\gexec
  GRANT ALL PRIVILEGES ON DATABASE n8n TO $POSTGRES_USER;
EOSQL
