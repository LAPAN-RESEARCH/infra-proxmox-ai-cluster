import io
import json
import time
import wave

import pytest

fastapi = pytest.importorskip("fastapi")


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("ESCUTA_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ESCUTA_RUN_DIR", str(tmp_path / "run"))
    monkeypatch.setenv("ESCUTA_ASR_BACKEND", "stub")
    monkeypatch.setenv("ESCUTA_LLM_BACKEND", "stub")
    monkeypatch.setenv("ESCUTA_UNLOAD_TITULAR_ON_JOB", "0")
    from fastapi.testclient import TestClient

    from escuta.api import app

    with TestClient(app) as c:
        yield c


def _wav_bytes(seconds=4.0, rate=16000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * int(seconds * rate))
    return buf.getvalue()


def _wait_job(client, cid, timeout_s=60):
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        job = client.get(f"/api/consultations/{cid}").json()["job"]
        if job and job["stage"] in ("concluido", "erro"):
            return job
        time.sleep(0.3)
    raise AssertionError("job não terminou")


def test_upload_flow_completo(client):
    resp = client.post(
        "/api/uploads",
        files={"file": ("consulta.wav", _wav_bytes(), "audio/wav")},
        data={"doctor_label": "dr-teste"},
    )
    assert resp.status_code == 200
    cid = resp.json()["id"]

    job = _wait_job(client, cid)
    assert job["stage"] == "concluido", job

    tr = client.get(f"/api/consultations/{cid}/transcript").json()
    assert "MEDICO" in tr["payload"]["dialogue"]

    soap = client.get(f"/api/consultations/{cid}/soap").json()
    assert set(soap["payload"]["soap"]) >= {"S", "O", "A", "P"}
    assert soap["payload"]["verificacao"]["sem_cobertura"]

    edit = client.put(f"/api/consultations/{cid}/soap", json={
        "S": "revisado", "O": "revisado", "A": "revisado", "P": "revisado",
        "created_by": "dr-teste"})
    assert edit.json()["version"] == 2

    assert client.post(f"/api/consultations/{cid}/sign", json={"signed_by": "dr-teste"}).json()["ok"]
    cons = client.get(f"/api/consultations/{cid}").json()["consultation"]
    assert cons["status"] == "assinada"

    audio_resp = client.get(f"/audio/{cid}")
    assert audio_resp.status_code == 200 and audio_resp.headers["content-type"].startswith("audio/")


def test_ws_live_flow(client):
    cid = client.post("/api/sessions", json={"doctor_label": "dr"}).json()["id"]
    with client.websocket_connect(f"/ws/stream/{cid}") as ws:
        ws.send_bytes(b"\x00\x00" * 8000)  # 0.5 s de silêncio simulado
        ws.send_text("stop")
        # mensagens: status (ao vivo degradado) e finalizada
        final = None
        for _ in range(4):
            msg = json.loads(ws.receive_text())
            if msg.get("type") == "finalizada":
                final = msg
                break
        assert final and final["consultation_id"] == cid

    job = _wait_job(client, cid)
    assert job["stage"] == "concluido"


def test_ws_rejects_wrong_token(tmp_path, monkeypatch):
    monkeypatch.setenv("ESCUTA_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ESCUTA_RUN_DIR", str(tmp_path / "run"))
    monkeypatch.setenv("ESCUTA_ASR_BACKEND", "stub")
    monkeypatch.setenv("ESCUTA_LLM_BACKEND", "stub")
    monkeypatch.setenv("ESCUTA_API_TOKEN", "segredo")
    from fastapi.testclient import TestClient

    from escuta.api import app

    with TestClient(app) as c:
        cid = c.post("/api/sessions", json={}, headers={"X-Escuta-Token": "segredo"}).json()["id"]
        with pytest.raises(Exception):
            with c.websocket_connect(f"/ws/stream/{cid}"):
                pass


def test_health(client):
    assert client.get("/api/health").json()["status"] == "ok"
    assert client.get("/").status_code == 200  # UI servida
