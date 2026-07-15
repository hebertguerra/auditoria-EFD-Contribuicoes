"""Suite de regressao: roda todos os checks contra o exemplo sintetico
(gerar_exemplo.py) e confere que cada um dispara exatamente nos erros
propositais documentados no docstring daquele arquivo -- nem a mais
(falso positivo) nem a menos (check quebrado/regrediu).

Numeros de ocorrencia foram tirados de uma execucao real do CLI contra o
exemplo gerado (nao adivinhados) -- se o gerador mudar, rode
`python gerar_exemplo.py` e `python -m audita.cli exemplo_sped.txt` para
atualizar os numeros abaixo antes de ajustar o teste.
"""
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from audita.parser import Documento  # noqa: E402
from audita.checks import executar, REGISTRY  # noqa: E402

# check_id -> numero exato de achados esperados no exemplo sintetico
COM_ACHADO = {
    "C03": 1, "C04": 1, "C05": 1, "C07": 1,
    "E03": 1, "E11": 1, "E12": 1, "E13": 1, "E14": 1, "E15": 2, "E16": 1,
    "E20": 1, "E21": 1,
    "E26": 1, "E27": 1, "E28": 1, "E29": 1,
    "R01": 2, "R07": 1, "R08": 2, "R09": 2, "R10": 1, "R11": 1, "R12": 1, "R13": 1,
    "R14": 1, "R15": 1, "R16": 2, "R17": 2, "R18": 2, "R19": 2,
    "T01": 2, "T02": 1, "T03": 1, "T04": 1,
}

# checks sem nenhum erro proposital no exemplo: devem terminar "limpos"
SEM_ACHADO = [
    "C01", "C02", "C06", "C08",
    "E01", "E02", "E04", "E05", "E06", "E07", "E08", "E09", "E10",
    "E17", "E18", "E19", "E22", "E23", "E24", "E25",
    "R02", "R03", "R04", "R05", "R06",
]


@pytest.fixture(scope="session")
def resultado():
    subprocess.run([sys.executable, "gerar_exemplo.py"],
                    cwd=RAIZ, check=True, capture_output=True)
    doc = Documento(str(RAIZ / "exemplo_sped.txt"))
    return {c.id: achados for c, achados in executar(doc)}


def test_cobertura_do_exemplo_bate_com_o_registro(resultado):
    esperado = set(COM_ACHADO) | set(SEM_ACHADO)
    ids_registrados = {c.id for c in REGISTRY}
    assert esperado == ids_registrados, (
        "COM_ACHADO/SEM_ACHADO neste teste ficaram fora de sincronia com "
        f"REGISTRY -- faltando: {ids_registrados - esperado}, "
        f"sobrando: {esperado - ids_registrados}"
    )


@pytest.mark.parametrize("check_id,esperado", sorted(COM_ACHADO.items()))
def test_check_dispara_com_a_contagem_esperada(resultado, check_id, esperado):
    achados = resultado[check_id]
    assert len(achados) == esperado, (
        f"{check_id}: esperado {esperado} achado(s), obtido {len(achados)}"
    )


@pytest.mark.parametrize("check_id", sorted(SEM_ACHADO))
def test_check_fica_limpo_no_exemplo(resultado, check_id):
    assert resultado[check_id] == [], (
        f"{check_id} nao deveria ter achado no exemplo, "
        f"obtido {len(resultado[check_id])} (possivel falso positivo)"
    )


def test_ids_de_check_sao_unicos():
    ids = [c.id for c in REGISTRY]
    assert len(ids) == len(set(ids)), "ID de check duplicado no REGISTRY"


def test_todo_achado_tem_severidade_e_titulo_declarados():
    for c in REGISTRY:
        assert c.severidade in ("ALTA", "MEDIA", "BAIXA"), c.id
        assert c.titulo.strip(), c.id
        assert c.base.strip(), f"{c.id}: base legal/tecnica vazia"


def test_checks_estendido_estao_marcados_por_dependerem_de_registro_nao_verificado():
    """Todo check que le um registro ESTENDIDO deve, ele mesmo, carregar a
    tag confianca=ESTENDIDO -- senao o laudo mostraria confianca alta para
    um achado apoiado em leiaute nao conferido.

    Apos a reconciliacao contra o PDF oficial (file.pdf, Guia Pratico
    v1.35), os registros que antes eram ESTENDIDO (0400, 0500, C501,
    C505, D101, D105, A170, F100, M410, M810) foram confirmados campo a
    campo e promovidos a NUCLEO -- por isso o conjunto esperado e vazio.
    """
    esperado_estendido = set()
    reais = {c.id for c in REGISTRY if c.confianca == "ESTENDIDO"}
    assert reais == esperado_estendido, (
        f"checks marcados ESTENDIDO mudaram: {reais}. Se isso for "
        "intencional, atualize esperado_estendido neste teste."
    )
