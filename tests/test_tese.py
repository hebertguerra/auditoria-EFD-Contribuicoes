"""Teste do check T05 (ajuste de reducao linear de incentivos -- LC 224/2025).

Baseado nos exemplos numericos da Nota Tecnica EFD-Contribuicoes no
012/2026 (Exemplo pratico 1: M220 com COD_AJ=11; Exemplo pratico 2: M110
com COD_AJ=12) -- os dois codigos que a nota introduz na Tabela 4.3.8.
"""
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from audita.layouts import LAYOUTS  # noqa: E402
from audita.parser import Documento  # noqa: E402
from audita.checks.tese import t05  # noqa: E402


def _linha(reg, **valores):
    campos = LAYOUTS[reg][1:]
    return "|" + reg + "|" + "|".join(valores.get(c, "") for c in campos) + "|"


def _doc(*linhas_ajuste):
    linhas = [
        "|0000|006|0|||01042026|30042026|EMPRESA TESTE|11222333000181|SP|3550308|||1|0|",
        *linhas_ajuste,
    ]
    linhas.append(f"|9999|{len(linhas) + 1}|")
    fd = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="latin-1")
    fd.write("\n".join(linhas) + "\n")
    fd.close()
    return fd.name


def _rodar(*linhas_ajuste):
    caminho = _doc(*linhas_ajuste)
    try:
        return list(t05(Documento(caminho)))
    finally:
        Path(caminho).unlink(missing_ok=True)


def test_cod_aj_11_em_m220_dispara_sinalizacao_aliquota_zero():
    """Exemplo pratico 1 da NT 012/2026: ajuste de acrescimo em M220,
    COD_AJ=11, VL_AJ=0,41 (redução de alíquota zero/isenção)."""
    linha = _linha("M220", IND_AJ="1", VL_AJ="0,41", COD_AJ="11",
                   DESCR_AJ="Reducao linear de beneficios fiscais - LC 224/2025",
                   DT_REF="01042026")
    achados = _rodar(linha)
    assert len(achados) == 1
    assert achados[0].registro == "M220"
    assert "aliquota zero" in achados[0].detalhe
    assert achados[0].valor == 0.41


def test_cod_aj_12_em_m110_dispara_sinalizacao_credito_presumido():
    """Exemplo pratico 2 da NT 012/2026: ajuste de reducao em M110,
    COD_AJ=12, VL_AJ=0,06 (limite de 90% no credito presumido)."""
    linha = _linha("M110", IND_AJ="0", VL_AJ="0,06", COD_AJ="12",
                   NUM_DOC="Art. 8 da Lei 10.925/2004",
                   DESCR_AJ="LC 224/2025 - Reducao de beneficios",
                   DT_REF="30042026")
    achados = _rodar(linha)
    assert len(achados) == 1
    assert achados[0].registro == "M110"
    assert "90%" in achados[0].detalhe
    assert achados[0].valor == 0.06


def test_cod_aj_nao_relacionado_nao_dispara():
    linha = _linha("M220", IND_AJ="1", VL_AJ="10,00", COD_AJ="99",
                   DESCR_AJ="Outro motivo", DT_REF="01042026")
    assert _rodar(linha) == []


def test_sem_registros_de_ajuste_fica_limpo():
    assert _rodar() == []


def test_reconhece_nos_quatro_registros_de_ajuste():
    """COD_AJ=11/12 pode aparecer em qualquer um dos 4 registros de ajuste
    (M110/M220 para PIS, M510/M620 para COFINS)."""
    linhas = [
        _linha("M110", IND_AJ="0", VL_AJ="1,00", COD_AJ="12", DT_REF="01042026"),
        _linha("M220", IND_AJ="1", VL_AJ="2,00", COD_AJ="11", DT_REF="01042026"),
        _linha("M510", IND_AJ="0", VL_AJ="3,00", COD_AJ="12", DT_REF="01042026"),
        _linha("M620", IND_AJ="1", VL_AJ="4,00", COD_AJ="11", DT_REF="01042026"),
    ]
    achados = _rodar(*linhas)
    assert len(achados) == 4
    assert {a.registro for a in achados} == {"M110", "M220", "M510", "M620"}
