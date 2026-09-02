#!/usr/bin/env python3
"""Benchmark local Ollama models for clinical pt-BR workloads.

Runs every case in a cases.jsonl file against each requested model through
the native Ollama chat API (http://127.0.0.1:11434), records wall-clock
timings, Ollama's own eval metrics and peak VRAM, and writes:

  results/<timestamp>/results.json        raw metrics
  results/<timestamp>/report.md           summary table
  results/<timestamp>/outputs/<model>/<case>.md   full generations

Usage:
  python3 benchmark_llm.py --cases cases.jsonl --models gpt-oss:20b gemma4:26b
  python3 benchmark_llm.py --list-cases cases.jsonl

Stdlib only; run inside the VM (needs the Ollama port and nvidia-smi).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

OLLAMA_URL = "http://127.0.0.1:11434"
REQUEST_TIMEOUT_S = 900
NUM_PREDICT = 2048
TEMPERATURE = 0.4


def post(path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        OLLAMA_URL + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_S) as resp:
        return json.loads(resp.read().decode("utf-8"))


class VramSampler(threading.Thread):
    """Samples nvidia-smi memory.used until stopped; keeps the peak."""

    def __init__(self, interval_s: float = 2.0) -> None:
        super().__init__(daemon=True)
        self.interval_s = interval_s
        self.peak_mib = 0
        self._stop = threading.Event()

    def run(self) -> None:
        while not self._stop.is_set():
            try:
                out = subprocess.run(
                    ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, timeout=10,
                )
                self.peak_mib = max(self.peak_mib, max(int(x) for x in out.stdout.split()))
            except Exception:
                pass
            self._stop.wait(self.interval_s)

    def stop(self) -> int:
        self._stop.set()
        self.join(timeout=15)
        return self.peak_mib


def run_case(model: str, case: dict) -> dict:
    messages = [{"role": "user", "content": case["prompt"]}]
    if case.get("system"):
        messages.insert(0, {"role": "system", "content": case["system"]})
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "num_predict": case.get("num_predict", NUM_PREDICT),
            "temperature": case.get("temperature", TEMPERATURE),
        },
    }
    t0 = time.monotonic()
    try:
        resp = post("/api/chat", payload)
    except urllib.error.URLError as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}
    wall_s = time.monotonic() - t0

    msg = resp.get("message", {})
    eval_count = int(resp.get("eval_count") or 0)
    eval_duration_s = (int(resp.get("eval_duration") or 0)) / 1e9
    load_s = (int(resp.get("load_duration") or 0)) / 1e6
    return {
        "wall_s": round(wall_s, 2),
        "load_ms": round(load_s, 1),
        "prompt_eval_count": int(resp.get("prompt_eval_count") or 0),
        "eval_count": eval_count,
        "tokens_per_s": round(eval_count / eval_duration_s, 1) if eval_duration_s > 0 else None,
        "thinking_chars": len(msg.get("thinking") or ""),
        "thinking": msg.get("thinking") or "",
        "content": msg.get("content") or "",
        "done_reason": resp.get("done_reason"),
    }


def render_outputs(model: str, cases: list[dict], runs: dict[str, dict], outdir: Path) -> None:
    model_dir = outdir / "outputs" / model.replace(":", "_").replace("/", "_")
    model_dir.mkdir(parents=True, exist_ok=True)
    for case in cases:
        run = runs.get(case["id"], {})
        if "error" in run:
            (model_dir / f"{case['id']}.md").write_text(f"ERROR: {run['error']}\n")
            continue
        text = (
            f"# {case['id']} — {case.get('title', '')}\n\n"
            f"## Prompt\n\n```\n{case['prompt'][:1500]}\n```\n\n"
            f"## Métricas\n\n"
            f"- wall: {run['wall_s']}s | {run['tokens_per_s']} tok/s | "
            f"{run['eval_count']} tokens gerados | thinking: {run['thinking_chars']} chars | "
            f"done: {run['done_reason']}\n\n"
        )
        if run["thinking_chars"]:
            text += f"## Raciocínio (thinking)\n\n```text\n{run['thinking']}\n```\n\n"
        text += f"## Resposta\n\n{run['content']}\n"
        (model_dir / f"{case['id']}.md").write_text(text, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", required=True, type=Path)
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--outdir", type=Path, default=None)
    ap.add_argument("--list-cases", action="store_true")
    args = ap.parse_args()

    cases = [json.loads(line) for line in args.cases.read_text().splitlines() if line.strip()]
    if args.list_cases:
        for c in cases:
            print(f"{c['id']}: {c.get('title', '')}")
        return 0

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    outdir = args.outdir or (Path(__file__).resolve().parent / "benchmark-results" / stamp)
    outdir.mkdir(parents=True, exist_ok=True)

    sampler = VramSampler()
    sampler.start()
    all_runs: dict[str, dict[str, dict]] = {}
    try:
        for model in args.models:
            print(f"\n=== {model} ===", flush=True)
            runs: dict[str, dict] = {}
            for case in cases:
                print(f"  -> {case['id']} ...", flush=True)
                run = run_case(model, case)
                if "error" in run:
                    print(f"     ERRO: {run['error']}", flush=True)
                else:
                    print(
                        f"     ok: {run['wall_s']}s, {run['tokens_per_s']} tok/s, "
                        f"{run['eval_count']} tok",
                        flush=True,
                    )
                runs[case["id"]] = run
            all_runs[model] = runs
            render_outputs(model, cases, runs, outdir)
    finally:
        peak = sampler.stop()

    (outdir / "results.json").write_text(
        json.dumps({"timestamp": stamp, "peak_vram_mib": peak, "runs": all_runs}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = [
        "# Benchmark LLM — " + stamp,
        "",
        f"VRAM de pico global: **{peak} MiB** (soma de todos os processos GPU, inclui modelos residuais)",
        "",
        "| Modelo | Caso | wall(s) | tok/s | tokens | done |",
        "|---|---|---|---|---|---|",
    ]
    for model, runs in all_runs.items():
        for cid, run in runs.items():
            if "error" in run:
                lines.append(f"| {model} | {cid} | ERRO | - | - | {run['error'][:40]} |")
            else:
                lines.append(
                    f"| {model} | {cid} | {run['wall_s']} | {run['tokens_per_s']} | "
                    f"{run['eval_count']} | {run['done_reason']} |"
                )
    per_model = []
    for model, runs in all_runs.items():
        oks = [r for r in runs.values() if "error" not in r]
        if not oks:
            continue
        avg_wall = sum(r["wall_s"] for r in oks) / len(oks)
        speeds = [r["tokens_per_s"] for r in oks if r["tokens_per_s"]]
        avg_speed = sum(speeds) / len(speeds) if speeds else 0
        per_model.append(f"- **{model}**: média {avg_wall:.1f}s/caso, {avg_speed:.1f} tok/s ({len(oks)}/{len(runs)} ok)")
    lines += ["", "## Médias por modelo", ""] + per_model
    lines += [
        "",
        "## Como pontuar qualidade",
        "",
        "Compare às cegas os arquivos em `outputs/<model>/<case>.md` (critérios por caso no",
        "`cases.jsonl`, campo `rubric`). Nota 0-5 por caso; some por modelo.",
        "",
    ]
    (outdir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nConcluído. Resultados em {outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
