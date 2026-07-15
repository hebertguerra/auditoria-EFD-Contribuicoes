"""Resultado estruturado da auditoria.

Executa os checks e devolve um dicionario reutilizavel pela tela web,
pelo PDF e pelo CSV. Nenhuma dependencia de I/O aqui: so dados.
"""
from datetime import datetime
from .parser import Documento
from .checks import executar

ORDEM = {"ALTA": 0, "MEDIA": 1, "BAIXA": 2}
COR_SEVERIDADE = {"ALTA": "#c0392b", "MEDIA": "#e67e22", "BAIXA": "#f1c40f"}
COR_CAIXA = {"RISCO": "#c0392b", "OPORTUNIDADE": "#27ae60", "ESTRUTURA": "#2980b9"}


def _fmt_data(d):
    """DDMMAAAA -> DD/MM/AAAA."""
    if d and len(d) == 8:
        return f"{d[0:2]}/{d[2:4]}/{d[4:8]}"
    return d or ""


def _fmt_cnpj(c):
    c = "".join(ch for ch in (c or "") if ch.isdigit())
    if len(c) == 14:
        return f"{c[0:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:14]}"
    return c


def gerar_laudo(caminho):
    """Roda a auditoria completa e devolve um dict estruturado."""
    doc = Documento(caminho)
    nome, cnpj = doc.empresa
    ini, fim = doc.competencia

    resultado = executar(doc)
    resultado.sort(key=lambda x: (ORDEM.get(x[0].severidade, 9), x[0].id))

    checks = []
    total_ok = total_falha = total_ocorrencias = 0
    valor_total = 0.0
    por_caixa = {"RISCO": 0, "OPORTUNIDADE": 0, "ESTRUTURA": 0}
    por_severidade = {"ALTA": 0, "MEDIA": 0, "BAIXA": 0}

    for c, achados in resultado:
        valor = sum(a.valor for a in achados)
        item = {
            "id": c.id,
            "titulo": c.titulo,
            "caixa": c.caixa,
            "cor_caixa": COR_CAIXA.get(c.caixa, "#7f8c8d"),
            "severidade": c.severidade,
            "cor_severidade": COR_SEVERIDADE.get(c.severidade, "#7f8c8d"),
            "base": c.base,
            "confianca": c.confianca,
            "n_ocorrencias": len(achados),
            "valor": valor,
            "tem_achado": bool(achados),
            "ocorrencias": [
                {
                    "linha": a.linha,
                    "registro": a.registro,
                    "referencia": a.referencia,
                    "detalhe": a.detalhe,
                    "valor": a.valor,
                }
                for a in achados
            ],
        }
        checks.append(item)
        if achados:
            total_falha += 1
            total_ocorrencias += len(achados)
            valor_total += valor
            por_caixa[c.caixa] = por_caixa.get(c.caixa, 0) + 1
            por_severidade[c.severidade] = por_severidade.get(c.severidade, 0) + 1
        else:
            total_ok += 1

    return {
        "empresa": {
            "nome": nome,
            "cnpj": _fmt_cnpj(cnpj),
            "competencia_ini": _fmt_data(ini),
            "competencia_fim": _fmt_data(fim),
        },
        "arquivo": {
            "total_linhas": doc.total_linhas_arquivo,
            "tipos_registro": len(doc.contagem),
            "regime": "Cumulativo" if doc.regime_cumulativo else "Nao-cumulativo",
        },
        "resumo": {
            "total_checks": len(checks),
            "sem_achado": total_ok,
            "com_achado": total_falha,
            "ocorrencias": total_ocorrencias,
            "valor_total": valor_total,
            "por_caixa": por_caixa,
            "por_severidade": por_severidade,
        },
        "checks": checks,
        "gerado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
    }


def linhas_csv(laudo):
    """Achata o laudo em linhas para CSV."""
    linhas = []
    for c in laudo["checks"]:
        for a in c["ocorrencias"]:
            linhas.append({
                "check": c["id"],
                "titulo": c["titulo"],
                "severidade": c["severidade"],
                "caixa": c["caixa"],
                "confianca": c["confianca"],
                "linha": a["linha"],
                "registro": a["registro"],
                "referencia": a["referencia"],
                "detalhe": a["detalhe"],
                "valor": f"{a['valor']:.2f}",
                "base": c["base"],
            })
    return linhas
