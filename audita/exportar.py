"""Exportadores do laudo: CSV e PDF."""
import csv
import io

from .report import linhas_csv


def para_csv(laudo):
    """Devolve os bytes de um CSV (utf-8-sig, abre no Excel-BR)."""
    linhas = linhas_csv(laudo)
    buf = io.StringIO()
    campos = ["check", "titulo", "severidade", "caixa", "confianca", "linha", "registro",
              "referencia", "detalhe", "valor", "base"]
    w = csv.DictWriter(buf, fieldnames=campos)
    w.writeheader()
    for l in linhas:
        w.writerow(l)
    return buf.getvalue().encode("utf-8-sig")


def para_pdf(laudo):
    """Devolve os bytes de um PDF formatado com reportlab."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                    Paragraph, Spacer)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=15 * mm, bottomMargin=15 * mm,
        title="Laudo de Auditoria EFD-Contribuicoes",
    )
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontSize=16,
                        textColor=colors.HexColor("#1a2b47"), spaceAfter=2)
    sub = ParagraphStyle("sub", parent=styles["Normal"], fontSize=9,
                         textColor=colors.HexColor("#555555"))
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=12,
                        textColor=colors.HexColor("#1a2b47"), spaceBefore=10,
                        spaceAfter=4)
    normal = ParagraphStyle("n", parent=styles["Normal"], fontSize=8,
                            leading=10)
    small = ParagraphStyle("sm", parent=styles["Normal"], fontSize=7,
                           leading=9, textColor=colors.HexColor("#666666"))

    el = []
    emp = laudo["empresa"]
    arq = laudo["arquivo"]
    res = laudo["resumo"]

    el.append(Paragraph("Laudo de Auditoria &mdash; EFD-Contribuicoes", h1))
    el.append(Paragraph(
        f"{emp['nome']} &nbsp;|&nbsp; CNPJ {emp['cnpj']} &nbsp;|&nbsp; "
        f"competencia {emp['competencia_ini']} a {emp['competencia_fim']}", sub))
    el.append(Paragraph(
        f"Regime: {arq['regime']} &nbsp;|&nbsp; {arq['total_linhas']:,} linhas "
        f"&nbsp;|&nbsp; {arq['tipos_registro']} tipos de registro "
        f"&nbsp;|&nbsp; gerado em {laudo['gerado_em']}", sub))
    el.append(Spacer(1, 8))

    # Resumo em tabela
    resumo_data = [
        ["Checks executados", str(res["total_checks"])],
        ["Sem achado", str(res["sem_achado"])],
        ["Com achado", str(res["com_achado"])],
        ["Total de ocorrencias", str(res["ocorrencias"])],
        ["Valor sob analise", f"R$ {res['valor_total']:,.2f}"],
        ["Achados ALTA / MEDIA / BAIXA",
         f"{res['por_severidade']['ALTA']} / {res['por_severidade']['MEDIA']} / {res['por_severidade']['BAIXA']}"],
    ]
    t = Table(resumo_data, colWidths=[70 * mm, 100 * mm])
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#1a2b47")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1),
         [colors.white, colors.HexColor("#f2f4f8")]),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#dddddd")),
    ]))
    el.append(t)

    # Achados
    cor_sev = {"ALTA": colors.HexColor("#c0392b"),
               "MEDIA": colors.HexColor("#e67e22"),
               "BAIXA": colors.HexColor("#b7950b")}

    achados = [c for c in laudo["checks"] if c["tem_achado"]]
    el.append(Paragraph(f"Achados ({len(achados)})", h2))

    if not achados:
        el.append(Paragraph("Nenhum achado. Arquivo integro nos checks aplicados.",
                            normal))

    for c in achados:
        val = f" &nbsp;|&nbsp; R$ {c['valor']:,.2f}" if c["valor"] else ""
        estendido = (" &nbsp;|&nbsp; <font color='#b7950b'>ESTENDIDO - leiaute pendente "
                     "de conferencia, tratar como pista</font>") if c["confianca"] == "ESTENDIDO" else ""
        titulo = (f"<b><font color='{cor_sev.get(c['severidade'], colors.black)}'>"
                  f"[{c['severidade']}]</font> {c['id']} &mdash; {c['titulo']}</b>")
        el.append(Spacer(1, 6))
        el.append(Paragraph(titulo, normal))
        el.append(Paragraph(
            f"{c['caixa']} &nbsp;|&nbsp; {c['n_ocorrencias']} ocorrencia(s){val}{estendido}"
            f"<br/>base: {c['base']}", small))

        dados = [["Linha", "Reg.", "Referencia", "Detalhe", "Valor R$"]]
        for a in c["ocorrencias"][:200]:
            dados.append([
                f"L{a['linha']}" if a["linha"] else "-",
                a["registro"],
                Paragraph(a["referencia"][:40], small),
                Paragraph(a["detalhe"][:80], small),
                f"{a['valor']:,.2f}" if a["valor"] else "",
            ])
        tab = Table(dados, colWidths=[14 * mm, 14 * mm, 42 * mm, 78 * mm, 22 * mm],
                    repeatRows=1)
        tab.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a2b47")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, colors.HexColor("#f7f8fa")]),
            ("ALIGN", (4, 0), (4, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#dddddd")),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        el.append(tab)
        if c["n_ocorrencias"] > 200:
            el.append(Paragraph(
                f"... mais {c['n_ocorrencias'] - 200} ocorrencia(s) no CSV completo.",
                small))

    el.append(Spacer(1, 12))
    el.append(Paragraph(
        "Diagnostico tecnico do arquivo. Nao constitui parecer fiscal.", small))

    doc.build(el)
    return buf.getvalue()
