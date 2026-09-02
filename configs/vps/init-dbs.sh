#!/bin/bash
# Creates the n8n database alongside the default litellm one.
set -euo pipefail
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" <<-EOSQL
  CREATE DATABASE n8n;
  GRANT ALL PRIVILEGES ON DATABASE n8n TO $POSTGRES_USER;
EOSQL
