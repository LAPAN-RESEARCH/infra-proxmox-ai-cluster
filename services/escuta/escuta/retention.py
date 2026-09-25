"""Retenção e expurgo do áudio bruto (Pilar 7, decisão 2026-09-24).

Política: após a assinatura da SOAP, o áudio é retido por
ESCUTA_RETENTION_DAYS dias (90 no piloto; meta futura 0) e então removido
com sobrescrita segura. O transcript assinado permanece — é o registro.
"""
from __future__ import annotations

import os
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .config import Settings
from .db import Database


def cutoff_iso(now: datetime, retention_days: int) -> str:
    return (now - timedelta(days=retention_days)).isoformat(timespec="seconds")


def secure_delete(path: Path, passes: int = 2) -> None:
    """Sobrescreve com aleatório e remove; degrada para unlink se somente-leitura."""
    size = path.stat().st_size
    try:
        with open(path, "r+b") as fh:
            for _ in range(passes):
                fh.seek(0)
                fh.write(random.randbytes(min(size, 1 << 22)))
                fh.flush()
                os.fsync(fh.fileno())
    except OSError:
        pass
    path.unlink(missing_ok=True)


def purge_due(db: Database, settings: Settings, now: datetime | None = None) -> list[dict[str, Any]]:
    """Expurga áudios vencidos; devolve o que foi expurgado (para o runbook)."""
    now = now or datetime.now(timezone.utc)
    due = db.consultations_signed_before(cutoff_iso(now, settings.retention_days))
    purged = []
    for cons in due:
        path = Path(cons["audio_path"])
        if path.is_file():
            secure_delete(path)
        db.purge_audio_done(cons["id"])
        purged.append({"consultation_id": cons["id"], "audio": str(path)})
    return purged
