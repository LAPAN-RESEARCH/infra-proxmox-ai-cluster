"""API da escuta clínica: dois cliques, gravação servidor-side, progresso em
background e revisão em tela dividida (Pilar 6 do plano).

- `POST /api/sessions` + `WS /ws/stream/{id}`: captura no navegador (PCM 16k
  Int16 via AudioWorklet) -> o SERVIDOR grava (aba pode cair) e repassa ao
  WhisperLiveKit para transcrição ao vivo (degrada para só-gravação se o WLK
  estiver fora).
- `POST /api/uploads`: alternativa por arquivo (corpus real futuro, imports).
- `GET /api/consultations/{id}/...`: job/transcript/SOAP; SSE em
  `/api/jobs/{id}/events`.
- Revisão: PUT da SOAP (nova versão), assinatura, troca de papéis com
  regeneração, enrollment do médico a partir da consulta.

Auth opcional: `ESCUTA_API_TOKEN` (header `X-Escuta-Token`; WS via `?token=`).
Padrão do hospital: bind 127.0.0.1 + túnel SSH.
"""
from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import audio
from .config import Settings
from .db import Database
from .worker import ScribeWorker

STATIC_DIR = Path(__file__).resolve().parent / "static"
TERMINAL_STAGES = {"concluido", "erro"}


def _token() -> str | None:
    return os.environ.get("ESCUTA_API_TOKEN") or None


def check_token(x_escuta_token: str | None = Header(default=None)) -> None:
    tok = _token()
    if tok and x_escuta_token != tok:
        raise HTTPException(status_code=401, detail="token inválido")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings()
    settings.ensure_dirs()
    db = Database(settings.db_path)
    worker = ScribeWorker(db, settings)
    worker.start()
    app.state.settings = settings
    app.state.db = db
    app.state.worker = worker
    try:
        yield
    finally:
        worker.stop()
        db.close()


app = FastAPI(title="Escuta Clínica LAPAN", version="0.1.0", lifespan=lifespan)


def _db(request) -> Database:
    return request.app.state.db


def _worker(request) -> ScribeWorker:
    return request.app.state.worker


def _settings(request) -> Settings:
    return request.app.state.settings


# --------------------------------------------------------------------------- #
# Sessão / gravação
# --------------------------------------------------------------------------- #

@app.post("/api/sessions", dependencies=[Depends(check_token)])
async def start_session(payload: dict, request: Request) -> dict:
    cid = _db(request).start_consultation(payload.get("doctor_label"), origin="server-ws")
    return {"id": cid, "ws": f"/ws/stream/{cid}"}


@app.websocket("/ws/stream/{cid}")
async def ws_stream(ws: WebSocket, cid: str) -> None:
    tok = _token()
    if tok and ws.query_params.get("token") != tok:
        await ws.close(code=4401)
        return
    await ws.accept()
    db: Database = ws.app.state.db
    settings: Settings = ws.app.state.settings
    cons = db.get_consultation(cid)
    if not cons or cons["status"] != "gravando":
        await ws.send_json({"type": "erro", "msg": "sessão inexistente ou já finalizada"})
        await ws.close()
        return

    raw_wav = settings.audio_dir / f"{cid}.raw.wav"
    acc = audio.WavAccumulator(raw_wav)

    wlk = None
    pump: asyncio.Task | None = None
    wlk_token = settings.env_secret(settings.wlk_token_env) or ""
    url = f"{settings.wlk_url}?token={wlk_token}&language=pt&mode=diff"
    try:
        import websockets

        wlk = await websockets.connect(url, max_size=None, ping_interval=10)

        async def relay() -> None:
            try:
                async for msg in wlk:
                    await ws.send_text(msg if isinstance(msg, str) else msg.decode())
            except Exception:
                pass

        pump = asyncio.create_task(relay())
        await ws.send_json({"type": "status", "live": True})
    except Exception:
        await ws.send_json({"type": "status", "live": False,
                            "msg": "transcrição ao vivo indisponível — gravação segue normal"})

    try:
        while True:
            msg = await ws.receive()
            if msg["type"] == "websocket.disconnect":
                break
            data = msg.get("bytes")
            if data:
                acc.write(data)
                if wlk is not None:
                    try:
                        await wlk.send(data)
                    except Exception:
                        pass
            elif msg.get("text") == "stop":
                break
    except WebSocketDisconnect:
        pass
    finally:
        if pump:
            pump.cancel()
        if wlk is not None:
            try:
                await wlk.close()
            except Exception:
                pass
        duration = acc.close()
        finalizada = _finalize(db, settings, cid, raw_wav, duration)
        try:
            await ws.send_json({"type": "finalizada", "duration_s": duration, **finalizada})
            await ws.close()
        except Exception:
            pass


def _finalize(db: Database, settings: Settings, cid: str, raw_wav: Path,
              duration: float) -> dict:
    """Transcodifica para Opus (armazenamento/retenção) e enfileira o job."""
    try:
        opus = audio.encode_opus(raw_wav, settings.audio_dir / f"{cid}.opus")
        raw_wav.unlink(missing_ok=True)
        db.finish_consultation(cid, opus, duration)
    except Exception as exc:  # ffmpeg ausente: mantém wav e segue
        db.finish_consultation(cid, raw_wav, duration)
        opus = None
    db.enqueue_job(cid)
    return {"consultation_id": cid}


