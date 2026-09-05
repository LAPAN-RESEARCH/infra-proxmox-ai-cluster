# Tutorial 01 — API pública: quickstart

## O caminho da requisição

```mermaid
flowchart LR
    A["Seu app<br/>(curl, Python, JS...)"] -->|"POST https://api.lapan.cloud/v1/...<br/>Authorization: Bearer sk-virtual"| B["Traefik<br/>TLS + rate-limit 30 rpm"]
    B --> C["LiteLLM Proxy<br/>valida chave virtual<br/>(budget, rpm, modelos)"]
    C -->|"tailnet-only, TLS ts.net<br/>Bearer AI_API_KEY"| D["ai-api (hospital)<br/>RAG opcional + citações"]
    D --> E["Ollama gpt-oss:20b<br/>(GPU no hospital)"]
    E --> D --> C --> B --> A
    C -.->|"só metadados<br/>(LGPD)"| F[("Postgres<br/>spend por chave")]
```

Conteúdo (prompts/respostas) **nunca** é gravado no VPS — só metadados.

## Primeira chamada (30 segundos)

```bash
curl https://api.lapan.cloud/v1/chat/completions \
  -H "Authorization: Bearer sk-SUA-CHAVE-VIRTUAL" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "lapan",
    "messages": [
      {"role": "system", "content": "Você é assistente clínico do LAPAN."},
      {"role": "user", "content": "Liste 3 causas de olho vermelho sem dor."}
    ],
    "max_tokens": 400
  }'
```

## Modelos disponíveis

| `model` na chamada | O que atende | Uso típico |
|---|---|---|
| `lapan` | `gpt-oss:20b` (titular) | laudos, chat, extração |
| `lapan/gemma4:26b` | gemma4:26b | alternativa de qualidade |
| `lapan/qwen3.8:27b` | qwen3.8:27b | batch lento (8 tok/s), contexto longo |
| `lapan/qwen3:8b` | qwen3:8b | tarefas leves/ferramentas |
| `lapan/qwen2.5-coder:7b` | coder | código |

Listar ao vivo: `curl https://api.lapan.cloud/v1/models -H "Authorization: Bearer sk-..."`.

## Streaming (texto aparecendo aos poucos)

```bash
curl -N https://api.lapan.cloud/v1/chat/completions \
  -H "Authorization: Bearer sk-SUA-CHAVE-VIRTUAL" \
  -H "Content-Type: application/json" \
  -d '{"model":"lapan","stream":true,
       "messages":[{"role":"user","content":"Escreva um parágrafo sobre ceratocone."}]}'
```

Saída: SSE (`data: {...}` por linha, terminando em `data: [DONE]`).

## Códigos de erro que importam

| HTTP | Causa | O que fazer |
|---|---|---|
| 401 | chave inválida/bloqueada | conferir chave; ver tutorial 02 |
| 429 | rpm/budget estourados ou VPS rate-limit | reduzir ritmo ou pedir limite maior |
| 502/504 | modelo demorou (frio/offload) | repetir; ver troubleshooting 10 |

## E agora

- Integrar na sua linguagem: tutorial 03 (SDK OpenAI).
- Criar/gerir chaves por consumidor: tutorial 02.
- Enviar áudio (arquivo) para transcrição: tutorial 06 — mesmo endpoint
  base, rota `/v1/audio/transcriptions`.
