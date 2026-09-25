import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from escuta.config import Settings
from escuta.db import Database
from escuta.retention import cutoff_iso, purge_due


def _wave(p: Path, seconds: float = 1.0) -> Path:
    import wave

    with wave.open(str(p), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\x01\x00" * int(seconds * 16000))
    return p


def test_retention_purges_only_due_signed(tmp_path, monkeypatch):
    monkeypatch.setenv("ESCUTA_RETENTION_DAYS", "90")
    settings = Settings(data_dir=tmp_path, run_dir=tmp_path / "run")
    settings.ensure_dirs()
    db = Database(settings.db_path)

    # consulta assinada há 100 dias (vencida).
    old = db.start_consultation("dr", "upload")
    _wave(tmp_path / "old.wav")
    db.finish_consultation(old, tmp_path / "old.wav", 1.0)
    db.insert_soap(old, {"soap": {}})
    db.sign_soap(old, "dr")
    with db._lock, db._conn:
        db._conn.execute("UPDATE soap_notes SET signed_at=? WHERE consultation_id=?",
                         (cutoff_iso(datetime.now(timezone.utc), 99), old))

    # consulta assinada ontem (dentro da retenção).
    recent = db.start_consultation("dr", "upload")
    _wave(tmp_path / "recent.wav")
    db.finish_consultation(recent, tmp_path / "recent.wav", 1.0)
    db.insert_soap(recent, {"soap": {}})
    db.sign_soap(recent, "dr")

    # consulta não assinada (nunca expurga).
    unsigned = db.start_consultation("dr", "upload")
    _wave(tmp_path / "unsigned.wav")
    db.finish_consultation(unsigned, tmp_path / "unsigned.wav", 1.0)

    purged = purge_due(db, settings)
    assert [p["consultation_id"] for p in purged] == [old]
    assert not (tmp_path / "old.wav").exists()
    assert (tmp_path / "recent.wav").exists()
    assert (tmp_path / "unsigned.wav").exists()
    assert db.get_consultation(old)["audio_path"] is None

    with db._lock:
        events = [r["event"] for r in db._conn.execute("SELECT event FROM audit").fetchall()]
    assert "audio_expurgado" in events
    db.close()


def test_cutoff_iso_math():
    now = datetime(2026, 9, 24, tzinfo=timezone.utc)
    assert cutoff_iso(now, 90) == (now - timedelta(days=90)).isoformat(timespec="seconds")
