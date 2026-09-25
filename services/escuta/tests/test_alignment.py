from escuta.alignment import (
    assign_word_speaker,
    build_dialogue,
    format_ts,
    resegment_by_speaker,
)

TURNS = [
    {"start": 0.0, "end": 2.0, "speaker": "SPEAKER_00"},
    {"start": 2.0, "end": 4.0, "speaker": "SPEAKER_01"},
    {"start": 4.0, "end": 6.0, "speaker": "SPEAKER_00"},
]


def test_assign_by_max_overlap():
    assert assign_word_speaker({"s": 0.2, "e": 0.8}, TURNS) == "SPEAKER_00"
    assert assign_word_speaker({"s": 2.2, "e": 2.8}, TURNS) == "SPEAKER_01"


def test_assign_orphan_within_tolerance():
    # palavra no gap: mais próxima do turno 1 (termina em 2.0) até 0.25 s
    assert assign_word_speaker({"s": 1.95, "e": 2.05}, TURNS) in TURNS[0]["speaker"], TURNS[1]["speaker"]
    assert assign_word_speaker({"s": 30.0, "e": 31.0}, TURNS) is None


def test_resegment_splits_at_speaker_change():
    seg = {
        "start": 0.0, "end": 3.0, "text": "bom dia tudo bem",
        "words": [
            {"w": "bom", "s": 0.1, "e": 0.4},
            {"w": "dia", "s": 0.4, "e": 0.7},
            {"w": "tudo", "s": 2.1, "e": 2.4},
            {"w": "bem", "s": 2.4, "e": 2.7},
        ],
    }
    out = resegment_by_speaker([seg], TURNS)
    assert len(out) == 2
    assert out[0]["speaker"] == "SPEAKER_00" and out[0]["text"] == "bom dia"
    assert out[1]["speaker"] == "SPEAKER_01" and out[1]["text"] == "tudo bem"
    assert out[0]["end"] < out[1]["start"]


def test_resegment_without_turns_keeps_text():
    seg = {"start": 0.0, "end": 1.0, "text": "sem diarizacao",
           "words": [{"w": "sem", "s": 0.0, "e": 0.5}, {"w": "diarizacao", "s": 0.5, "e": 1.0}]}
    out = resegment_by_speaker([seg], [])
    assert len(out) == 1 and out[0]["speaker"] is None and out[0]["text"] == "sem diarizacao"


def test_format_ts_and_dialogue():
    assert format_ts(65.4) == "01:05"
    segs = [
        {"start": 1.0, "end": 2.0, "speaker": "SPEAKER_00", "text": "bom dia"},
        {"start": 3.0, "end": 4.0, "speaker": "SPEAKER_01", "text": "olá"},
    ]
    text = build_dialogue(segs, {"SPEAKER_00": "MEDICO", "SPEAKER_01": "PACIENTE"})
    assert "[00:01] MEDICO: bom dia" in text
    assert "[00:03] PACIENTE: olá" in text
