"""Testes do check C06 (mesmo item, CST diferente na competencia).

Cobre a correcao que separa documento complementar (COD_SIT=06) de
documento regular na comparacao de CST por item -- descoberta numa
investigacao real (auditoria de arquivo de producao): um item com 88
saidas tinha CST 08 em 86 documentos regulares e CST 09 nos outros 2, que
eram documentos complementares. Comparar as duas categorias juntas gerava
falso positivo, porque documento complementar pode legitimamente ter
natureza tributaria diferente do documento original (nao e erro de
cadastro/parametrizacao do item).
"""
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from audita.layouts import LAYOUTS  # noqa: E402
from audita.parser import Documento  # noqa: E402
from audita.checks.coerencia import c06  # noqa: E402


def _linha(reg, **valores):
    """Monta uma linha pipe-delimitada na ordem oficial de LAYOUTS[reg],
    preenchendo com vazio o que nao for informado -- imune a erro de
    contagem manual de posicao de campo."""
    campos = LAYOUTS[reg][1:]  # sem REG, que e fixo (vem do proprio reg)
    return "|" + reg + "|" + "|".join(valores.get(c, "") for c in campos) + "|"


def _doc(linhas_c100_c170):
    """linhas_c100_c170: lista de (cod_sit, cod_item, cst_pis) -- cada
    tupla vira um C100 (saida) com um C170 filho."""
    linhas = [
        "|0000|006|0|||01012024|31012024|EMPRESA TESTE|11222333000181|SP|3550308|||1|0|",
        "|C010|11222333000181|0|",
    ]
    for i, (cod_sit, cod_item, cst_pis) in enumerate(linhas_c100_c170, 1):
        linhas.append(_linha("C100", IND_OPER="1", IND_EMIT="0", COD_PART="999",
                             COD_MOD="55", COD_SIT=cod_sit, SER="1", NUM_DOC=str(i),
                             DT_DOC="15012024", DT_E_S="15012024", VL_DOC="100,00",
                             IND_PGTO="1"))
        linhas.append(_linha("C170", NUM_ITEM="1", COD_ITEM=cod_item, VL_ITEM="100,00",
                             CFOP="5101", CST_PIS=cst_pis, VL_BC_PIS="100,00",
                             CST_COFINS=cst_pis))
    linhas.append(f"|9999|{len(linhas) + 1}|")
    fd = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="latin-1")
    fd.write("\n".join(linhas) + "\n")
    fd.close()
    return fd.name


def _rodar(linhas_c100_c170):
    caminho = _doc(linhas_c100_c170)
    try:
        return list(c06(Documento(caminho)))
    finally:
        Path(caminho).unlink(missing_ok=True)


def test_cst_divergente_entre_documentos_regulares_ainda_dispara():
    """O caso que o check deve continuar pegando: mesmo item, CST
    diferente, ambos documentos regulares (COD_SIT=00) -- indicio real de
    cadastro/parametrizacao inconsistente."""
    achados = _rodar([("00", "ITEM1", "01"), ("00", "ITEM1", "02")])
    assert len(achados) == 1
    assert "complementares" not in achados[0].referencia


def test_cst_divergente_entre_regular_e_complementar_nao_dispara():
    """Regressao do achado real: CST 08 em documentos regulares e CST 09
    em documentos complementares (COD_SIT=06) do mesmo item NAO deveria
    disparar -- naturezas de documento diferentes, nao erro de item."""
    achados = _rodar([
        ("00", "ITEM1", "08"), ("00", "ITEM1", "08"), ("00", "ITEM1", "08"),
        ("06", "ITEM1", "09"), ("06", "ITEM1", "09"),
    ])
    assert achados == []


def test_cst_divergente_dentro_dos_proprios_complementares_ainda_dispara():
    """Dois documentos complementares do MESMO item com CST diferente
    ENTRE SI continua sendo um sinal a investigar -- a excecao e so para
    nao comparar complementar contra regular."""
    achados = _rodar([("06", "ITEM1", "09"), ("06", "ITEM1", "07")])
    assert len(achados) == 1
    assert "complementares" in achados[0].referencia


def test_item_so_com_documentos_regulares_do_mesmo_cst_fica_limpo():
    achados = _rodar([("00", "ITEM1", "01"), ("00", "ITEM1", "01")])
    assert achados == []
