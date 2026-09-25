import json

from escuta.db import Database


def make_db(tmp_path):
    return Database(tmp_path / "escuta.db")


def make_audio(tmp_path, name="a.wav", seconds=1.0, rate=16000):
    import wave

    p = tmp_path / name
    with wave.open(str(p), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * int(seconds * rate))
    return p


def test_consultation_lifecycle(tmp_path):
    db = make_db(tmp_path)
    cid = db.start_consultation("dr-teste", "upload")
    cons = db.get_consultation(cid)
    assert cons["status"] == "gravando"
    audio = make_audio(tmp_path)
    db.finish_consultation(cid, audio, 1.0)
    cons = db.get_consultation(cid)
    assert cons["status"] == "processando"
    assert cons["audio_sha256"] and len(cons["audio_sha256"]) == 64
    db.close()


def test_transcript_append_only_shape(tmp_path):
    db = make_db(tmp_path)
    cid = db.start_consultation(None, "upload")
    db.insert_transcript(cid, "m1", {"a": 1}, {"segments": []})
    db.insert_transcript(cid, "m2", {"a": 2}, {"segments": []})
    latest = db.latest_transcript(cid)
    assert latest["model"] == "m2"
    with db._lock:
        rows = db._conn.execute("SELECT COUNT(*) c FROM transcripts WHERE consultation_id=?", (cid,)).fetchone()
    assert rows["c"] == 2  # duas versões preservadas, nada sobrescrito
    db.close()


def test_soap_versions_and_sign(tmp_path):
    db = make_db(tmp_path)
    cid = db.start_consultation(None, "upload")
    v1 = db.insert_soap(cid, {"soap": {"S": "x"}})
    v2 = db.insert_soap(cid, {"soap": {"S": "y"}}, created_by="dr")
    assert (v2 - v1) == 1
    assert db.get_consultation(cid)["status"] == "revisao"
    assert db.sign_soap(cid, "dr assina")
    note = db.get_soap(cid)
    assert note["signed_by"] == "dr assina" and note["signed_at"]
    assert db.get_consultation(cid)["status"] == "assinada"
    db.close()


def test_roles_and_jobs(tmp_path):
    db = make_db(tmp_path)
    cid = db.start_consultation(None, "upload")
    db.set_roles(cid, {"SPEAKER_00": ("MEDICO", "heuristica", 0.8),
                       "SPEAKER_01": ("PACIENTE", "heuristica", 0.8)})
    roles = db.get_roles(cid)
    assert roles["SPEAKER_00"]["role"] == "MEDICO"
    db.enqueue_job(cid)
    db.job_update(cid, "asr", 0.5, "transcrevendo")
    job = db.get_job(cid)
    assert job["stage"] == "asr" and job["progress"] == 0.5
    assert db.pending_jobs() == []  # saiu da fila ao atualizar estágio
    cid2 = db.start_consultation(None, "upload")
    db.enqueue_job(cid2)
    assert db.pending_jobs() == [cid2]
    db.close()


def test_audit_trail_exists(tmp_path):
    db = make_db(tmp_path)
    cid = db.start_consultation(None, "upload")
    with db._lock:
        rows = db._conn.execute("SELECT event FROM audit ORDER BY id").fetchall()
    assert rows[0]["event"] == "consulta_iniciada"
    db.close()
