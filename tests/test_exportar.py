"""Testes unitarios dos exportadores (audita/exportar.py).

Cobre as correcoes da rodada de hardening pos-auditoria:
- F3: CSV/Formula Injection na exportacao CSV.
- F4: marcacao nao escapada antes de Paragraph() na exportacao PDF.
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from audita.exportar import _celula_segura, _texto_pdf, para_csv, para_pdf  # noqa: E402


# --- F3: CSV / Formula Injection --------------------------------------------

def test_celula_segura_neutraliza_formula_igual():
    assert _celula_segura('=HYPERLINK("http://x","clique")') == \
        "'=HYPERLINK(\"http://x\",\"clique\")"


def test_celula_segura_neutraliza_outros_gatilhos_de_formula():
    for gatilho in ("+cmd|calc", "-2+3", "@SUM(A1:A2)"):
        resultado = _celula_segura(gatilho)
        assert resultado.startswith("'"), gatilho
        assert resultado[1:] == gatilho


def test_celula_segura_preserva_texto_normal():
    assert _celula_segura("NF 12345") == "NF 12345"
    assert _celula_segura("Parafuso M6") == "Parafuso M6"


def test_celula_segura_none_vira_string_vazia():
    assert _celula_segura(None) == ""


def _laudo_minimo(referencia, detalhe):
    return {
        "empresa": {"nome": "EMPRESA TESTE", "cnpj": "11.222.333/0001-81",
                    "competencia_ini": "01/01/2024", "competencia_fim": "31/01/2024"},
        "arquivo": {"total_linhas": 10, "tipos_registro": 3, "regime": "Nao-cumulativo"},
        "resumo": {"total_checks": 1, "sem_achado": 0, "com_achado": 1,
                   "ocorrencias": 1, "valor_total": 100.0,
                   "por_caixa": {"RISCO": 1, "OPORTUNIDADE": 0, "ESTRUTURA": 0},
                   "por_severidade": {"ALTA": 1, "MEDIA": 0, "BAIXA": 0}},
        "checks": [{
            "id": "E11", "titulo": "Item sem NCM", "caixa": "ESTRUTURA",
            "cor_caixa": "#2980b9", "severidade": "ALTA", "cor_severidade": "#c0392b",
            "base": "teste", "confianca": "NUCLEO", "n_ocorrencias": 1,
            "valor": 100.0, "tem_achado": True,
            "ocorrencias": [{"linha": 12, "registro": "0200", "referencia": referencia,
                             "detalhe": detalhe, "valor": 100.0}],
        }],
        "gerado_em": "17/07/2026 10:00",
    }


def test_para_csv_neutraliza_formula_vinda_do_arquivo_sped():
    """Simula um DESCR_ITEM malicioso vindo do proprio arquivo SPED --
    a celula no CSV final nao pode comecar com caractere de formula."""
    laudo = _laudo_minimo("item 1", '=HYPERLINK("http://malicioso")')
    csv_bytes = para_csv(laudo)
    texto = csv_bytes.decode("utf-8-sig")
    assert '"\'=HYPERLINK' in texto or "'=HYPERLINK" in texto
    assert '\n=HYPERLINK' not in texto  # nunca cru, sem o apostrofo de neutralizacao


# --- F4: escape de marcacao no PDF ------------------------------------------

def test_texto_pdf_escapa_caracteres_de_marcacao():
    # xml.sax.saxutils.escape() cobre os 3 caracteres que quebram o parser
    # de marcacao do reportlab em texto (nao-atributo): & < > . Aspas nao
    # precisam de escape fora de atributo XML, entao ficam intactas.
    assert _texto_pdf("Parafuso < 10mm & porca") == "Parafuso &lt; 10mm &amp; porca"
    assert _texto_pdf("preco > custo") == "preco &gt; custo"
    assert _texto_pdf('aspas "duplas"') == 'aspas "duplas"'


def test_texto_pdf_none_vira_string_vazia():
    assert _texto_pdf(None) == ""


def test_para_pdf_nao_quebra_com_caracteres_de_marcacao_no_arquivo():
    """Regressao do achado F4: NOME/DESCR_ITEM/referencia vindos do arquivo
    podem conter '<' ou '&' soltos -- antes da correcao isso quebrava o
    parser de marcacao do reportlab (Paragraph) e derrubava a geracao do
    PDF inteiro com excecao nao tratada."""
    laudo = _laudo_minimo("item <1> & cia", "Parafuso M6 < 10mm & porca \"especial\"")
    pdf_bytes = para_pdf(laudo)
    assert pdf_bytes[:4] == b"%PDF"
