/* Escuta clínica — fluxo de dois cliques + revisão em tela dividida. */
"use strict";

const TOKEN = new URLSearchParams(location.search).get("token") || localStorage.getItem("escuta_token") || "";
if (TOKEN) localStorage.setItem("escuta_token", TOKEN);

const $ = (id) => document.getElementById(id);
const show = (id) => ["home", "live", "proc", "review", "error"]
  .forEach((s) => $(s).classList.toggle("hidden", s !== id));

let cid = null, ws = null, ctx = null, stream = null, node = null;
let timerId = null, t0 = 0;

async function api(path, opts = {}) {
  const resp = await fetch(path, {
    ...opts,
    headers: { "Content-Type": "application/json", "X-Escuta-Token": TOKEN, ...(opts.headers || {}) },
  });
  if (!resp.ok) throw new Error(`${path}: ${resp.status} ${await resp.text()}`);
  return resp.json();
}

/* ---- clique 1: iniciar ---- */
$("btn-start").onclick = async () => {
  try {
    const out = await api("/api/sessions", { method: "POST", body: JSON.stringify({ doctor_label: $("doctor").value || null }) });
    cid = out.id;
    show("live"); t0 = Date.now();
    timerId = setInterval(() => {
      const s = Math.floor((Date.now() - t0) / 1000);
      $("timer").textContent = `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
    }, 500);
    await startMic(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}${out.ws}${TOKEN ? `?token=${TOKEN}` : ""}`);
  } catch (e) { fail(e); }
};

/* ---- captura: PCM 16 kHz Int16 via AudioWorklet; servidor grava ---- */
async function startMic(url) {
  stream = await navigator.mediaDevices.getUserMedia({
    audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true },
  });
  ctx = new AudioContext({ sampleRate: 16000 });
  const blob = new Blob([`
    class Rec extends AudioWorkletProcessor {
      process(inputs) {
        const ch = inputs[0][0];
        if (ch) {
          const pcm = new Int16Array(ch.length);
          for (let i = 0; i < ch.length; i++) {
            const s = Math.max(-1, Math.min(1, ch[i]));
            pcm[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
          }
          this.port.postMessage(pcm.buffer, [pcm.buffer]);
        }
        return true;
      }
    }
    registerProcessor("rec", Rec);`], { type: "application/javascript" });
  await ctx.audioWorklet.addModule(URL.createObjectURL(blob));
  node = new AudioWorkletNode(ctx, "rec");
  node.port.onmessage = (ev) => { if (ws && ws.readyState === 1) ws.send(ev.data); };

  ws = new WebSocket(url);
  ws.binaryType = "arraybuffer";
  ws.onopen = () => { $("conn").classList.add("on"); ctx.resume(); node.connect(ctx.destination); };
  ws.onmessage = (ev) => { if (typeof ev.data === "string") renderLive(ev.data); };
  ws.onclose = () => { $("conn").classList.remove("on"); };
}

function renderLive(raw) {
  let msg; try { msg = JSON.parse(raw); } catch { return; }
  if (msg.type === "finalizada") { stopMic(); followJob(); return; }
  const box = $("livetext");
  box.scrollTop = box.scrollHeight;
  const segs = msg.segments || [];
  for (const s of segs) {
    const text = (s.text || "").trim();
    if (!text) continue;
    const who = s.speaker || s.diarization || "?";
    let p = box.querySelector(`[data-sp="${CSS.escape(who)}"]`);
    if (!p) {
      p = document.createElement("p");
      p.dataset.sp = who;
      p.innerHTML = `<span class="sp"></span><span class="tx"></span>`;
      box.appendChild(p);
    }
    p.querySelector(".sp").textContent = who.startsWith("MEDICO") ? "Médico:" : who.startsWith("PACIENTE") ? "Paciente:" : who + ":";
    p.querySelector(".tx").textContent = text;
  }
}

function stopMic() {
  clearInterval(timerId);
  if (node) node.disconnect();
  if (ctx) ctx.close();
  if (stream) stream.getTracks().forEach((t) => t.stop());
  $("conn").classList.remove("on");
}

/* ---- clique 2: finalizar ---- */
$("btn-stop").onclick = () => { if (ws && ws.readyState === 1) ws.send("stop"); $("btn-stop").disabled = true; };

/* ---- processamento em background (SSE) ---- */
const STAGES = { fila: "na fila", asr: "transcrevendo", diarizacao: "separando falantes",
                 papeis: "atribuindo papéis", soap: "gerando prontuário", concluido: "concluído", erro: "erro" };

