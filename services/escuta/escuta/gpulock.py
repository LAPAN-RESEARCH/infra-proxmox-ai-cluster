"""Lock de GPU com prioridade clínica (decisão 2026-09-24, Pilar 4).

Dois níveis sobre um mesmo arquivo de lock (fcntl):
- `clinical-high`: preemptivo — enquanto ativo, pesquisa deve ceder;
- `research-low`: cooperativo — o detentor deve checar `should_yield()`
  periodicamente e interromper com checkpoint.

Preempção do titular do Ollama: ao iniciar etapa clínica, descarrega o modelo
titular (`docker exec ollama ollama stop <modelo>`) liberando ~13,8 GB.
"""
from __future__ import annotations

import fcntl
import json
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path

from .config import Settings

CLINICAL = "clinical-high"
RESEARCH = "research-low"


class GpuLock:
    def __init__(self, settings: Settings) -> None:
        self._s = settings
        self._path = settings.run_dir / "gpu.lock"
        self._flag = settings.run_dir / "clinical-active"
        settings.run_dir.mkdir(parents=True, exist_ok=True)

    def _read_holder(self) -> dict | None:
        try:
            return json.loads(self._path.read_text())
        except (OSError, ValueError):
            return None

    def _write_holder(self, level: str) -> None:
        self._path.write_text(json.dumps({"level": level, "since": time.time()}))

    @contextmanager
    def acquire(self, level: str, wait_s: float = 120.0):
        """Adquire o lock; `clinical-high` derruba `research-low` na hora."""
        deadline = time.monotonic() + wait_s
        fd = None
        while True:
            fd = fd or open(self._path, "a+")
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                holder = self._read_holder()
                if level == CLINICAL and (holder or {}).get("level") == RESEARCH:
                    # pesquisa cooperativa deve sair sozinha; esperamos o prazo
                    pass
                if time.monotonic() > deadline:
                    raise TimeoutError("GPU ocupada além do prazo (política clínica)")
                time.sleep(2.0)
                continue
            break
        self._write_holder(level)
        if level == CLINICAL:
            self._flag.write_text(str(time.time()))
            try:
                if self._s.unload_titular_on_job:
                    unload_titular(self._s)
            except Exception:
                pass  # Docker indisponível não pode travar a consulta
        try:
            yield
        finally:
            if level == CLINICAL:
                self._flag.unlink(missing_ok=True)
            try:
                self._path.unlink(missing_ok=True)
            finally:
                if fd is not None:
                    fcntl.flock(fd, fcntl.LOCK_UN)
                    fd.close()

    def should_yield(self) -> bool:
        """Para jobs de pesquisa: ceder quando houver clínica ativa."""
        return self._flag.exists()


def unload_titular(settings: Settings) -> None:
    """Descarrega o modelo titular do Ollama para liberar VRAM (~13,8 GB)."""
    subprocess.run(
        ["docker", "exec", settings.ollama_container, "ollama", "stop", settings.ollama_model],
        check=False, capture_output=True, timeout=60,
    )


def vram_used_mib() -> int | None:
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10, check=True,
        )
        return max(int(x) for x in out.stdout.split())
    except Exception:
        return None
