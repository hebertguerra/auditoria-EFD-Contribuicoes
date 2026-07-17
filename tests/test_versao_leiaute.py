"""Testes unitarios do check E31 (COD_VER x versao de leiaute modelada).

Ver Guia Pratico, Tabela 3.1.1 (Versao do Leiaute) -- COD_VER e uma tabela
independente da versao do PROPRIO Guia Pratico como documento (ex.: "versao
1.35"). audita/layouts.py foi modelado contra COD_VER="006" (leiaute
3.2.0, vigente desde 01/01/2020); gerar_exemplo.py ja usa esse codigo, por
isso o exemplo sintetico fica limpo neste check (ver SEM_ACHADO em
test_checks.py).
"""
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from audita.parser import Documento  # noqa: E402
from audita.checks.estrutura import e31  # noqa: E402


def _doc_com_cod_ver(valor):
    linhas = [
        f"|0000|{valor}|0|||01012024|31012024|EMPRESA TESTE|11222333000181|SP|3550308|||1|0|",
        "|9999|2|",
    ]
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                     encoding="latin-1") as f:
        f.write("\n".join(linhas) + "\n")
        caminho = f.name
    try:
        return Documento(caminho)
    finally:
        Path(caminho).unlink(missing_ok=True)


def test_cod_ver_igual_ao_modelado_fica_limpo():
    doc = _doc_com_cod_ver("006")
    assert list(e31(doc)) == []


def test_cod_ver_vazio_fica_limpo():
    """Campo vazio e responsabilidade do E17 (obrigatorio), nao deste check."""
    doc = _doc_com_cod_ver("")
    assert list(e31(doc)) == []


def test_cod_ver_leiaute_antigo_m210_gera_achado_especifico():
    """001-004 usam o leiaute antigo de M210/M610 (13 campos) -- risco real
    e ja documentado de desalinhamento silencioso de campo."""
    for codigo in ("001", "002", "003", "004"):
        doc = _doc_com_cod_ver(codigo)
        achados = list(e31(doc))
        assert len(achados) == 1, codigo
        assert "M210/M610" in achados[0].detalhe
        assert "desalinhados" in achados[0].detalhe


def test_cod_ver_005_gera_achado_generico_sem_mencionar_m210():
    """005 ja tem o leiaute vigente de M210/M610 -- a divergencia e sobre
    outros registros (1011, CHV_DOCe) adicionados so na 006."""
    doc = _doc_com_cod_ver("005")
    achados = list(e31(doc))
    assert len(achados) == 1
    assert "M210/M610" not in achados[0].detalhe
    assert "1011" in achados[0].detalhe


def test_cod_ver_desconhecido_gera_achado_de_versao_futura():
    """Codigo fora da Tabela 3.1.1 conhecida: pode ser uma versao de
    leiaute publicada depois desta reconciliacao -- sinalizar, nao afirmar
    que esta errado."""
    doc = _doc_com_cod_ver("009")
    achados = list(e31(doc))
    assert len(achados) == 1
    assert "publicada depois desta reconciliacao" in achados[0].detalhe


def test_cod_ver_sem_registro_0000_nao_quebra():
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                     encoding="latin-1") as f:
        f.write("|9999|2|\n")
        caminho = f.name
    try:
        doc = Documento(caminho)
        assert list(e31(doc)) == []
    finally:
        Path(caminho).unlink(missing_ok=True)
