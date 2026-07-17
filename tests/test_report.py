"""Testes do resumo executivo (audita/report.py): top_achados ordenado por
valor e o aviso de causa comum entre R01/R02 e R03 (bloco M ausente).
"""
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from audita.layouts import LAYOUTS  # noqa: E402
from audita.parser import Documento  # noqa: E402
from audita.report import montar_laudo  # noqa: E402


def _linha(reg, **valores):
    campos = LAYOUTS[reg][1:]
    return "|" + reg + "|" + "|".join(valores.get(c, "") for c in campos) + "|"


def _abrir(*linhas_extra):
    linhas = [
        "|0000|006|0|||01012024|31012024|EMPRESA TESTE|11222333000181|SP|3550308|||1|0|",
        "|0110|1|1|1||",
        *linhas_extra,
    ]
    linhas.append(f"|9999|{len(linhas) + 1}|")
    fd = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="latin-1")
    fd.write("\n".join(linhas) + "\n")
    fd.close()
    caminho = fd.name
    try:
        return montar_laudo(Documento(caminho))
    finally:
        Path(caminho).unlink(missing_ok=True)


def _venda_com_pis_cofins(num_doc="1"):
    """C100 (saida) + C170 com PIS/COFINS apurado -- sem nenhum bloco M
    no arquivo, isso sozinho ja dispara R03; e com 0111 zerado, tambem
    dispara R01 (0111 nao reflete a receita do detalhe)."""
    return [
        _linha("C010", CNPJ="11222333000181", IND_ESCRI="0"),
        _linha("C100", IND_OPER="1", IND_EMIT="0", COD_PART="1", COD_MOD="55",
               COD_SIT="00", SER="1", NUM_DOC=num_doc, DT_DOC="15012024",
               DT_E_S="15012024", VL_DOC="1000,00", IND_PGTO="1"),
        _linha("C170", NUM_ITEM="1", COD_ITEM="ITEM1", VL_ITEM="1000,00", CFOP="5102",
               CST_PIS="01", VL_BC_PIS="1000,00", ALIQ_PIS="1,65", VL_PIS="16,50",
               CST_COFINS="01", VL_BC_COFINS="1000,00", ALIQ_COFINS="7,60", VL_COFINS="76,00"),
        _linha("0111", REC_BRU_NCUM_TRIB_MI="0,00", REC_BRU_NCUM_NT_MI="0,00",
               REC_BRU_NCUM_EXP="0,00", REC_BRU_CUM="0,00", REC_BRU_TOTAL="0,00"),
    ]


def test_top_achados_ordenado_por_valor_descendente():
    laudo = _abrir(*_venda_com_pis_cofins())
    top = laudo["resumo"]["top_achados"]
    assert len(top) > 0
    valores = [c["valor"] for c in top]
    assert valores == sorted(valores, reverse=True)


def test_top_achados_limitado_a_cinco():
    laudo = _abrir(*_venda_com_pis_cofins())
    assert len(laudo["resumo"]["top_achados"]) <= 5


def test_aviso_bloco_m_ausente_dispara_com_r01_e_r03_juntos():
    laudo = _abrir(*_venda_com_pis_cofins())
    ids_com_achado = {c["id"] for c in laudo["checks"] if c["tem_achado"]}
    assert "R01" in ids_com_achado
    assert "R03" in ids_com_achado
    aviso = laudo["resumo"]["aviso_bloco_m_ausente"]
    assert aviso is not None
    assert "bloco de apuração" in aviso
    assert "R01" in aviso


def test_aviso_bloco_m_ausente_none_quando_arquivo_limpo():
    laudo = _abrir()  # sem nenhum documento -- nada a reconciliar
    assert laudo["resumo"]["aviso_bloco_m_ausente"] is None


def test_aviso_bloco_m_ausente_none_quando_so_r03_sem_r01_r02():
    """R03 sozinho (sem R01/R02 tambem com achado) nao deveria disparar
    o aviso de correlacao -- a hipotese so faz sentido quando os dois
    aparecem juntos."""
    linhas = [
        _linha("C010", CNPJ="11222333000181", IND_ESCRI="0"),
        _linha("C100", IND_OPER="1", IND_EMIT="0", COD_PART="1", COD_MOD="55",
               COD_SIT="00", SER="1", NUM_DOC="1", DT_DOC="15012024",
               DT_E_S="15012024", VL_DOC="1000,00", IND_PGTO="1"),
        _linha("C170", NUM_ITEM="1", COD_ITEM="ITEM1", VL_ITEM="1000,00", CFOP="5102",
               CST_PIS="01", VL_BC_PIS="1000,00", ALIQ_PIS="1,65", VL_PIS="16,50",
               CST_COFINS="01", VL_BC_COFINS="1000,00", ALIQ_COFINS="7,60", VL_COFINS="76,00"),
        # 0111 preenchido corretamente -- R01 NAO deve disparar
        _linha("0111", REC_BRU_NCUM_TRIB_MI="1000,00", REC_BRU_NCUM_NT_MI="0,00",
               REC_BRU_NCUM_EXP="0,00", REC_BRU_CUM="0,00", REC_BRU_TOTAL="1000,00"),
    ]
    laudo = _abrir(*linhas)
    ids_com_achado = {c["id"] for c in laudo["checks"] if c["tem_achado"]}
    assert "R01" not in ids_com_achado
    assert "R03" in ids_com_achado
    assert laudo["resumo"]["aviso_bloco_m_ausente"] is None


# --- composicao do arquivo -----------------------------------------------

def test_composicao_agrupa_por_bloco_na_ordem_oficial():
    laudo = _abrir(*_venda_com_pis_cofins())
    composicao = laudo["arquivo"]["composicao"]
    letras = [b["letra"] for b in composicao]
    # 0 (abertura), C (mercadorias), 9 (controle) -- nessa ordem, mesmo que
    # os registros tenham sido escriturados fora dessa ordem no arquivo
    assert letras.index("0") < letras.index("C") < letras.index("9")


def test_composicao_conta_registros_certo():
    laudo = _abrir(*_venda_com_pis_cofins())
    composicao = laudo["arquivo"]["composicao"]
    bloco_c = next(b for b in composicao if b["letra"] == "C")
    regs = {r["reg"]: r["qtd"] for r in bloco_c["registros"]}
    assert regs["C100"] == 1
    assert regs["C170"] == 1
    assert bloco_c["nome"] == "Mercadorias (NF-e)"


def test_composicao_nao_lista_bloco_ausente():
    """Se o arquivo nao tem nenhum registro de bloco M, o bloco M
    simplesmente nao aparece na composicao -- e a mesma informacao que
    embasa o aviso_bloco_m_ausente, so que visivel diretamente."""
    laudo = _abrir(*_venda_com_pis_cofins())
    letras = {b["letra"] for b in laudo["arquivo"]["composicao"]}
    assert "M" not in letras


# --- distribuicao de valor por categoria (caixa) --------------------------

def test_valor_por_caixa_soma_certo():
    laudo = _abrir(*_venda_com_pis_cofins())
    r = laudo["resumo"]
    # cada achado com valor entra na categoria (caixa) do proprio check
    soma_categorias = sum(r["valor_por_caixa"].values())
    assert round(soma_categorias, 2) == round(r["valor_total"], 2)


def test_descr_e_cor_caixa_presentes_para_as_tres_categorias():
    laudo = _abrir(*_venda_com_pis_cofins())
    r = laudo["resumo"]
    for cat in ("RISCO", "OPORTUNIDADE", "ESTRUTURA"):
        assert cat in r["descr_caixa"]
        assert cat in r["cor_caixa"]
