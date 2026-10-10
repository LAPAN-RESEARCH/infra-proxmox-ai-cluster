#!/bin/sh
# Wrapper do semantic-scholar-mcp.
#
# A chave SEMANTIC_SCHOLAR_API_KEY é opcional (vem do .env da stack via
# environment do container): sem ela o Semantic Scholar aplica limites de
# requisição anônimos, mais baixos. O wrapper apenas normaliza a variável
# para vazia quando ausente, evitando repassar strings literais "${...}".
: "${SEMANTIC_SCHOLAR_API_KEY:=}"
export SEMANTIC_SCHOLAR_API_KEY

exec semantic-scholar-mcp
