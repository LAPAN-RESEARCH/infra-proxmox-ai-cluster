# Tutorial 07 — Automações com n8n

n8n (`https://n8n.lapan.cloud`) orquestra: chat com documentos do Drive,
webhooks, agendamentos — sempre chamando o modelo local pela API com
**chave virtual**.

## Visão do fluxo "Consulta Drive → IA LAPAN" (já em produção)

```mermaid
flowchart LR
    U["Usuário no chat<br/>do n8n"] --> T["Chat Trigger"]
    T --> P["Preparar busca<br/>(extrai link/id ou nome)"]
    P --> G["Google Drive API<br/>(OAuth2)"]
    G --> S["Selecionar arquivo<br/>(prefere .md/.txt)"]
    S --> D["Baixar conteúdo"]
    D --> H["POST api.lapan.cloud<br/>(Bearer sk n8n-workflow)"]
    H --> M["gpt-oss:20b<br/>(hospital)"]
    M --> R["Resposta citada no chat"]
```

## Usar o chat de produção

Abra o workflow → nó **Chat Trigger** → "Chat URL" (produção). Mensagem:
primeiro termo = nome do arquivo no Drive, o resto = instrução.
Ex.: `2026-08-31_farnsworth-d15_085122.md Gere um laudo`.

## Criar uma nova automação que usa o modelo

1. Novo workflow → gatilho (Chat, Webhook, Schedule, Google Drive
   Trigger…).
2. Nó **HTTP Request**:
   - Method `POST`, URL `https://api.lapan.cloud/v1/chat/completions`
   - Authentication: *None* (a chave vai no header)
   - Headers: `Authorization: Bearer sk-CHAVE-VIRTUAL-DESTE-WORKFLOW`
   - Body (JSON): montar com `{{ JSON.stringify({...}) }}` — nunca
     interpolar texto do usuário direto no JSON (escapamento).
   - Model: `lapan`.
3. Para credenciais Google: Credentials → *Google Drive OAuth2 API* já
   existe ("Google Drive (LAPAN)"); conecte sua conta no botão *Connect*.
4. Publique (**Publish/Active**) — no n8n 2.3x, webhook de produção só
   registra na publicação.

## Boas práticas

- **Uma chave virtual por workflow** (alias = nome do workflow) — facilita
  auditar e revogar (tutorial 02).
- Execução com dados clínicos: desabilite *Save execution progress* e
  limpe execuções antigas (n8n guarda payloads por padrão no VPS).
- Erros do nó HTTP: 401 = chave, 429 = limite da chave, 504 = modelo frio —
  ative *On Error → Continue* + nó de resposta amigável quando o workflow
  for voltado a leigos.

## Importar/exportar workflows versionados

No repo: `configs/vps/n8n-workflow-drive.json` (com `__N8N_KEY__` no lugar
da chave). Para restaurar/instalar:

```bash
sed 's/__N8N_KEY__/sk-CHAVE-REAL/' configs/vps/n8n-workflow-drive.json > /tmp/wf.json
scp /tmp/wf.json root@lapan-vps:/srv/vps/n8n/files/
ssh root@lapan-vps 'chown 1000:1000 /srv/vps/n8n/files/wf.json && \
  docker exec lapan-n8n n8n import:workflow --input=/files/wf.json'
```

A versão com a chave real também está no backup local
(`lapan-vps/n8n-files/n8n-wf.json`).
