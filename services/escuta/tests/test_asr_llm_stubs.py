from escuta.asr import StubAsr, normalize_segments
from escuta.config import Settings
from escuta.llm import StubLlm, parse_json_reply


def test_normalize_interpolates_missing_words():
    segs = normalize_segments([{"start": 1.0, "end": 2.0, "text": "bom dia"}])
    words = segs[0]["words"]
    assert [w["w"] for w in words] == ["bom", "dia"]
    assert words[0]["s"] == 1.0 and words[-1]["e"] == 2.0


def test_normalize_keeps_provided_words():
    segs = normalize_segments([{"start": 0, "end": 1, "text": "ok",
                                "words": [{"word": "ok", "start": 0.1, "end": 0.5, "probability": 0.9}]}])
    assert segs[0]["words"][0] == {"w": "ok", "s": 0.1, "e": 0.5, "p": 0.9}


def test_parse_json_reply_with_fences_and_prose():
    reply = 'Segue o JSON pedido:\n```json\n{"S": "x", "O": "y"}\n```\nobrigado'
    assert parse_json_reply(reply) == {"S": "x", "O": "y"}
    assert parse_json_reply('{"a": 1}') == {"a": 1}


def test_stub_asr_two_speakers(tmp_path):
    import wave

    p = tmp_path / "a.wav"
    with wave.open(str(p), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\x00\x00" * 16000)
    out = StubAsr(Settings(data_dir=tmp_path)).transcribe(p)
    speakers = {s.get("stub_speaker") for s in out["segments"]}
    assert speakers == {"SPEAKER_00", "SPEAKER_01"}
    assert all(s["words"] for s in out["segments"])


def test_stub_llm_chain_shapes(tmp_path):
    llm = StubLlm(Settings(data_dir=tmp_path))
    soap = llm.soap("dialogo")
    assert set(soap) >= {"S", "O", "A", "P"}
    assert "CID" in llm.laudo(soap)
    verify = llm.verify("dialogo", soap)
    assert set(verify) == {"sem_cobertura", "sem_evidencia"}
    roles = llm.verify_roles("dialogo", ["SPEAKER_00", "SPEAKER_01"])
    assert roles == {"SPEAKER_00": "MEDICO", "SPEAKER_01": "PACIENTE"}
    assert llm.calls == ["soap", "laudo", "verify", "roles"]


def test_http_llm_native_ollama_mode(tmp_path, monkeypatch):
    """Modo nativo /api/chat: think=false e conteúdo vazio é erro explícito."""
    from escuta.config import Settings
    from escuta.llm import HttpLlm, LlmError

    settings = Settings(data_dir=tmp_path)
    settings.llm_url = "http://ollama:11434/api/chat"
    llm = HttpLlm(settings)

    class FakeResp:
        status_code = 200
        def __init__(self, payload):
            self._p = payload
        def json(self):
            return self._p

    calls = []

    class FakeClient:
        def post(self, url, json=None, headers=None):
            calls.append(json)
            return FakeResp({"message": {"content": '{"ok": true}'}})

    llm._client = FakeClient()
    assert llm.chat("m", "sys", "usr") == '{"ok": true}'
    assert calls[0]["think"] is False and calls[0]["stream"] is False

    llm._client = type("C", (), {"post": staticmethod(lambda *a, **k: FakeResp({"message": {"content": ""}}))})()
    try:
        llm.chat("m", "s", "u")
        raised = False
    except LlmError:
        raised = True
    assert raised


def test_http_llm_soap_salvage_truncated_json(tmp_path):
    """SOAP truncada no meio: regex recupera as seções fechadas."""
    from escuta.config import Settings
    from escuta.llm import HttpLlm

    llm = HttpLlm(Settings(data_dir=tmp_path))
    llm.chat = lambda *a, **k: (
        '{"S":"Paciente relata ardência [00:05]","O":"córnea pontilhada [00:31]",'
        '"A":"olho seco","P":"colírio 4x/dia [00:37]. Retorno em 30 dias. [00:41'
    )  # truncado: sem fechação
    soap = llm.soap("dialogo")
    assert soap["S"].startswith("Paciente relata")
    assert soap["O"].startswith("córnea")
    assert soap["P"].startswith("colírio")
