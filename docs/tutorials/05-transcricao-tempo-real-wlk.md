# Tutorial 05 — Transcrição em tempo real (WhisperLiveKit)

Transcrição **durante** a consulta (~1 s de latência), com separação de
falantes (diarização, máximo 2: médico × paciente), rodando na GPU do
hospital.

## Como funciona

```mermaid
sequenceDiagram
    actor U as Navegador na sala
    participant W as WhisperLiveKit :8010
    participant F as faster-whisper turbo (GPU)
    participant D as Sortformer (GPU)
    U->>W: WebSocket /asr?token=... (mic)
    loop cada janela de áudio (SimulStreaming)
        W->>F: áudio
        F-->>W: texto (prefixo confirmado)
        W->>D: áudio
        D-->>W: Speaker 1 / Speaker 2
        W-->>U: transcrição ao vivo com falante
    end
    U->>W: encerrar
    W-->>U: transcript diarizado final
```

## Usar sem programar (Web UI)

```bash
# 1. Túnel com a porta 8010 (tutorial 00 tem a linha completa)
ssh -L 8010:127.0.0.1:8010 hugo@lapan-ai
# 2. Abra http://localhost:8010
# 3. Informe o token (WLK_API_TOKEN do .env do hospital) e idioma pt
# 4. Clique no microfone e converse — rótulos Speaker 1/2 aparecem ao vivo
```

Funciona em qualquer navegador, inclusive tablet/celular do hospital se o
túnel estiver montado num computador da sala.

Outros clientes prontos (mesmo servidor): extensão Chrome do WLK
(transcreve o **áudio da aba**, com diarização) e o app macOS de referência
(`macos/WhisperLiveKitMac` no repo do projeto).

## Consumir via REST (upload, sem tempo real)

```bash
curl -X POST "http://localhost:8010/v1/audio/transcriptions" \
  -H "Authorization: Bearer $WLK_API_TOKEN" \
  -F file=@consulta.wav -F model=large-v3-turbo
```

## Consumir via WebSocket (integração própria)

```python
# pip install websockets
import asyncio, json, websockets

TOKEN = "seu-wlk-token"

async def main():
    uri = f"ws://127.0.0.1:8010/asr?token={TOKEN}&language=pt&model=large-v3-turbo"
    async with websockets.connect(uri) as ws:
        # envia chunks de 16 kHz mono s16le (ex.: de um arquivo/pipe)
        # e recebe o transcript em tempo real:
        async for msg in ws:
            data = json.loads(msg)
            segs = data.get("segments") or []
            for s in segs:
                who = s.get("speaker") or s.get("diarization") or "?"
                txt = s.get("text", "").strip()
                if txt:
                    print(f"[{who}] {txt}")

asyncio.run(main())
```

Dica: o parâmetro `mode=diff` na URL devolve apenas as mudanças (para
renderizar incrementalmente); sem ele, snapshot acumulado.

## Do transcript ao laudo

O transcript final (com `Speaker 1/2`) alimenta o prompt do tutorial 09
(`/soap` no Open WebUI, ou via API com o template
`configs/prompts/transcricao-para-laudo.md`). Identificar qual Speaker é o
médico ainda é manual; o enrollment por embeddings de voz (rotular
automaticamente Médico/Paciente) é a evolução planejada.

## Consumir de fora do hospital (OpenWhispr e afins)

O STT público é o próprio WLK, via LiteLLM (`model=whisper-1`, chave
virtual com allowlist de STT):

```bash
curl -X POST https://api.lapan.cloud/v1/audio/transcriptions \
  -H "Authorization: Bearer sk-CHAVE-VIRTUAL-STT" \
  -F file=@consulta.mp3 -F model=whisper-1
```

**OpenWhispr (ditado no desktop externo)** — Settings → Speech-to-Text →
provider **Custom** (repetir em cada aba usada: Dictation, Audio Upload):

| Campo | Valor |
|---|---|
| Endpoint URL | `https://api.lapan.cloud/v1` |
| API Key | chave virtual STT (alias `openwhispr`) |
| Model | `whisper-1` |

O polimento de texto (Settings → Language Models → Self-Hosted) pode usar
o modelo local: mesma Endpoint URL, chave virtual de LLM (alias
`openwhispr-llm`) e model `lapan`. Detalhe: OpenWhispr é push-to-talk
batch (não streaming) — tempo real é a Web UI acima.

## Limitações operacionais

- **VRAM**: durante a sessão, WLK usa ~3 GB. Se o modelo titular estiver
  carregado (~13 GB), o Ollama faz offload automático — em sessões longas,
  prefira transcrever com o chat parado.
- Diarização máxima de **2 falantes** (configurado para consultas); mudar
  requer `WLK_MAX_SPEAKERS` no `.env` e recreate.
- Áudio: 16 kHz mono recomendado; formatos comuns (wav/mp3/m4a) no REST.