function followJob() {
  show("proc");
  const es = new EventSource(`/api/jobs/${cid}/events${TOKEN ? `?token=${TOKEN}` : ""}`);
  es.onmessage = (ev) => {
    const job = JSON.parse(ev.data);
    $("prog").style.width = `${Math.round((job.progress || 0) * 100)}%`;
    $("stage").textContent = STAGES[job.stage] || job.stage;
    if (job.stage === "concluido") { es.close(); loadReview(job.detail); }
    if (job.stage === "erro") { es.close(); fail(new Error(job.error)); }
  };
  es.onerror = () => { es.close(); loadReview(); }; // SSE caiu: tenta revisão direto
}

/* ---- revisão: tela dividida ---- */
async function loadReview(warnPapeis) {
  show("review");
  if (warnPapeis === "confirmar papéis") $("papeis-warning").classList.remove("hidden");
  const [tr, soap, cons] = await Promise.all([
    api(`/api/consultations/${cid}/transcript`), api(`/api/consultations/${cid}/soap`),
    api(`/api/consultations/${cid}`),
  ]);

  const fields = $("soap-fields");
  fields.innerHTML = "";
  for (const [k, label] of [["S", "S — Subjetivo"], ["O", "O — Objetivo"], ["A", "A — Avaliação"], ["P", "P — Plano"]]) {
    const lab = document.createElement("label"); lab.textContent = label;
    const ta = document.createElement("textarea"); ta.id = `soap-${k}`;
    ta.value = soap.payload.soap?.[k] || "não informado";
    fields.append(lab, ta);
  }
  $("laudo").textContent = soap.payload.laudo || "";

  const v = soap.payload.verificacao || {};
  const vl = $("verify"); vl.innerHTML = "<h3>Verificação cruzada (IA)</h3>";
  const mk = (title, items) => {
    if (!items?.length) return;
    const h = document.createElement("div"); h.textContent = title;
    const ul = document.createElement("ul");
    items.forEach((i) => { const li = document.createElement("li"); li.textContent = i; ul.appendChild(li); });
    vl.append(h, ul);
  };
  mk("Afirmar da transcrição sem cobertura na SOAP:", v.sem_cobertura);
  mk("Afirmar da SOAP sem evidência na transcrição:", v.sem_evidencia);

  if (soap.signed_by) {
    $("signed-note").textContent = `Assinada por ${soap.signed_by} em ${soap.signed_at}`;
    $("signed-note").classList.remove("hidden");
    $("btn-sign").disabled = true;
  }

  const trBox = $("transcript"); trBox.innerHTML = "";
  const roleMap = {};
  Object.entries(tr.roles || {}).forEach(([sp, r]) => (roleMap[sp] = r.role));
  for (const seg of tr.payload.segments || []) {
    const p = document.createElement("p");
    const ts = document.createElement("span"); ts.className = "ts";
    ts.textContent = `[${fmt(seg.start)}]`;
    ts.onclick = () => { const a = $("player"); a.currentTime = Math.max(0, seg.start - 1.5); a.play(); };
    const who = document.createElement("span"); who.className = "who";
    who.textContent = roleMap[seg.speaker] === "MEDICO" ? "Médico" : roleMap[seg.speaker] === "PACIENTE" ? "Paciente" : (seg.speaker || "?");
    p.append(ts, who, document.createTextNode(seg.text || ""));
    trBox.appendChild(p);
  }
  $("player").src = `/audio/${cid}`;
}

const fmt = (s) => `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(Math.round(s % 60)).padStart(2, "0")}`;

$("btn-save").onclick = async () => {
  const body = { S: $("soap-S").value, O: $("soap-O").value, A: $("soap-A").value, P: $("soap-P").value, laudo: $("laudo").textContent, created_by: $("doctor").value || "medico" };
  await api(`/api/consultations/${cid}/soap`, { method: "PUT", body: JSON.stringify(body) });
  $("btn-save").textContent = "Salvo ✓";
};
$("btn-sign").onclick = async () => {
  const signed_by = $("doctor").value?.trim() || prompt("Assinar como:");
  if (!signed_by) return;
  await api(`/api/consultations/${cid}/sign`, { method: "POST", body: JSON.stringify({ signed_by }) });
  $("signed-note").textContent = `Assinada por ${signed_by}. O áudio será expurgado em 90 dias.`;
  $("signed-note").classList.remove("hidden");
  $("btn-sign").disabled = true;
};
$("btn-swap").onclick = async () => {
  await api(`/api/consultations/${cid}/roles/swap`, { method: "POST", body: "{}" });
  followJob();
};
$("btn-enroll").onclick = async () => {
  const out = await api(`/api/consultations/${cid}/enrollment`, { method: "POST", body: "{}" });
  alert(out.msg);
};

function fail(e) { $("errmsg").textContent = e.message || String(e); show("error"); }
