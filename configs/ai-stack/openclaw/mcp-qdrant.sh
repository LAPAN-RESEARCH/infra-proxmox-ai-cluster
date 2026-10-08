#!/bin/sh
# Wrapper do servidor MCP oficial do Qdrant.
#
# Conecta ao container Qdrant da rede lapan-ai-net com a coleção padrão.
: "${QDRANT_URL:=http://qdrant:6333}"
: "${COLLECTION_NAME:=research_chunks_bge_m3}"

export QDRANT_URL QDRANT_API_KEY COLLECTION_NAME

exec mcp-server-qdrant
