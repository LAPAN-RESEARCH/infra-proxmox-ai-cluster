"""Scribe-worker: pipeline batch de fidelidade (Fase 2/3 do plano).

Etapas por consulta: decode 16k -> passa-alta -> [lock GPU clínico] ASR
determinístico -> diarização pyannote (opcional) -> alinhamento palavra×locutor
-> papéis (enrollment + heurística + LLM) -> transcript imutável ->
SOAP -> laudo -> verificação cruzada -> versão 1 para revisão humana.

Roda como thread no processo da API (GPU é serial; concorrência 1 é o
comportamento desejado) ou standalone: `python -m escuta.worker`.
"""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from . import alignment, asr as asr_mod, audio, roles as roles_mod
from .config import Settings
from .db import Database
from .gpulock import GpuLock
from .llm import make_llm
from .retention import purge_due


class ScribeWorker:
    def __init__(self, db: Database, settings: Settings) -> None:
        self.db = db
        self.s = settings
        self.gpu = GpuLock(settings)
        self.llm = make_llm(settings)
        self._asr: Any = None  # embedded exige GPU: instanciar sob demanda
        self._diarizer: Any = None
        self._diarizer_failed = False
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    # -- infra .git/lazy ----------------------------------------------------

    @property
    def asr(self) -> Any:
        if self._asr is None:
            self._asr = asr_mod.make_asr(self.s)
        return self._asr

    def _diarizer_or_none(self) -> Any:
        if self._diarizer_failed:
            return None
        if self._diarizer is None:
            try:
                from .speakers import Diarizer

                self._diarizer = Diarizer(self.s)
            except Exception:
                self._diarizer_failed = True
                return None
        return self._diarizer

    # -- pipeline -------------------------------------------------------------

    def process(self, cid: str) -> None:
        cons = self.db.get_consultation(cid)
        if not cons or not cons["audio_path"]:
            self.db.job_error(cid, "consulta sem áudio registrado")
            return
        tmp_dir = self.s.data_dir / "tmp" / cid
        tmp_dir.mkdir(parents=True, exist_ok=True)

        try:
            # 1) Decode + pré-filtragem leve (Pilar 1).
            self.db.job_update(cid, "asr", 0.05, "decodificando áudio")
            src = Path(cons["audio_path"])
            wav = audio.decode_to_wav16k(src, tmp_dir / "process.wav")
            wav = audio.apply_highpass(wav, tmp_dir / "highpass.wav")

            # 2) ASR determinístico sob lock clínico (Pilar 2/4).
            with self.gpu.acquire("clinical-high"):
                self.db.job_update(cid, "asr", 0.10, "transcrevendo")
                result = self.asr.transcribe(wav)

                # 3) Diarização (Pilar 3).
                self.db.job_update(cid, "diarizacao", 0.5, "separando falantes")
                turns = self._turns(wav, result)
            segments = result["segments"]
            del result

            # 4) Alinhamento palavra × locutor.
            self.db.job_update(cid, "diarizacao", 0.55, "alinhando palavras")
            segments = alignment.resegment_by_speaker(segments, turns)

            # 5) Papéis MEDICO/PACIENTE (tripla checagem).
            self.db.job_update(cid, "papeis", 0.6, "atribuindo papéis")
            final_roles, consensus, divergent = self._assign_roles(cid, segments, wav)
            role_map = final_roles
            dialogue = alignment.build_dialogue(segments, role_map)

            # 6) Transcript imutável (contrato do Pilar 5).
            self.db.insert_transcript(
                cid, self.s.asr_model, {"backend": self.s.asr_backend, "language": self.s.asr_language},
                {"segments": segments, "roles": final_roles, "divergencia_papeis": divergent,
                 "diarizacao_ativa": bool(turns), "dialogue": dialogue},
            )

            # 7) Síntese desacoplada: SOAP -> laudo -> verificação.
            self.db.job_update(cid, "soap", 0.7, "gerando nota SOAP")
            soap = self.llm.soap(dialogue)
            self.db.job_update(cid, "soap", 0.8, "redigindo laudo")
            laudo = self.llm.laudo(soap)
            self.db.job_update(cid, "soap", 0.9, "verificação cruzada")
            verify = self.llm.verify(dialogue, soap)

            payload = {"soap": soap, "laudo": laudo, "verificacao": verify,
                       "divergencia_papeis": divergent, "papeis": final_roles}
            self.db.insert_soap(cid, payload)
            detail = "confirmar papéis" if divergent else None
            self.db.job_update(cid, "concluido", 1.0, detail)
        except Exception as exc:  # noqa: BLE001 - erro vira estado do job
            self.db.job_error(cid, f"{type(exc).__name__}: {exc}")
        finally:
            for f in tmp_dir.glob("*.wav"):
                f.unlink(missing_ok=True)

    def _turns(self, wav: Path, result: dict[str, Any]) -> list[dict[str, Any]]:
        diar = self._diarizer_or_none()
        if diar is not None:
            try:
                return diar.turns(wav)
            except Exception:
                self._diarizer_failed = True
        # Fallback: turnos sintéticos do backend (stub) ou nenhum.
        turns = []
        for seg in result["segments"]:
            sp = seg.pop("stub_speaker", None)
            if sp:
                turns.append({"start": seg["start"], "end": seg["end"], "speaker": sp})
        return turns

    def _assign_roles(self, cid: str, segments: list[dict[str, Any]],
                      wav: Path) -> tuple[dict[str, str], bool, list[str]]:
        speakers = sorted({s["speaker"] for s in segments if s["speaker"]})
        if not speakers:
            return {}, True, []

        sources: list[dict[str, str]] = []
        used_enrollment = False

        # (a) enrollment ECAPA do médico, se disponível.
        enrollment = self.db.get_enrollment("medico")
        if enrollment and speakers:
            roles_e = self._match_enrollment(segments, wav, enrollment[0], speakers)
            if roles_e:
                sources.append(roles_e)
                used_enrollment = True

        # (b) heurística de turnos.
        sources.append(roles_mod.heuristic_roles(segments, self.s.diar_max_speakers))

        # (c) verificação semântica por LLM barato.
        dialogue = alignment.build_dialogue(segments)
        try:
            sources.append(self.llm.verify_roles(dialogue, speakers))
        except Exception:
            pass  # LLM fora do ar não bloqueia: 2 fontes bastam, divergência segue marcada

        final, consensus, divergent = roles_mod.combine_roles(*sources)
        source_name = "enrollment" if used_enrollment else "heuristica"
        self.db.set_roles(cid, {sp: (role, source_name, 0.8) for sp, role in final.items()})
        return final, consensus, divergent

    def _match_enrollment(self, segments: list[dict[str, Any]], wav: Path,
                          reference: bytes, speakers: list[str]) -> dict[str, str] | None:
        try:
            from .speakers import EcapaEnroller, match_speaker

            enroller = EcapaEnroller()
        except Exception:
            return None
        # embedding médio dos turnos de cada falante (amostra de até 3 trechos)
        best: dict[str, float] = {}
        counts: dict[str, int] = {sp: 0 for sp in speakers}
        for seg in segments:
            sp = seg.get("speaker")
            if sp and counts.get(sp, 3) < 3:
                try:
                    score = match_speaker(
                        enroller.embed(wav, seg["start"], seg["end"]), reference)
                except Exception:
                    continue
                counts[sp] += 1
                best[sp] = max(best.get(sp, -1.0), score)
        doctor = max(best, key=best.get) if best else None
        if doctor is None:
            return None
        out = {sp: "PACIENTE" for sp in speakers}
        out[doctor] = "MEDICO"
        return out

    # -- regeneração (troca de papéis / refazer SOAP) --------------------------

    def regenerate(self, cid: str, swap: bool = False) -> None:
        cons = self.db.get_consultation(cid)
        if not cons:
            return
        if swap:
            current = self.db.get_roles(cid)
            swapped = roles_mod.swap_roles({sp: r["role"] for sp, r in current.items()})
            self.db.set_roles(cid, {sp: (r, "manual", 1.0) for sp, r in swapped.items()})
        transcript = self.db.latest_transcript(cid)
        if not transcript:
            self.db.job_error(cid, "sem transcript para regenerar")
            return
        import json

        payload = json.loads(transcript["payload_json"])
        roles_now = {sp: r["role"] for sp, r in self.db.get_roles(cid).items()}
        dialogue = alignment.build_dialogue(payload["segments"], roles_now)
        try:
            self.db.job_update(cid, "soap", 0.7, "regenerando SOAP")
            soap = self.llm.soap(dialogue)
            laudo = self.llm.laudo(soap)
            verify = self.llm.verify(dialogue, soap)
            self.db.insert_soap(cid, {"soap": soap, "laudo": laudo, "verificacao": verify,
                                      "papeis": roles_now}, created_by="sistema")
            self.db.job_update(cid, "concluido", 1.0, "regenerado")
        except Exception as exc:  # noqa: BLE001
            self.db.job_error(cid, f"regeneração: {exc}")

    # -- enrollment -------------------------------------------------------------

    def enroll_doctor(self, cid: str) -> bool:
        transcript = self.db.latest_transcript(cid)
        cons = self.db.get_consultation(cid)
        if not (transcript and cons and cons["audio_path"]):
            return False
        try:
            from .speakers import EcapaEnroller

            enroller = EcapaEnroller()
        except Exception:
            return False
        import json

        payload = json.loads(transcript["payload_json"])
        role_map = {sp: r["role"] for sp, r in self.db.get_roles(cid).items()}
        medico = next((sp for sp, r in role_map.items() if r == "MEDICO"), None)
        if medico is None:
            return False
        tmp = self.s.data_dir / "tmp" / f"enroll-{cid}"
        tmp.mkdir(parents=True, exist_ok=True)
        wav = audio.decode_to_wav16k(Path(cons["audio_path"]), tmp / "e.wav")
        clips = [s for s in payload["segments"] if s.get("speaker") == medico][:5]
        for i, seg in enumerate(clips):
            blob = enroller.embed(wav, seg["start"], seg["end"])
            existing = self.db.get_enrollment("medico")
            if existing and i > 0:
                blob = _avg_embedding(blob, existing[0], weight_new=1 / (i + 1))
            self.db.save_enrollment("medico", blob, n_samples=i + 1)
        wav.unlink(missing_ok=True)
        return True

    # -- loop -----------------------------------------------------------------

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, name="scribe-worker", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        import time

        while not self._stop.is_set():
            try:
                for cid in self.db.pending_jobs():
                    self.process(cid)
            except Exception:  # loop nunca morre
                pass
            self._retention_tick()
            time.sleep(2.0)

    def _retention_tick(self) -> None:
        try:
            purge_due(self.db, self.s)
        except Exception:
            pass

    def stop(self) -> None:
        self._stop.set()


def _avg_embedding(new: bytes, old: bytes, weight_new: float) -> bytes:
    from .speakers import _unpack_embedding, _pack_embedding

    a, b = _unpack_embedding(new), _unpack_embedding(old)
    if not b or len(a) != len(b):
        return new
    return _pack_embedding([weight_new * x + (1 - weight_new) * y for x, y in zip(a, b)])