@app.post("/api/uploads", dependencies=[Depends(check_token)])
async def upload(file: UploadFile, request: Request, doctor_label: str | None = None) -> dict:
    db, settings = _db(request), _settings(request)
    cid = db.start_consultation(doctor_label, origin="upload")
    raw = settings.audio_dir / f"{cid}{Path(file.filename or 'a.wav').suffix}"
    raw.write_bytes(await file.read())
    tmp_wav = settings.data_dir / "tmp" / f"{cid}-up.wav"
    try:
        wav = audio.decode_to_wav16k(raw, tmp_wav)
        duration = audio.wav_duration_s(wav)
        opus = audio.encode_opus(wav, settings.audio_dir / f"{cid}.opus")
        db.finish_consultation(cid, opus, duration)
        raw.unlink(missing_ok=True)
        wav.unlink(missing_ok=True)
    except Exception:
        db.job_error(cid, f"formato de áudio não processável: {file.filename}")
        raise HTTPException(status_code=400, detail="áudio não processável")
    db.enqueue_job(cid)
    return {"id": cid}


# --------------------------------------------------------------------------- #
# Consulta / job / revisão
# --------------------------------------------------------------------------- #

@app.get("/api/consultations/{cid}", dependencies=[Depends(check_token)])
async def get_consultation(cid: str, request: Request) -> dict:
    cons = _db(request).get_consultation(cid)
    if not cons:
        raise HTTPException(status_code=404, detail="consulta não encontrada")
    return {"consultation": cons, "job": _db(request).get_job(cid)}


@app.get("/api/consultations/{cid}/transcript", dependencies=[Depends(check_token)])
async def get_transcript(cid: str, request: Request) -> dict:
    row = _db(request).latest_transcript(cid)
    if not row:
        raise HTTPException(status_code=404, detail="sem transcript")
    return {"created_at": row["created_at"], "model": row["model"],
            "sha256": row["sha256"], "payload": json.loads(row["payload_json"]),
            "roles": _db(request).get_roles(cid)}


@app.get("/api/consultations/{cid}/soap", dependencies=[Depends(check_token)])
async def get_soap(cid: str, request: Request) -> dict:
    row = _db(request).get_soap(cid)
    if not row:
        raise HTTPException(status_code=404, detail="sem SOAP")
    return {"version": row["version"], "created_at": row["created_at"],
            "signed_by": row["signed_by"], "signed_at": row["signed_at"],
            "payload": json.loads(row["payload_json"])}


@app.put("/api/consultations/{cid}/soap", dependencies=[Depends(check_token)])
async def edit_soap(cid: str, payload: dict, request: Request) -> dict:
    soap = {k: payload.get(k) for k in ("S", "O", "A", "P") if payload.get(k)}
    if not soap:
        raise HTTPException(status_code=422, detail="SOAP vazia")
    previous = _db(request).get_soap(cid)
    merged = json.loads(previous["payload_json"]) if previous else {}
    merged["soap"] = soap
    if payload.get("laudo"):
        merged["laudo"] = payload["laudo"]
    version = _db(request).insert_soap(cid, merged, created_by=payload.get("created_by") or "medico")
    return {"version": version}


@app.post("/api/consultations/{cid}/sign", dependencies=[Depends(check_token)])
async def sign(cid: str, payload: dict, request: Request) -> dict:
    signed_by = payload.get("signed_by") or "medico"
    if not _db(request).sign_soap(cid, signed_by):
        raise HTTPException(status_code=404, detail="sem SOAP para assinar")
    return {"ok": True, "signed_by": signed_by}


@app.post("/api/consultations/{cid}/roles/swap", dependencies=[Depends(check_token)])
async def swap_roles(cid: str, background: BackgroundTasks, request: Request) -> dict:
    if not _db(request).latest_transcript(cid):
        raise HTTPException(status_code=404, detail="sem transcript")
    _db(request).audit("medico", "troca_papeis_solicitada", {"consultation_id": cid})
    background.add_task(_worker(request).regenerate, cid, True)
    return {"ok": True, "msg": "regenerando com papéis invertidos"}


@app.post("/api/consultations/{cid}/soap/regenerate", dependencies=[Depends(check_token)])
async def regenerate(cid: str, background: BackgroundTasks, request: Request) -> dict:
    background.add_task(_worker(request).regenerate, cid, False)
    return {"ok": True}


@app.post("/api/consultations/{cid}/enrollment", dependencies=[Depends(check_token)])
async def enrollment(cid: str, request: Request) -> dict:
    ok = _worker(request).enroll_doctor(cid)
    return {"ok": ok, "msg": "enrollment do médico atualizado" if ok else
            "enrollment indisponível (requer speechbrain) ou sem turno do médico"}


@app.get("/api/jobs/{cid}/events", dependencies=[Depends(check_token)])
async def job_events(cid: str, request: Request) -> StreamingResponse:
    db = _db(request)

    async def gen():
        last = None
        while True:
            job = db.get_job(cid)
            if job != last:
                last = job
                yield f"data: {json.dumps(job, ensure_ascii=False)}\n\n"
                if job and job.get("stage") in TERMINAL_STAGES:
                    return
            await asyncio.sleep(1.0)

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/audio/{cid}", dependencies=[Depends(check_token)])
async def get_audio(cid: str, request: Request):
    cons = _db(request).get_consultation(cid)
    if not cons or not cons["audio_path"]:
        raise HTTPException(status_code=404, detail="áudio indisponível (expurgado ou inexistente)")
    path = Path(cons["audio_path"])
    if not path.is_file():
        raise HTTPException(status_code=404, detail="áudio não encontrado")
    media = "audio/ogg" if path.suffix == ".opus" else "audio/wav"
    return FileResponse(path, media_type=media, filename=path.name)


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "version": app.version}


# UI (dois cliques) e arquivos estáticos.
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")
