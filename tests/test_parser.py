"""Testes unitarios do leitor (audita/parser.py).

Cobre as correcoes da rodada de hardening pos-auditoria:
- F2: gramatica numerica SPED nao aceita mais ponto decimal (evitava
  inflacao/deflacao silenciosa de 100x quando um campo vinha malformado).
- F7: COD_INC_TRIB=3 (regime misto) reconhecido como estado proprio, nao
  reduzido a "nao-cumulativo".
- F9: heuristica de encoding incorreto (UTF-8 lido como Latin-1).
"""
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from audita.parser import Documento, num, numero_sped_valido  # noqa: E402


# --- F2: gramatica numerica -------------------------------------------------

def test_numero_valido_aceita_gramatica_sped():
    assert numero_sped_valido("1234,56")
    assert numero_sped_valido("-1234,56")
    assert numero_sped_valido("+1234,56")
    assert numero_sped_valido("1234")
    assert numero_sped_valido("")  # campo vazio: ausencia e responsabilidade do E17


def test_numero_valido_rejeita_ponto_decimal():
    """Formato americano ("1234.56") ou separador de milhar (nao previsto
    no SPED) nao sao gramatica valida -- ANTES desta correcao, num() tratava
    o ponto como separador de milhar e removia, inflando o valor em 100x."""
    assert not numero_sped_valido("1234.56")
    assert not numero_sped_valido("1.234")
    assert not numero_sped_valido("1.234,56")


def test_num_nao_inflaciona_valor_malformado():
    """Regressao direta do achado F2: campo com ponto decimal devolvia
    123456.0 em vez de 1234.56 (100x). Agora devolve 0.0 -- explicito e
    seguro -- em vez de adivinhar o separador."""
    assert num("1234.56") == 0.0
    assert num("1234,56") == 1234.56
    assert num("-1234,56") == -1234.56
    assert num("") == 0.0
    assert num(None) == 0.0


# --- F7: regime misto (COD_INC_TRIB=3) --------------------------------------

def _doc_com_cod_inc_trib(valor):
    linhas = [
        "|0000|017|0|||01012024|31012024|EMPRESA TESTE|11222333000181|SP|3550308|||1|0|",
        f"|0110|{valor}|0|0|0|",
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


def test_regime_cumulativo_reconhece_cod_inc_trib_2():
    doc = _doc_com_cod_inc_trib("2")
    assert doc.regime_cumulativo is True
    assert doc.regime_misto is False


def test_regime_misto_reconhece_cod_inc_trib_3():
    """Antes da correcao, COD_INC_TRIB=3 (regime misto/concomitante) caia
    no mesmo balde que COD_INC_TRIB=1 (100% nao-cumulativo), gerando falso
    positivo de aliquota nos checks C05/T04 para contribuinte que legitima-
    mente escritura as duas aliquotas basicas no mesmo periodo."""
    doc = _doc_com_cod_inc_trib("3")
    assert doc.regime_misto is True
    assert doc.regime_cumulativo is False


def test_regime_nao_cumulativo_padrao():
    doc = _doc_com_cod_inc_trib("1")
    assert doc.regime_cumulativo is False
    assert doc.regime_misto is False


# --- F9: heuristica de encoding ---------------------------------------------

def _doc_com_nome(nome_bytes_latin1):
    """Grava um arquivo cujos bytes brutos de NOME sao os informados,
    simulando o que acontece quando um arquivo UTF-8 e lido como latin-1."""
    linha0000 = ("|0000|017|0|||01012024|31012024|" + nome_bytes_latin1
                 + "|11222333000181|SP|3550308|||1|0|")
    linhas = [linha0000, "|9999|2|"]
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                     encoding="latin-1") as f:
        f.write("\n".join(linhas) + "\n")
        caminho = f.name
    try:
        return Documento(caminho)
    finally:
        Path(caminho).unlink(missing_ok=True)


def test_encoding_correto_nao_dispara_heuristica():
    doc = _doc_com_nome("DISTRIBUIDORA SAO JOSE")
    assert doc.possivel_encoding_incorreto is False


def test_encoding_incorreto_dispara_heuristica():
    """"Distribuição" gravado em UTF-8 e reaberto como latin-1 vira
    "DistribuiÃ§Ã£o" -- padrao caracteristico que a heuristica deve pegar
    quando aparece repetidas vezes no arquivo."""
    nome_mojibake = "DistribuiÃ§Ã£o e ComÃ©rcio de Peças EletrÃ´nicas Ltda"
    doc = _doc_com_nome(nome_mojibake)
    assert doc.possivel_encoding_incorreto is True
