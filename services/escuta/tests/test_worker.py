import json

import pytest

from escuta.config import Settings
from escuta.db import Database
from escuta.speakers import _pack_embedding, _unpack_embedding, cosine
from escuta.worker import ScribeWorker


def _wave(p, seconds=6.0):
    import wave

    with wave.open(str(p), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\x00\x00" * int(seconds * 16000))
    return p


def _make_worker(tmp_path, monkeypatch):
    monkeypatch.setenv("ESCUTA_ASR_BACKEND", "stub")
    monkeypatch.setenv("ESCUTA_LLM_BACKEND", "stub")
    monkeypatch.setenv("ESCUTA_UNLOAD_TITULAR_ON_JOB", "0")
    s = Settings(data_dir=tmp_path, run_dir=tmp_path / "run")
    s.ensure_dirs()
    db = Database(s.db_path)
    return ScribeWorker(db, s), db, s


def test_worker_end_to_end_consenso(tmp_path, monkeypatch):
    w, db, s = _make_worker(tmp_path, monkeypatch)
    cid = db.start_consultation("dr", "upload")
    db.finish_consultation(cid, _wave(tmp_path / "c.wav"), 6.0)
    db.enqueue_job(cid)
    w.process(cid)

    job = db.get_job(cid)
    assert job["stage"] == "concluido" and job["progress"] == 1.0

    transcript = db.latest_transcript(cid)
    payload = json.loads(transcript["payload_json"])
    assert payload["diarizacao_ativa"] is True
    assert payload["divergencia_papeis"] == []
    assert "MEDICO" in payload["dialogue"] and "PACIENTE" in payload["dialogue"]
    roles = {sp: r["role"] for sp, r in db.get_roles(cid).items()}
    assert roles["SPEAKER_00"] == "MEDICO" and roles["SPEAKER_01"] == "PACIENTE"

    note = db.get_soap(cid)
    data = json.loads(note["payload_json"])
    assert set(data["soap"]) >= {"S", "O", "A", "P"}
    assert "CID" in data["laudo"]
    assert data["verificacao"]["sem_cobertura"]
    db.close()


def test_worker_divergencia_de_papeis_registrada(tmp_path, monkeypatch):
    w, db, s = _make_worker(tmp_path, monkeypatch)
    # LLM "discorda": inverte os papéis da heurística.
    w.llm.verify_roles = lambda dialogue, speakers: {
        "SPEAKER_00": "PACIENTE", "SPEAKER_01": "MEDICO"}
    cid = db.start_consultation("dr", "upload")
    db.finish_consultation(cid, _wave(tmp_path / "c.wav"), 6.0)
    db.enqueue_job(cid)
    w.process(cid)

    payload = json.loads(db.latest_transcript(cid)["payload_json"])
    assert set(payload["divergencia_papeis"]) == {"SPEAKER_00", "SPEAKER_01"}
    assert db.get_job(cid)["detail"] == "confirmar papéis"
    db.close()


def test_regenerate_with_role_swap(tmp_path, monkeypatch):
    w, db, s = _make_worker(tmp_path, monkeypatch)
    cid = db.start_consultation("dr", "upload")
    db.finish_consultation(cid, _wave(tmp_path / "c.wav"), 6.0)
    db.enqueue_job(cid)
    w.process(cid)

    w.regenerate(cid, swap=True)
    roles = {sp: r["role"] for sp, r in db.get_roles(cid).items()}
    assert roles["SPEAKER_00"] == "PACIENTE" and roles["SPEAKER_01"] == "MEDICO"
    v2 = db.get_soap(cid)
    assert v2["version"] == 2 and v2["created_by"] == "sistema"
    # transcript original permanece imutável (registro médico-legal do Pilar 5):
    dialogue = json.loads(db.latest_transcript(cid)["payload_json"])["dialogue"]
    assert "[00:00] MEDICO:" in dialogue
    db.close()


def test_worker_error_vira_estado_de_job(tmp_path, monkeypatch):
    w, db, s = _make_worker(tmp_path, monkeypatch)
    w.asr.transcribe = lambda p: (_ for _ in ()).throw(RuntimeError("GPU sumiu"))
    cid = db.start_consultation("dr", "upload")
    db.finish_consultation(cid, _wave(tmp_path / "c.wav"), 6.0)
    db.enqueue_job(cid)
    w.process(cid)
    job = db.get_job(cid)
    assert job["stage"] == "erro" and "GPU sumiu" in job["error"]
    db.close()


def test_embedding_pack_roundtrip_and_cosine():
    vec = [0.1, 0.2, 0.3, -0.4]
    blob = _pack_embedding(vec)
    assert _unpack_embedding(blob) == pytest.approx(vec, rel=1e-6)
    assert cosine(vec, vec) > 0.99
    assert cosine(vec, [-x for x in vec]) < -0.99
    assert cosine([], []) == -1.0
