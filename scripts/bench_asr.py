#!/usr/bin/env python3
"""Benchmark ASR local (Speaches / WhisperLiveKit) para o trilho clínico.

Mede wall-clock, RTF (tempo de processamento / duração do áudio) e VRAM de
pico ao transcrever áudios sintéticos de consulta médica pt-BR contra um
endpoint OpenAI-compatible (/v1/audio/transcriptions). Sem corpus real
disponível (sala indisponível), o corpus é gerado por TTS a partir do
roteiro conhecido em configs/ai-stack/benchmark/asr-dialogo-ptbr.txt —
o WER contra esse texto é apenas sanity (voz robótica), NÃO clínico.

Escreve (mesmo layout do benchmark_llm.py):

  <outdir>/results.json        métricas cruas
  <outdir>/report.md           tabela resumo
  <outdir>/corpus/             wavs sintéticos + referência

Uso (dentro da VM; túnel -L 8000 se rodar fora):

  python3 bench_asr.py \
    --models Systran/faster-whisper-large-v3-turbo \
             mobiuslabsgmbh/faster-whisper-large-v3 \
    --minutes 1 5 15
  python3 bench_asr.py --synth-only --minutes 60          # só gerar corpus
  python3 bench_asr.py --selftest                          # validação sem GPU
  python3 bench_asr.py --audio c.wav --reference ref.txt \
    --models Systran/faster-whisper-large-v3-turbo        # corpus real futuro

TTS: preferência espeak-ng (duas vozes: pt+f3 paciente / pt+m3 médico;
`sudo apt install espeak-ng`), fallback piper (uma voz; baixa modelo do HF).
Stdlib only (jiwer opcional para WER).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.request
import uuid
import wave
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_ENDPOINT = "http://127.0.0.1:8000/v1/audio/transcriptions"
DEFAULT_DIALOGUE = Path(__file__).resolve().parent.parent / "configs/ai-stack/benchmark/asr-dialogo-ptbr.txt"
SAMPLE_RATE_FALLBACK = 22050  # espeak-ng/piper nativo
TURN_PAUSE_S = (0.45, 0.75)  # pausa entre falas (jitter; simula turno real)
REQUEST_TIMEOUT_S = 3600

ESPEAK_VOICES = {"P": "pt+f3", "M": "pt+m3"}
ESPEAK_SPEED = {"P": "150", "M": "135"}


# --------------------------------------------------------------------------- #
# Áudio: leitura/concatenação WAV (16-bit PCM mono) sem dependências.
# --------------------------------------------------------------------------- #

def wav_read(path: Path) -> tuple[bytes, int]:
    with wave.open(str(path), "rb") as w:
        assert w.getnchannels() == 1 and w.getsampwidth() == 2, f"{path}: não é s16le mono"
        return w.readframes(w.getnframes()), w.getframerate()


def wav_write(path: Path, frames: bytes, rate: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(frames)


def audio_duration_s(path: Path) -> float:
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / float(w.getframerate() or SAMPLE_RATE_FALLBACK)


def silence(seconds: float, rate: int) -> bytes:
    return b"\x00\x00" * int(seconds * rate)


# --------------------------------------------------------------------------- #
# Corpus sintético: roteiro -> falas TTS -> wav único por duração alvo.
# --------------------------------------------------------------------------- #

def parse_dialogue(path: Path) -> list[tuple[str, str]]:
    lines = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if len(line) > 2 and line[1] == ":" and line[0] in "MP":
            lines.append((line[0], line[3:].strip()))
    if not lines:
        raise SystemExit(f"Roteiro sem falas M:/P: em {path}")
    return lines


def tts_espeak(text: str, voice: str, speed: str, out: Path) -> None:
    subprocess.run(
        ["espeak-ng", "-v", voice, "-s", speed, "-w", str(out), text],
        check=True, capture_output=True,
    )


PIPER_VOICE = "pt_BR-faber-medium"
PIPER_DATA_DIR = Path.home() / ".cache" / "piper-voices"


def tts_piper(text: str, out: Path) -> None:
    PIPER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    sys = __import__("sys")
    cmd = ["piper"] if shutil.which("piper") else [sys.executable, "-m", "piper"]
    if not (PIPER_DATA_DIR / f"{PIPER_VOICE}.onnx").exists():
        dl = ["piper", "download_voices", PIPER_VOICE] if shutil.which("piper") else \
            [sys.executable, "-m", "piper.download_voices", PIPER_VOICE]
        subprocess.run(dl, cwd=PIPER_DATA_DIR, check=True, capture_output=True)
    subprocess.run(
        cmd + ["--model", PIPER_VOICE, "--data-dir", str(PIPER_DATA_DIR),
               "--output_file", str(out)],
        input=text.encode("utf-8"), check=True, capture_output=True,
    )


def pick_engine(requested: str) -> str:
    if requested != "auto":
        return requested
    if shutil.which("espeak-ng"):
        return "espeak-ng"
    if shutil.which("piper"):
        return "piper"
    raise SystemExit("Nenhum TTS disponível. Instale espeak-ng (sudo apt install espeak-ng) ou use --tts none com --audio.")


def synth_consulta(dialogue: list[tuple[str, str]], target_s: float, engine: str,
                   workdir: Path, rng_seed: int = 7) -> tuple[Path, str]:
    """Sintetiza o roteiro repetidamente até >= target_s; devolve (wav, texto).

    Vozes distintas M/P (espeak-ng) para que o áudio sirva também a testes de
    diarização; com piper usa-se uma voz única (nota vai no relatório).
    """
    import random

    rng = random.Random(rng_seed)
    cache = workdir / "tts-cache"
    cache.mkdir(parents=True, exist_ok=True)
    chunks: list[bytes] = []
    rate = None
    ref_parts: list[str] = []
    i = 0
    total = 0.0
    while total < target_s:
        speaker, text = dialogue[i % len(dialogue)]
        h = hashlib.sha1(f"{engine}|{speaker}|{text}".encode()).hexdigest()[:16]
        piece = cache / f"{h}.wav"
        if not piece.exists():
            if engine == "espeak-ng":
                tts_espeak(text, ESPEAK_VOICES[speaker], ESPEAK_SPEED[speaker], piece)
            else:
                tts_piper(text, piece)
        frames, r = wav_read(piece)
        rate = rate or r
        if r != rate:  # motores homogêneos; proteção barata
            raise SystemExit(f"Taxa inconsistente no TTS: {r} != {rate}")
        pause = rng.uniform(*TURN_PAUSE_S)
        chunks.append(frames + silence(pause, rate))
        ref_parts.append(f"{'M' if speaker == 'M' else 'P'}: {text}")
        total += len(frames) / (2 * rate) + pause
        i += 1

    out = workdir / f"consulta-sintetica-{int(total / 60)}min.wav"
    wav_write(out, b"".join(chunks), rate)
    (workdir / "referencia.txt").write_text("\n".join(ref_parts) + "\n", encoding="utf-8")
    return out, "\n".join(ref_parts)


def synth_sine_speech(n_seconds: float, rate: int, out: Path, seed: int = 3) -> None:
    """'Fala' de bursts tonais (selftest): exercita a montagem sem TTS."""
    import math
    import random
    import struct

    rng = random.Random(seed)
    frames = bytearray()
    t = 0.0
    while t < n_seconds:
        burst = rng.uniform(0.15, 0.5)
        freq = rng.uniform(180, 900)
        gap = rng.uniform(0.05, 0.25)
        n = int(burst * rate)
        for k in range(n):
            env = 0.6 * (1 - k / n)
            v = int(env * 18000 * math.sin(2 * math.pi * freq * (k / rate)))
            frames += struct.pack("<h", v)
        frames += silence(gap, rate)
        t += burst + gap
    wav_write(out, bytes(frames), rate)


# --------------------------------------------------------------------------- #
# Cliente do endpoint (multipart POST manual; sem dependências).
# --------------------------------------------------------------------------- #

def multipart_body(fields: dict[str, str], filename: str, payload: bytes,
                   content_type: str = "audio/wav") -> tuple[bytes, str]:
    boundary = "----lapanasrbench" + uuid.uuid4().hex
    parts = []
    for key, value in fields.items():
        parts.append(
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\"\r\n\r\n{value}\r\n".encode()
        )
    parts.append(
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\n"
        f"Content-Type: {content_type}\r\n\r\n".encode() + payload + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), boundary


def transcribe(endpoint: str, api_key: str | None, model: str, audio: Path,
               language: str = "pt", timeout_s: int = REQUEST_TIMEOUT_S) -> dict:
    body, boundary = multipart_body(
        {"model": model, "language": language, "response_format": "json"},
        audio.name, audio.read_bytes(),
    )
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(endpoint, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        return json.loads(resp.read().decode("utf-8"))


class VramSampler(threading.Thread):
    """Amostra nvidia-smi memory.used até parar; guarda o pico (por rodada)."""

    def __init__(self, interval_s: float = 1.0) -> None:
        super().__init__(daemon=True)
        self.interval_s = interval_s
        self.peak_mib = 0
        self._halt = threading.Event()

    def run(self) -> None:
        while not self._halt.is_set():
            try:
                out = subprocess.run(
                    ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, timeout=10,
                )
                self.peak_mib = max(self.peak_mib, max(int(x) for x in out.stdout.split()))
            except Exception:
                pass
            self._halt.wait(self.interval_s)

    def stop(self) -> int:
        self._halt.set()
        self.join(timeout=15)
        return self.peak_mib


def compute_wer(reference: str, hypothesis: str) -> float | None:
    try:
        import jiwer
    except ImportError:
        return None
    clean_ref = " ".join(reference.split())
    clean_hyp = " ".join(hypothesis.split())
    if not clean_ref:
        return None
    return jiwer.wer(clean_ref, clean_hyp)


# --------------------------------------------------------------------------- #
# Selftest: corpus senoidal + servidor mock OpenAI-compatible.
# --------------------------------------------------------------------------- #

class MockSttServer(threading.Thread):
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    def __init__(self) -> None:
        super().__init__(daemon=True)

        class Handler(self.BaseHTTPRequestHandler):
            seen: list[int] = []

            def do_POST(self) -> None:  # noqa: N802
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length)
                Handler.seen.append(len(body))
                payload = json.dumps({"text": "teste sintetico do selftest"}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *_args) -> None:
                pass

        self.httpd = self.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.httpd.server_address[1]
        self.seen = Handler.seen

    def run(self) -> None:
        self.httpd.serve_forever()

    def stop(self) -> None:
        self.httpd.shutdown()


def selftest(outdir: Path) -> int:
    wav = outdir / "corpus" / "selftest-10s.wav"
    synth_sine_speech(10.0, 16000, wav)
    duration = audio_duration_s(wav)
    assert 9.0 <= duration <= 12.0, f"duração inesperada: {duration}"
    print(f"  corpus senoidal ok: {duration:.1f}s")

    server = MockSttServer()
    server.start()
    time.sleep(0.2)
    try:
        result = transcribe(
            f"http://127.0.0.1:{server.port}/v1/audio/transcriptions",
            api_key="k", model="mock-model", audio=wav,
        )
        assert result["text"] == "teste sintetico do selftest", result
        assert server.seen and server.seen[-1] > 320_000, "payload parecia curto demais"
        print(f"  POST multipart ok ({server.seen[-1]} bytes)")
    finally:
        server.stop()
    print("selftest ok")
    return 0


# --------------------------------------------------------------------------- #
# Runner.
# --------------------------------------------------------------------------- #

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--models", nargs="+", default=["Systran/faster-whisper-large-v3-turbo"])
    ap.add_argument("--minutes", nargs="+", type=float, default=[1, 5])
    ap.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    ap.add_argument("--api-key-env", default="SPEACHES_API_KEY",
                    help="nome da variável de ambiente com a chave (vazia = sem auth)")
    ap.add_argument("--language", default="pt")
    ap.add_argument("--tts", choices=["auto", "espeak-ng", "piper", "none"], default="auto")
    ap.add_argument("--dialogue", type=Path, default=DEFAULT_DIALOGUE)
    ap.add_argument("--audio", type=Path, help="wav pronto (pula síntese; exige --reference p/ WER)")
    ap.add_argument("--reference", type=Path, help="transcrição de referência (WER)")
    ap.add_argument("--no-wer", action="store_true", help="pular cálculo de WER mesmo com referência")
    ap.add_argument("--no-warmup", action="store_true", help="não fazer chamada de aquecimento por modelo")
    ap.add_argument("--synth-only", action="store_true", help="só gerar o corpus sintético")
    ap.add_argument("--selftest", action="store_true", help="validação offline (sem GPU/endpoint real)")
    ap.add_argument("--outdir", type=Path, default=None)
    args = ap.parse_args()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    outdir = args.outdir or (Path(__file__).resolve().parent / "benchmark-results" / f"asr-{stamp}")
    corpus_dir = outdir / "corpus"
    corpus_dir.mkdir(parents=True, exist_ok=True)

    if args.selftest:
        return selftest(outdir)

    # 1) Corpus.
    reference_text: str | None = None
    if args.audio:
        audio_files = [(args.audio, args.minutes[0] if args.minutes else 1.0)]
        if args.reference:
            reference_text = args.reference.read_text(encoding="utf-8")
        engine = "externo"
    else:
        engine = pick_engine(args.tts)
        dialogue = parse_dialogue(args.dialogue)
        audio_files = []
        for minutes in args.minutes:
            target_s = minutes * 60.0
            sub = corpus_dir / f"{int(minutes)}min"
            sub.mkdir(parents=True, exist_ok=True)
            wav, ref = synth_consulta(dialogue, target_s, engine, sub)
            audio_files.append((wav, minutes))
            reference_text = ref if reference_text is None else reference_text
        if args.synth_only:
            for wav, minutes in audio_files:
                print(f"  {wav} ({audio_duration_s(wav) / 60:.1f} min)")
            print(f"Corpus pronto em {corpus_dir}")
            return 0

    # 2) Endpoint.
    api_key = __import__("os").environ.get(args.api_key_env, "")
    runs: dict[str, dict[float, dict]] = {}

    for model in args.models:
        print(f"\n=== {model} ===", flush=True)
        runs[model] = {}
        if not args.no_warmup:
            warm = corpus_dir / "warmup.wav"
            if not warm.exists():
                synth_sine_speech(2.0, 16000, warm)
            print("  aquecendo (carga de modelo)...", flush=True)
            try:
                transcribe(args.endpoint, api_key or None, model, warm, args.language)
            except Exception as exc:  # endpoint fora do ar: aborta este modelo
                print(f"  ERRO no aquecimento: {exc}", flush=True)
                runs[model] = {m: {"error": str(exc)} for m in (a[1] for a in audio_files)}
                continue
        for wav, minutes in audio_files:
            duration = audio_duration_s(wav)
            sampler = VramSampler()
            sampler.start()
            t0 = time.monotonic()
            try:
                resp = transcribe(args.endpoint, api_key or None, model, wav, args.language)
                wall_s = time.monotonic() - t0
                peak = sampler.stop()
                text = resp.get("text", "")
                run = {
                    "audio": str(wav),
                    "audio_min": round(duration / 60, 2),
                    "audio_mib": round(wav.stat().st_size / 2**20, 1),
                    "wall_s": round(wall_s, 2),
                    "rtf": round(wall_s / duration, 4),
                    "chars": len(text),
                    "text": text,  # hipótese completa p/ WER offline (jiwer)
                    "peak_vram_mib": peak,
                }
                if reference_text and not args.no_wer:
                    wer = compute_wer(reference_text, text)
                    if wer is not None:
                        run["wer_sanity"] = round(wer, 4)
            except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
                sampler.stop()
                run = {"audio": str(wav), "error": f"{type(exc).__name__}: {exc}"}
            runs[model][minutes] = run
            ok = "error" not in run
            line = f"  {minutes:g}min -> "
            if ok:
                line += f"RTF {run['rtf']:.3f} ({run['wall_s']}s), pico {run['peak_vram_mib']} MiB"
                if "wer_sanity" in run:
                    line += f", WER(sanity) {run['wer_sanity']:.1%}"
            else:
                line += f"ERRO: {run['error'][:80]}"
            print(line, flush=True)

    # 3) Relatórios.
    (outdir / "results.json").write_text(
        json.dumps(
            {
                "timestamp": stamp,
                "endpoint": args.endpoint,
                "tts_engine": engine,
                "language": args.language,
                "runs": {m: {str(k): v for k, v in per.items()} for m, per in runs.items()},
            },
            ensure_ascii=False, indent=2,
        ),
        encoding="utf-8",
    )

    lines = [
        "# Benchmark ASR — " + stamp,
        "",
        f"- Endpoint: `{args.endpoint}` | idioma: {args.language} | TTS: {engine}",
        "- Corpus sintético a partir de roteiro conhecido: WER é sanity (voz TTS),",
        "  não medida clínica. Substitua por `--audio/--reference` com gravação real",
        "  quando a sala voltar a estar disponível.",
        "",
        "| Modelo | Áudio (min) | wall (s) | RTF | pico VRAM (MiB) | WER sanity |",
        "|---|---|---|---|---|---|",
    ]
    for model, per in runs.items():
        for minutes, run in sorted(per.items()):
            if "error" in run:
                lines.append(f"| {model} | {minutes:g} | ERRO | - | - | {run['error'][:40]} |")
            else:
                lines.append(
                    f"| {model} | {run['audio_min']} | {run['wall_s']} | {run['rtf']:.3f} | "
                    f"{run['peak_vram_mib']} | {run.get('wer_sanity', '—')} |"
                )
    lines += [
        "",
        "## Leitura",
        "",
        "- **RTF** é o gate primário (decisão 2026-09-24: rapidez primeiro):",
        "  RTF <= 0,15 = 1 h de consulta em até 9 min.",
        "- pico VRAM informa a coexistência com o modelo titular (gpt-oss:20b ~13,8 GB).",
        "",
    ]
    (outdir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nConcluído. Resultados em {outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
