"""Processamento de multiplos arquivos EFD-Contribuicoes como lote.

Agrupa automaticamente por CNPJ e ordena por competencia -- cada arquivo ja
carrega essa informacao no proprio registro 0000 (campos CNPJ, DT_INI,
DT_FIN), entao o usuario NAO precisa declarar que esta enviando um lote
nem informar qual periodo cada arquivo cobre. A ferramenta so pede atencao
(aviso, nao bloqueio -- o lote e processado de qualquer forma) quando os
arquivos entre si nao formam uma sequencia limpa: CNPJ misto no mesmo
envio, competencia duplicada, buraco ou sobreposicao entre periodos.

O valor do lote sobre processar arquivo por arquivo nao e so a conveniencia
de upload: e o ranking de reincidencia (`por_check` em cada grupo) --
qual erro se repete mes a mes, e nao um evento isolado de um periodo.
"""
from datetime import date, timedelta

from .parser import Documento
from .report import montar_laudo, _fmt_cnpj

_ORDEM_SEVERIDADE = {"ALTA": 0, "MEDIA": 1, "BAIXA": 2}


def _data(d):
    """DDMMAAAA -> date. None se vazio/invalido (ja e responsabilidade do
    check E19 apontar data invalida -- aqui so precisamos saber se dá para
    ordenar/comparar ou nao)."""
    if not d or len(d) != 8 or not d.isdigit():
        return None
    try:
        return date(int(d[4:8]), int(d[2:4]), int(d[0:2]))
    except ValueError:
        return None


def _fmt_data(d):
    return d.strftime("%d/%m/%Y") if d else "?"


def _fmt_periodo(p):
    return f"{_fmt_data(p['dt_ini'])} a {_fmt_data(p['dt_fim'])}"


def gerar_lote(caminhos_com_nome):
    """caminhos_com_nome: lista de (caminho_no_disco, nome_original).

    Devolve um dict com um grupo por CNPJ distinto encontrado nos arquivos
    enviados, cada grupo com periodos ordenados por competencia, avisos de
    consistencia entre periodos, resumo consolidado e ranking de checks
    por reincidencia entre periodos.
    """
    periodos = []
    for caminho, nome_original in caminhos_com_nome:
        doc = Documento(caminho)
        laudo = montar_laudo(doc)
        laudo["arquivo"]["nome_original"] = nome_original
        ini, fim = doc.competencia
        nome, cnpj = doc.empresa
        periodos.append({
            "laudo": laudo,
            "cnpj": cnpj,
            "nome": nome,
            "dt_ini": _data(ini),
            "dt_fim": _data(fim),
            "nome_original": nome_original,
        })

    por_cnpj = {}
    for p in periodos:
        por_cnpj.setdefault(p["cnpj"], []).append(p)

    grupos = []
    for cnpj, itens in por_cnpj.items():
        itens.sort(key=lambda p: p["dt_ini"] or date.min)
        grupos.append({
            "cnpj_fmt": _fmt_cnpj(cnpj),
            "nome": itens[0]["nome"] or "(empresa nao identificada)",
            "periodos": itens,
            "avisos": _avisos_consistencia(itens),
            "resumo": _resumo_consolidado(itens),
            "por_check": _ranking_reincidencia(itens),
        })
    grupos.sort(key=lambda g: g["nome"])

    return {
        "grupos": grupos,
        "total_arquivos": len(periodos),
        "multiplos_cnpj": len(por_cnpj) > 1,
    }


def _avisos_consistencia(itens_ordenados):
    """itens_ordenados: periodos do MESMO cnpj, ja ordenados por dt_ini."""
    avisos = []
    vistas = set()
    anterior = None
    for p in itens_ordenados:
        chave = (p["dt_ini"], p["dt_fim"])
        if chave in vistas:
            avisos.append(f"competência {_fmt_periodo(p)} aparece em mais de um "
                          f"arquivo enviado (ex.: {p['nome_original']})")
        vistas.add(chave)

        if anterior is not None and p["dt_ini"] and anterior["dt_fim"]:
            if p["dt_ini"] > anterior["dt_fim"] + timedelta(days=1):
                avisos.append(f"intervalo sem arquivo entre {_fmt_data(anterior['dt_fim'])} "
                              f"e {_fmt_data(p['dt_ini'])} -- competência(s) faltando no lote")
            elif p["dt_ini"] <= anterior["dt_fim"]:
                avisos.append(f"competências sobrepostas: {anterior['nome_original']} "
                              f"({_fmt_periodo(anterior)}) e {p['nome_original']} "
                              f"({_fmt_periodo(p)})")
        anterior = p
    return avisos


def _resumo_consolidado(itens):
    por_severidade = {"ALTA": 0, "MEDIA": 0, "BAIXA": 0}
    ocorrencias = valor_total = 0
    for p in itens:
        r = p["laudo"]["resumo"]
        ocorrencias += r["ocorrencias"]
        valor_total += r["valor_total"]
        for sev, n in r["por_severidade"].items():
            por_severidade[sev] += n
    return {
        "periodos": len(itens),
        "ocorrencias": ocorrencias,
        "valor_total": valor_total,
        "por_severidade": por_severidade,
    }


def _ranking_reincidencia(itens):
    """Por check, em quantos periodos (dos N do grupo) ele deu achado --
    e o que separa um erro pontual de um erro sistemico que se repete mes
    a mes (ex.: o mesmo CFOP errado usado o ano inteiro)."""
    agregados = {}
    for p in itens:
        for c in p["laudo"]["checks"]:
            if not c["tem_achado"]:
                continue
            a = agregados.setdefault(c["id"], {
                "id": c["id"], "titulo": c["titulo"], "caixa": c["caixa"],
                "cor_caixa": c["cor_caixa"], "severidade": c["severidade"],
                "cor_severidade": c["cor_severidade"], "confianca": c["confianca"],
                "periodos_com_achado": 0, "ocorrencias_total": 0, "valor_total": 0.0,
            })
            a["periodos_com_achado"] += 1
            a["ocorrencias_total"] += c["n_ocorrencias"]
            a["valor_total"] += c["valor"]

    total_periodos = len(itens)
    lista = list(agregados.values())
    for a in lista:
        a["total_periodos"] = total_periodos
    lista.sort(key=lambda a: (-a["periodos_com_achado"],
                              _ORDEM_SEVERIDADE.get(a["severidade"], 9), a["id"]))
    return lista
