"""Banco SQLite (WAL): consultas, transcripts imutáveis, SOAP versionada,
jobs, enrollment e trilha de auditoria.

Invariantes do plano (seção 8 do plano de escuta clínica):
- `transcripts` é append-only: o INSERT existe, UPDATE/DELETE não.
- `soap_notes` é versionada: cada revisão é uma linha nova.
- áudio é referenciado por SHA-256; expurgo registra evento de auditoria.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS consultations (
  id TEXT PRIMARY KEY,
  started_at TEXT NOT NULL,
  ended_at TEXT,
  status TEXT NOT NULL DEFAULT 'gravando',   -- gravando|processando|revisao|assinada|erro
  doctor_label TEXT,
  audio_path TEXT,
  audio_sha256 TEXT,
  audio_duration_s REAL,
  origin TEXT NOT NULL DEFAULT 'server-ws'   -- server-ws|upload
);
CREATE TABLE IF NOT EXISTS transcripts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  consultation_id TEXT NOT NULL REFERENCES consultations(id),
  created_at TEXT NOT NULL,
  model TEXT NOT NULL,
  params_json TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  sha256 TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS soap_notes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  consultation_id TEXT NOT NULL REFERENCES consultations(id),
  version INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  created_by TEXT NOT NULL DEFAULT 'sistema',
  payload_json TEXT NOT NULL,               -- {S,O,A,P,laudo,verificacao,...}
  signed_by TEXT,
  signed_at TEXT,
  UNIQUE (consultation_id, version)
);
CREATE TABLE IF NOT EXISTS speaker_roles (
  consultation_id TEXT NOT NULL REFERENCES consultations(id),
  speaker TEXT NOT NULL,
  role TEXT NOT NULL,                       -- MEDICO|PACIENTE
  source TEXT NOT NULL,                     -- enrollment|heuristica|llm|manual
  confidence REAL NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  PRIMARY KEY (consultation_id, speaker)
);
CREATE TABLE IF NOT EXISTS enrollments (
  speaker_label TEXT PRIMARY KEY,
  embedding BLOB NOT NULL,
  n_samples INTEGER NOT NULL DEFAULT 1,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS jobs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  consultation_id TEXT NOT NULL REFERENCES consultations(id),
  stage TEXT NOT NULL,                      -- fila|asr|diarizacao|papeis|soap|concluido|erro
  progress REAL NOT NULL DEFAULT 0,
  detail TEXT,
  error TEXT,
  updated_at TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  actor TEXT NOT NULL,
  event TEXT NOT NULL,
  details_json TEXT
);
"""


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class Database:
    """Wrapper thread-safe de um SQLite WAL (worker e API no mesmo processo)."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        with self._lock, self._conn:
            self._conn.executescript(SCHEMA)

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # -- consultas ----------------------------------------------------------
    def start_consultation(self, doctor_label: str | None, origin: str) -> str:
        cid = new_id()
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO consultations (id, started_at, status, doctor_label, origin) VALUES (?,?,?,?,?)",
                (cid, utcnow(), "gravando", doctor_label, origin),
            )
        self.audit("sistema", "consulta_iniciada", {"consultation_id": cid, "origin": origin})
        return cid

    def finish_consultation(self, cid: str, audio_path: Path, duration_s: float) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE consultations SET ended_at=?, status='processando', audio_path=?,"
                " audio_sha256=?, audio_duration_s=? WHERE id=?",
                (utcnow(), str(audio_path), sha256_file(audio_path), duration_s, cid),
            )
        self.audit("sistema", "audio_registrado", {"consultation_id": cid, "duration_s": duration_s})

    def set_status(self, cid: str, status: str) -> None:
        with self._lock, self._conn:
            self._conn.execute("UPDATE consultations SET status=? WHERE id=?", (status, cid))

    def get_consultation(self, cid: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM consultations WHERE id=?", (cid,)).fetchone()
        return dict(row) if row else None

    def consultations_signed_before(self, cutoff_iso: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT c.* FROM consultations c JOIN soap_notes n ON n.consultation_id=c.id"
                " WHERE n.signed_at IS NOT NULL AND n.signed_at < ?"
                " AND c.audio_path IS NOT NULL", (cutoff_iso,),
            ).fetchall()
        return [dict(r) for r in rows]

    # -- transcript (append-only) -------------------------------------------
    def insert_transcript(self, cid: str, model: str, params: dict, payload: dict) -> None:
        blob = json.dumps(payload, ensure_ascii=False)
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO transcripts (consultation_id, created_at, model, params_json, payload_json, sha256)"
                " VALUES (?,?,?,?,?,?)",
                (cid, utcnow(), model, json.dumps(params), blob, hashlib.sha256(blob.encode()).hexdigest()),
            )
        self.audit("sistema", "transcript_registrado", {"consultation_id": cid, "model": model})

    def latest_transcript(self, cid: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM transcripts WHERE consultation_id=? ORDER BY id DESC LIMIT 1",
                (cid,),
            ).fetchone()
        return dict(row) if row else None

    # -- SOAP versionada ------------------------------------------------------
    def insert_soap(self, cid: str, payload: dict, created_by: str = "sistema") -> int:
        with self._lock, self._conn:
            (version,) = self._conn.execute(
                "SELECT COALESCE(MAX(version),0)+1 FROM soap_notes WHERE consultation_id=?", (cid,)
            ).fetchone()
            cur = self._conn.execute(
                "INSERT INTO soap_notes (consultation_id, version, created_at, created_by, payload_json)"
                " VALUES (?,?,?,?,?)",
                (cid, version, utcnow(), created_by, json.dumps(payload, ensure_ascii=False)),
            )
            self._conn.execute("UPDATE consultations SET status='revisao' WHERE id=?", (cid,))
        self.audit(created_by, "soap_version_criada", {"consultation_id": cid, "version": version})
        return int(cur.lastrowid)

    def update_soap_payload(self, cid: str, version: int, payload: dict) -> None:
        # Edição humana cria nova versão; aqui só o worker ajusta a versão corrente.
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE soap_notes SET payload_json=? WHERE consultation_id=? AND version=?",
                (json.dumps(payload, ensure_ascii=False), cid, version),
            )

    def get_soap(self, cid: str, version: int | None = None) -> dict[str, Any] | None:
        q = "SELECT * FROM soap_notes WHERE consultation_id=?"
        args: tuple = (cid,)
        if version is not None:
            q += " AND version=?"
            args = (cid, version)
        q += " ORDER BY version DESC LIMIT 1"
        with self._lock:
            row = self._conn.execute(q, args).fetchone()
        return dict(row) if row else None

    def sign_soap(self, cid: str, signed_by: str) -> bool:
        note = self.get_soap(cid)
        if not note:
            return False
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE soap_notes SET signed_by=?, signed_at=? WHERE consultation_id=? AND version=?",
                (signed_by, utcnow(), cid, note["version"]),
            )
            self._conn.execute("UPDATE consultations SET status='assinada' WHERE id=?", (cid,))
        self.audit(signed_by, "soap_assinada", {"consultation_id": cid, "version": note["version"]})
        return True

    # -- papéis ---------------------------------------------------------------
    def set_roles(self, cid: str, roles: dict[str, tuple[str, str, float]]) -> None:
        """roles: speaker -> (papel, origem, confiança)."""
        with self._lock, self._conn:
            self._conn.execute("DELETE FROM speaker_roles WHERE consultation_id=?", (cid,))
            for speaker, (role, source, conf) in roles.items():
                self._conn.execute(
                    "INSERT INTO speaker_roles (consultation_id, speaker, role, source, confidence, created_at)"
                    " VALUES (?,?,?,?,?,?)", (cid, speaker, role, source, conf, utcnow()),
                )
        self.audit("sistema", "papeis_definidos", {"consultation_id": cid, "roles": {
            k: v[0] for k, v in roles.items()}})

    def get_roles(self, cid: str) -> dict[str, dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM speaker_roles WHERE consultation_id=?", (cid,)).fetchall()
        return {r["speaker"]: dict(r) for r in rows}

    # -- enrollment -------------------------------------------------------------
    def save_enrollment(self, label: str, embedding: bytes, n_samples: int) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO enrollments (speaker_label, embedding, n_samples, updated_at) VALUES (?,?,?,?)"
                " ON CONFLICT(speaker_label) DO UPDATE SET embedding=excluded.embedding,"
                " n_samples=excluded.n_samples, updated_at=excluded.updated_at",
                (label, embedding, n_samples, utcnow()),
            )
        self.audit("sistema", "enrollment_atualizado", {"label": label, "n_samples": n_samples})

    def get_enrollment(self, label: str) -> tuple[bytes, int] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT embedding, n_samples FROM enrollments WHERE speaker_label=?", (label,)
            ).fetchone()
        return (row["embedding"], row["n_samples"]) if row else None

    # -- jobs ---------------------------------------------------------------------
    def enqueue_job(self, cid: str) -> int:
        with self._lock, self._conn:
            cur = self._conn.execute(
                "INSERT INTO jobs (consultation_id, stage, updated_at, created_at) VALUES (?,?,?,?)",
                (cid, "fila", utcnow(), utcnow()),
            )
        return int(cur.lastrowid)

    def job_update(self, cid: str, stage: str, progress: float, detail: str | None = None,
                   error: str | None = None) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE jobs SET stage=?, progress=?, detail=?, error=?, updated_at=?"
                " WHERE consultation_id=? AND id=(SELECT MAX(id) FROM jobs WHERE consultation_id=?)",
                (stage, progress, detail, error, utcnow(), cid, cid),
            )

    def job_error(self, cid: str, error: str) -> None:
        self.job_update(cid, "erro", 0.0, None, error[:2000])
        self.set_status(cid, "erro")

    def get_job(self, cid: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM jobs WHERE consultation_id=? ORDER BY id DESC LIMIT 1", (cid,)
            ).fetchone()
        return dict(row) if row else None

    def pending_jobs(self) -> list[str]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT DISTINCT consultation_id FROM jobs WHERE stage IN ('fila') ORDER BY id"
            ).fetchall()
        return [r["consultation_id"] for r in rows]

    # -- auditoria -----------------------------------------------------------------
    def audit(self, actor: str, event: str, details: dict | None = None) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO audit (ts, actor, event, details_json) VALUES (?,?,?,?)",
                (utcnow(), actor, event, json.dumps(details, ensure_ascii=False) if details else None),
            )

    def purge_audio_done(self, cid: str) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE consultations SET audio_path=NULL, audio_sha256=NULL WHERE id=?", (cid,)
            )
        self.audit("sistema", "audio_expurgado", {"consultation_id": cid, "at": utcnow()})


# Reexport para o worker medir passos com relógio monotônico quando útil.
monotonic = time.monotonic
