#!/bin/sh
# Wrapper do servidor MCP oficial do Neo4j Cypher.
#
# Resolve a senha a partir de NEO4J_AUTH (formato 'neo4j/senha') ou NEO4J_PASSWORD.
: "${NEO4J_URI:=bolt://neo4j:7687}"
: "${NEO4J_USERNAME:=neo4j}"
: "${NEO4J_PASSWORD:=${NEO4J_AUTH#*/}}"
: "${NEO4J_DATABASE:=neo4j}"

export NEO4J_URI NEO4J_USERNAME NEO4J_PASSWORD NEO4J_DATABASE

exec mcp-neo4j-cypher
