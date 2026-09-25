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
