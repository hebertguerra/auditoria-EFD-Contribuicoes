"""Testes do processamento em lote (audita/lote.py).

O usuario nao declara nada sobre o conjunto que esta enviando -- o
agrupamento por CNPJ e a ordenacao por competencia vem so dos dados que
cada arquivo ja carrega no proprio registro 0000. Estes testes cobrem
esse agrupamento automatico e os avisos de consistencia entre periodos
(duplicata, buraco, sobreposicao).
"""
import sys
import tempfile
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from audita.lote import gerar_lote  # noqa: E402

CNPJ_A = "11222333000181"
CNPJ_B = "11444777000161"


def _sped_minimo(cnpj, dt_ini, dt_fim, qtd_lin_errada=False, nome="EMPRESA TESTE"):
    """Arquivo minimo, valido o bastante para virar um Documento -- so os
    registros de abertura/fechamento. qtd_lin_errada=True faz o check E03
    disparar de proposito (util para testar o ranking de reincidencia sem
    depender de um erro fiscal de verdade)."""
    linha_9999 = "|9999|" + ("99" if qtd_lin_errada else "2") + "|"
    linhas = [
        f"|0000|006|0|||{dt_ini}|{dt_fim}|{nome}|{cnpj}|SP|3550308|||1|0|",
        linha_9999,
    ]
    fd = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="latin-1")
    fd.write("\n".join(linhas) + "\n")
    fd.close()
    return fd.name


@pytest.fixture
def _limpeza():
    caminhos = []
    yield caminhos
    for c in caminhos:
        Path(c).unlink(missing_ok=True)


def test_agrupa_por_cnpj_e_ordena_por_competencia_independente_da_ordem_de_upload(_limpeza):
    mar = _sped_minimo(CNPJ_A, "01032024", "31032024"); _limpeza.append(mar)
    jan = _sped_minimo(CNPJ_A, "01012024", "31012024"); _limpeza.append(jan)
    fev = _sped_minimo(CNPJ_A, "01022024", "29022024"); _limpeza.append(fev)

    # upload fora de ordem de proposito -- o usuario nao deveria precisar
    # selecionar os arquivos em ordem cronologica
    lote = gerar_lote([(mar, "mar.txt"), (jan, "jan.txt"), (fev, "fev.txt")])

    assert len(lote["grupos"]) == 1
    assert lote["multiplos_cnpj"] is False
    nomes_em_ordem = [p["nome_original"] for p in lote["grupos"][0]["periodos"]]
    assert nomes_em_ordem == ["jan.txt", "fev.txt", "mar.txt"]


def test_cnpjs_diferentes_viram_grupos_separados(_limpeza):
    a = _sped_minimo(CNPJ_A, "01012024", "31012024", nome="EMPRESA A"); _limpeza.append(a)
    b = _sped_minimo(CNPJ_B, "01012024", "31012024", nome="EMPRESA B"); _limpeza.append(b)

    lote = gerar_lote([(a, "a.txt"), (b, "b.txt")])

    assert lote["multiplos_cnpj"] is True
    assert len(lote["grupos"]) == 2
    nomes = sorted(g["nome"] for g in lote["grupos"])
    assert nomes == ["EMPRESA A", "EMPRESA B"]


def test_sequencia_limpa_nao_gera_aviso(_limpeza):
    jan = _sped_minimo(CNPJ_A, "01012024", "31012024"); _limpeza.append(jan)
    fev = _sped_minimo(CNPJ_A, "01022024", "29022024"); _limpeza.append(fev)

    lote = gerar_lote([(jan, "jan.txt"), (fev, "fev.txt")])

    assert lote["grupos"][0]["avisos"] == []


def test_competencia_duplicada_gera_aviso(_limpeza):
    jan1 = _sped_minimo(CNPJ_A, "01012024", "31012024"); _limpeza.append(jan1)
    jan2 = _sped_minimo(CNPJ_A, "01012024", "31012024"); _limpeza.append(jan2)

    lote = gerar_lote([(jan1, "jan_v1.txt"), (jan2, "jan_v2.txt")])

    avisos = lote["grupos"][0]["avisos"]
    assert any("mais de um arquivo" in a for a in avisos)


def test_buraco_entre_competencias_gera_aviso(_limpeza):
    jan = _sped_minimo(CNPJ_A, "01012024", "31012024"); _limpeza.append(jan)
    # pula fevereiro de proposito
    mar = _sped_minimo(CNPJ_A, "01032024", "31032024"); _limpeza.append(mar)

    lote = gerar_lote([(jan, "jan.txt"), (mar, "mar.txt")])

    avisos = lote["grupos"][0]["avisos"]
    assert any("faltando no lote" in a for a in avisos)


def test_sobreposicao_de_competencias_gera_aviso(_limpeza):
    jan = _sped_minimo(CNPJ_A, "01012024", "31012024"); _limpeza.append(jan)
    quinzena = _sped_minimo(CNPJ_A, "15012024", "15022024"); _limpeza.append(quinzena)

    lote = gerar_lote([(jan, "jan.txt"), (quinzena, "quinzena.txt")])

    avisos = lote["grupos"][0]["avisos"]
    assert any("sobrepostas" in a for a in avisos)


def test_resumo_consolidado_soma_ocorrencias_dos_periodos(_limpeza):
    jan = _sped_minimo(CNPJ_A, "01012024", "31012024", qtd_lin_errada=True); _limpeza.append(jan)
    fev = _sped_minimo(CNPJ_A, "01022024", "29022024", qtd_lin_errada=True); _limpeza.append(fev)
    mar = _sped_minimo(CNPJ_A, "01032024", "31032024", qtd_lin_errada=False); _limpeza.append(mar)

    lote = gerar_lote([(jan, "jan.txt"), (fev, "fev.txt"), (mar, "mar.txt")])

    resumo = lote["grupos"][0]["resumo"]
    assert resumo["periodos"] == 3
    assert resumo["ocorrencias"] >= 2  # pelo menos os 2 E03 propositais


def test_ranking_reincidencia_identifica_erro_sistemico(_limpeza):
    """E03 dispara em jan e fev, mas nao em mar -- deve aparecer no topo
    do ranking com periodos_com_achado=2 de um total de 3."""
    jan = _sped_minimo(CNPJ_A, "01012024", "31012024", qtd_lin_errada=True); _limpeza.append(jan)
    fev = _sped_minimo(CNPJ_A, "01022024", "29022024", qtd_lin_errada=True); _limpeza.append(fev)
    mar = _sped_minimo(CNPJ_A, "01032024", "31032024", qtd_lin_errada=False); _limpeza.append(mar)

    lote = gerar_lote([(jan, "jan.txt"), (fev, "fev.txt"), (mar, "mar.txt")])

    por_check = {a["id"]: a for a in lote["grupos"][0]["por_check"]}
    assert "E03" in por_check
    assert por_check["E03"]["periodos_com_achado"] == 2
    assert por_check["E03"]["total_periodos"] == 3


def test_lote_de_um_arquivo_so_funciona_sem_avisos(_limpeza):
    jan = _sped_minimo(CNPJ_A, "01012024", "31012024"); _limpeza.append(jan)

    lote = gerar_lote([(jan, "jan.txt")])

    assert lote["total_arquivos"] == 1
    assert len(lote["grupos"]) == 1
    assert lote["grupos"][0]["avisos"] == []
