"""Resultado estruturado da auditoria.

Executa os checks e devolve um dicionario reutilizavel pela tela web,
pelo PDF e pelo CSV. Nenhuma dependencia de I/O aqui: so dados.
"""
from collections import defaultdict
from datetime import datetime
from .parser import Documento
from .checks import executar
from .layouts import ORDEM_BLOCO, NOME_BLOCO

ORDEM = {"ALTA": 0, "MEDIA": 1, "BAIXA": 2}
COR_SEVERIDADE = {"ALTA": "#c0392b", "MEDIA": "#e67e22", "BAIXA": "#f1c40f"}
COR_CAIXA = {"RISCO": "#c0392b", "OPORTUNIDADE": "#27ae60", "ESTRUTURA": "#2980b9"}
DESCR_CAIXA = {
    "RISCO": "achado com potencial impacto fiscal direto (débito/crédito incorreto)",
    "OPORTUNIDADE": "possível crédito ou receita não aproveitada/consolidada",
    "ESTRUTURA": "inconsistência de forma/leiaute, sem indicar por si só erro de valor",
}


def _composicao_arquivo(doc):
    """Agrupa a contagem de registros do arquivo por bloco, na ordem
    oficial do leiaute. Da visibilidade direta do que o arquivo REALMENTE
    contem -- e do que NAO contem -- sem esperar um check disparar pra
    descobrir (ex.: ver que o bloco M nao tem nenhum M100/M200 antes
    mesmo de ler o achado R03 sobre isso)."""
    por_bloco = defaultdict(list)
    for reg, qtd in doc.contagem.items():
        letra = reg[0] if reg[0] in ORDEM_BLOCO else "?"
        por_bloco[letra].append({"reg": reg, "qtd": qtd})

    blocos = []
    for letra, registros in por_bloco.items():
        registros.sort(key=lambda r: r["reg"])
        blocos.append({
            "letra": letra,
            "nome": NOME_BLOCO.get(letra, "Outros"),
            "registros": registros,
            "total": sum(r["qtd"] for r in registros),
        })
    blocos.sort(key=lambda b: ORDEM_BLOCO.get(b["letra"], 99))
    return blocos


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
    return montar_laudo(doc)


def montar_laudo(doc):
    """Mesma logica de gerar_laudo, mas a partir de um Documento ja lido --
    usado pelo processamento em lote (audita/lote.py) para nao reabrir e
    reparsear o mesmo arquivo duas vezes."""
    nome, cnpj = doc.empresa
    ini, fim = doc.competencia

    resultado = executar(doc)
    resultado.sort(key=lambda x: (ORDEM.get(x[0].severidade, 9), x[0].id))

    checks = []
    total_ok = total_falha = total_ocorrencias = 0
    valor_total = 0.0
    por_caixa = {"RISCO": 0, "OPORTUNIDADE": 0, "ESTRUTURA": 0}
    valor_por_caixa = {"RISCO": 0.0, "OPORTUNIDADE": 0.0, "ESTRUTURA": 0.0}
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
            valor_por_caixa[c.caixa] = valor_por_caixa.get(c.caixa, 0.0) + valor
            por_severidade[c.severidade] = por_severidade.get(c.severidade, 0) + 1
        else:
            total_ok += 1

    # Resumo executivo: os achados que mais pesam em R$, nao por ordem de
    # ID/severidade -- e a pergunta que quem abre o laudo faz primeiro
    # ("por onde eu comeco a olhar"), diferente da lista completa abaixo
    # (essa sim ordenada por severidade, pra nao esconder um achado ALTA
    # de valor pequeno atras de um MEDIA de valor grande).
    com_achado = [c for c in checks if c["tem_achado"]]
    top_achados = sorted(com_achado, key=lambda c: -c["valor"])[:5]

    # E03/R03 (bloco de apuracao M100/M200/M500/M600 ausente) costuma ser
    # a causa raiz por tras de R01/R02 (0111 nao bate com o detalhe) --
    # confirmado numa auditoria real: sem o bloco M, o 0111 tende a nao
    # ter sido recalculado na exportacao. So sinaliza a correlacao quando
    # R03 de fato tem achado (nao e um palpite -- R03 literalmente
    # significa "sem bloco de apuracao"); nunca afirma que E o motivo,
    # so que pode ser, para nao virar conclusao fechada sem revisao.
    por_id = {c["id"]: c for c in com_achado}
    aviso_bloco_m_ausente = None
    if "R03" in por_id and ("R01" in por_id or "R02" in por_id):
        relacionados = [i for i in ("R01", "R02", "R06") if i in por_id]
        aviso_bloco_m_ausente = (
            "O arquivo não tem bloco de apuração (M100/M200 e/ou M500/M600 "
            "— ver achado R03). Isso costuma ser a causa por trás de "
            f"{'/'.join(relacionados)} abaixo: sem o bloco M, o 0111 e a "
            "consolidação de crédito geralmente não foram recalculados "
            "nesta exportação. Confirme se este é o arquivo final antes "
            "de investigar cada achado isoladamente."
        )

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
            "composicao": _composicao_arquivo(doc),
        },
        "resumo": {
            "total_checks": len(checks),
            "sem_achado": total_ok,
            "com_achado": total_falha,
            "ocorrencias": total_ocorrencias,
            "valor_total": valor_total,
            "por_caixa": por_caixa,
            "valor_por_caixa": valor_por_caixa,
            "descr_caixa": DESCR_CAIXA,
            "cor_caixa": COR_CAIXA,
            "por_severidade": por_severidade,
            "top_achados": top_achados,
            "aviso_bloco_m_ausente": aviso_bloco_m_ausente,
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
