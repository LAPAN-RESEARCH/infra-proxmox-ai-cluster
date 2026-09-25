from escuta.roles import (
    combine_roles,
    heuristic_roles,
    parse_llm_roles_reply,
    swap_roles,
)

DOCTOR_SEGS = [
    {"speaker": "SPEAKER_00", "text": "Bom dia, o que está sentando? Há quanto tempo começou?"},
    {"speaker": "SPEAKER_00", "text": "Vou prescrever colírio lubrificante, uma gota quatro vezes ao dia."},
    {"speaker": "SPEAKER_00", "text": "Retorno em trinta dias para reavaliar o exame."},
]
PATIENT_SEGS = [
    {"speaker": "SPEAKER_01", "text": "Doutor, meus olhos estão ardendo muito, estou sentindo desconforto."},
    {"speaker": "SPEAKER_01", "text": "É grave, doutor? Obrigado pela atenção."},
]


def test_heuristic_assigns_doctor_correctly():
    roles = heuristic_roles(DOCTOR_SEGS + PATIENT_SEGS)
    assert roles["SPEAKER_00"] == "MEDICO"
    assert roles["SPEAKER_01"] == "PACIENTE"


def test_heuristic_single_speaker_defaults_medico():
    assert heuristic_roles(DOCTOR_SEGS[:1]) == {"SPEAKER_00": "MEDICO"}


def test_combine_consensus_and_divergence():
    a = {"SPEAKER_00": "MEDICO", "SPEAKER_01": "PACIENTE"}
    roles, consensus, divergent = combine_roles(a, dict(a))
    assert consensus and roles["SPEAKER_00"] == "MEDICO" and not divergent
    b = {"SPEAKER_00": "PACIENTE", "SPEAKER_01": "MEDICO"}
    roles, consensus, divergent = combine_roles(a, b)
    assert not consensus and set(divergent) == {"SPEAKER_00", "SPEAKER_01"}


def test_combine_majority_vote():
    a = {"S": "MEDICO", "P": "PACIENTE"}
    b = {"S": "MEDICO", "P": "PACIENTE"}
    c = {"S": "PACIENTE", "P": "MEDICO"}
    roles, consensus, divergent = combine_roles(a, b, c)
    assert roles["S"] == "MEDICO" and not consensus and set(divergent) == {"S", "P"}


def test_swap_and_parse_llm():
    assert swap_roles({"A": "MEDICO", "B": "PACIENTE"}) == {"A": "PACIENTE", "B": "MEDICO"}
    reply = 'Aqui está: ```json\n{"SPEAKER_00": "MEDICO", "SPEAKER_01": "PACIENTE"}\n```'
    parsed = parse_llm_roles_reply(reply, ["SPEAKER_00", "SPEAKER_01"])
    assert parsed == {"SPEAKER_00": "MEDICO", "SPEAKER_01": "PACIENTE"}
