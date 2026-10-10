# Automações (Cron) do OpenClaw

Automações são agendamentos persistentes do gateway: "nesta hora, entregue
este prompt ao agente". Elas sobrevivem a restarts (ficam no volume), rodam em
sessão isolada por padrão e têm histórico de execuções audível.

## Automações configuradas no LAPAN

Criadas por `scripts/openclaw_setup.sh` (idempotente por nome — rode a cada
deploy sem medo):

| Nome | Agenda (America/Sao_Paulo) | O que faz |
| --- | --- | --- |
| `varredura-literatura` | dias úteis, 06:00 | busca novas publicações nos temas prioritários (oculomics, ERG, TDAH/dislexia, IA clínica, instrumentos de saúde) via MCP `papers`/`arxiv`, aplica triagem IA-as-a-Judge e grava relatório em `~/workspace/literature-watch/AAAA-MM-DD.md` |
| `resumo-semanal-literatura` | segundas, 07:00 | compila a semana num resumo executivo (top 5 achados com veredito de evidência + 1 ação recomendada) em `literature-watch/semana-AAAA-SS.md` |

Onde saem os resultados: hoje, nos arquivos do workspace (consultáveis
pedindo ao agente "mostre a varredura de hoje"). Com o Telegram ativado
([03-plugins-e-skills.md](03-plugins-e-skills.md)), o resumo semanal pode ser
**entregue** no seu chat com `--announce --channel telegram`.

## Gestão pelo CLI

```bash
# listar e inspecionar
sudo docker exec openclaw openclaw automations list
sudo docker exec openclaw openclaw automations show varredura-literatura

# histórico de execuções (sucesso/falha de cada disparo)
sudo docker exec openclaw openclaw automations runs varredura-literatura

# pausar/retomar/remover
sudo docker exec openclaw openclaw automations pause <job-id>
sudo docker exec openclaw openclaw automations resume <job-id>
sudo docker exec openclaw openclaw automations remove <job-id>
```

## Como criar uma automação nova

```bash
sudo docker exec openclaw openclaw automations add \
  --name "meu-job" \
  --cron "0 7 * * 1-5" \
  --tz America/Sao_Paulo \
  --session isolated \
  --message 'Instrução clara para o agente: quais ferramentas usar (MCP papers,
arxiv...), onde gravar o resultado e o que fazer quando não houver novidades.'
```

Regras de ouro para o `--message` (que roda sem você por perto):

1. **Diga quais ferramentas usar** (`papers`, `zotero`...) — o job de cada
   disparo parte de contexto limpo.
2. **Diga onde gravar** (caminho no workspace) — o resultado precisa ser
   durável e auditável.
3. **Diga o que fazer no vazio** ("se não houver novidades, registre 'sem
   novidades'") — evita alucinação de resultados.

Outros payloads úteis: `--command "script.sh"` (determinístico, sem LLM —
ideal para checks que só avisam quando há problema) e `--script arquivo.js`
(código headless com ferramentas, para condições complexas). Agendas aceitam
cron 5 campos, `--every 30m`, ou timestamps absolutos.

## Custo e controle

Cada disparo é um turno completo de LLM (modelo do agente). A varredura diária
usa `gemini-2.5-pro` pela cadeia padrão — se quiser baratear, restrinja o job:
`openclaw automations edit varredura-literatura --model google/gemini-2.5-flash`.
