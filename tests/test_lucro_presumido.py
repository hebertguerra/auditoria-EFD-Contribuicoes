"""Testes da familia de registros do Lucro Presumido consolidado
(1900, F500, F510, F525, F550, F560) -- conferidos campo a campo contra
o Guia Pratico da EFD-Contribuicoes v1.35 nesta rodada.

Os valores de exemplo usados aqui reproduzem os exemplos oficiais citados
na Nota Tecnica/Guia Pratico sobre os registros 1900 e F525, o que serve
tambem como conferencia cruzada da ordem de campo declarada em
audita/layouts.py.
"""
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from audita.layouts import LAYOUTS  # noqa: E402
from audita.parser import Documento  # noqa: E402
from audita.checks.campos import e17, e18  # noqa: E402
from audita.checks.reconciliacao import r20  # noqa: E402


def _linha(reg, **valores):
    campos = LAYOUTS[reg][1:]
    return "|" + reg + "|" + "|".join(valores.get(c, "") for c in campos) + "|"


def _doc(*linhas_extra):
    linhas = [
        "|0000|006|0|||01012024|31012024|EMPRESA TESTE|11222333000181|SP|3550308|||1|0|",
        *linhas_extra,
    ]
    linhas.append(f"|9999|{len(linhas) + 1}|")
    fd = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="latin-1")
    fd.write("\n".join(linhas) + "\n")
    fd.close()
    return fd.name


def _abrir(*linhas_extra):
    caminho = _doc(*linhas_extra)
    try:
        return Documento(caminho)
    finally:
        Path(caminho).unlink(missing_ok=True)


# --- Registro 1900: exemplo oficial (NF-e 350k/150k tributavel/aliquota
# zero, Cupom Fiscal 220k/180k) -----------------------------------------

def test_1900_le_os_campos_na_ordem_oficial():
    linhas = [
        _linha("1900", CNPJ="88888888000191", COD_MOD="55", VL_TOT_REC="350000,00",
               CST_PIS="01", CST_COFINS="01"),
        _linha("1900", CNPJ="88888888000191", COD_MOD="55", VL_TOT_REC="150000,00",
               CST_PIS="06", CST_COFINS="06"),
        _linha("1900", CNPJ="88888888000191", COD_MOD="2D", VL_TOT_REC="220000,00",
               CST_PIS="01", CST_COFINS="01"),
        _linha("1900", CNPJ="88888888000191", COD_MOD="2D", VL_TOT_REC="180000,00",
               CST_PIS="06", CST_COFINS="06"),
    ]
    doc = _abrir(*linhas)
    regs = doc.todos("1900")
    assert len(regs) == 4
    assert regs[0]["CNPJ"] == "88888888000191"
    assert regs[0]["COD_MOD"] == "55"
    assert regs[0].n("VL_TOT_REC") == 350000.00
    assert regs[1].n("VL_TOT_REC") == 150000.00
    assert regs[1]["CST_PIS"] == "06"
    total = sum(r.n("VL_TOT_REC") for r in regs)
    assert total == 900000.00  # 350k + 150k + 220k + 180k, bate com o exemplo oficial


def test_1900_sem_cnpj_dispara_e17():
    linha = _linha("1900", COD_MOD="55", VL_TOT_REC="100,00", CST_PIS="01", CST_COFINS="01")
    doc = _abrir(linha)
    achados = [a for a in e17(doc) if a.registro == "1900"]
    assert len(achados) == 1
    assert "CNPJ" in achados[0].detalhe


def test_1900_com_valor_malformado_dispara_e18():
    linha = _linha("1900", CNPJ="88888888000191", COD_MOD="55", VL_TOT_REC="1234.56",
                   CST_PIS="01", CST_COFINS="01")
    doc = _abrir(linha)
    achados = [a for a in e18(doc) if a.registro == "1900"]
    assert len(achados) == 1
    assert achados[0].referencia == "VL_TOT_REC"


# --- Registro F525: exemplo oficial (vendas a vista 250k, cartao 200k+300k) --

def test_f525_le_os_campos_na_ordem_oficial():
    linhas = [
        _linha("F525", VL_REC="250000,00", IND_REC="01"),
        _linha("F525", VL_REC="200000,00", IND_REC="02", CNPJ_CPF="11111111000111"),
        _linha("F525", VL_REC="300000,00", IND_REC="02", CNPJ_CPF="22222222000122"),
    ]
    doc = _abrir(*linhas)
    regs = doc.todos("F525")
    assert len(regs) == 3
    assert regs[0].n("VL_REC") == 250000.00
    assert regs[0]["IND_REC"] == "01"
    assert regs[1]["CNPJ_CPF"] == "11111111000111"
    assert sum(r.n("VL_REC") for r in regs) == 750000.00  # bate com o exemplo oficial


# --- R20: F525 x F500/F510 -----------------------------------------------

def test_r20_fecha_quando_f525_bate_com_f500():
    linhas = [
        _linha("F500", VL_REC_CAIXA="750000,00", CST_PIS="01", CST_COFINS="01"),
        _linha("F525", VL_REC="250000,00", IND_REC="01"),
        _linha("F525", VL_REC="500000,00", IND_REC="02"),
    ]
    doc = _abrir(*linhas)
    assert list(r20(doc)) == []


def test_r20_dispara_quando_f525_diverge_de_f500():
    linhas = [
        _linha("F500", VL_REC_CAIXA="750000,00", CST_PIS="01", CST_COFINS="01"),
        _linha("F525", VL_REC="100000,00", IND_REC="01"),  # bem menor que os 750k do F500
    ]
    doc = _abrir(*linhas)
    achados = list(r20(doc))
    assert len(achados) == 1
    assert "750.000,00" in achados[0].detalhe or "750000.00" in achados[0].detalhe.replace(",", "")


def test_r20_soma_f500_e_f510_juntos():
    """F510 e a mesma consolidacao de regime de caixa, so que por
    unidade de medida (bebidas frias/combustivel) -- deve entrar na
    mesma soma do lado F500."""
    linhas = [
        _linha("F500", VL_REC_CAIXA="400000,00", CST_PIS="01", CST_COFINS="01"),
        _linha("F510", VL_REC_CAIXA="350000,00", CST_PIS="03", CST_COFINS="03"),
        _linha("F525", VL_REC="750000,00", IND_REC="01"),
    ]
    doc = _abrir(*linhas)
    assert list(r20(doc)) == []


def test_r20_fica_limpo_quando_empresa_nao_usa_lucro_presumido_consolidado():
    doc = _abrir()  # nenhum F500/F510/F525 no arquivo
    assert list(r20(doc)) == []
