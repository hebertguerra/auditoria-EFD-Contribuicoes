"""Reconciliacao: detalhe x bloco M x 0111."""
from collections import defaultdict
from . import check, Achado, RISCO, OPORTUNIDADE, ESTRUTURA
from .coerencia import _itens_pis_cofins
from ..layouts import COD_CONT_NAO_CUMULATIVO, COD_CONT_CUMULATIVO

TOL = 1.00
# Teto absoluto de tolerancia: sem isso, o piso relativo de 0,5% escala sem
# limite para contribuintes grandes (0,5% de uma base de R$ 500 milhoes =
# R$ 2,5 milhoes de divergencia tolerada sem gerar achado). Acima deste
# valor, a divergencia sempre gera achado, mesmo que seja < 0,5% da base.
TETO_TOLERANCIA = 10_000.00


def _tol(valor):
    """Tolerancia de reconciliacao: piso de TOL (R$ 1,00), 0,5% do valor
    declarado, com teto absoluto de TETO_TOLERANCIA -- o menor teto entre
    o relativo e o absoluto que ainda vale."""
    return min(TETO_TOLERANCIA, max(TOL, abs(valor) * 0.005))


def _receita_por_cst(doc):
    trib, nao_trib = 0.0, 0.0
    por_cst = defaultdict(float)
    for i in _itens_pis_cofins(doc):
        if i["saida"] is not True:
            continue
        por_cst[i["cst_c"] or i["cst_p"]] += i["vl_item"]
    for cst, v in por_cst.items():
        if cst in ("01", "02", "03", "05"):
            trib += v
        else:
            nao_trib += v
    return trib, nao_trib, por_cst


@check("R01", "0111 nao reflete a receita do detalhe",
       RISCO, "ALTA", "0111 e a base do rateio de credito e do ressarcimento")
def r01(doc):
    r = doc.um("0111")
    if not r:
        return
    trib, nao_trib, _ = _receita_por_cst(doc)
    pares = (("REC_BRU_NCUM_TRIB_MI", trib, "tributada"),
             ("REC_BRU_NCUM_NT_MI", nao_trib, "nao tributada"))
    for campo, calc, nome in pares:
        decl = r.n(campo)
        if abs(decl - calc) > _tol(calc):
            yield Achado(r.linha, "0111", nome,
                         f"declarado {decl:,.2f} x detalhe {calc:,.2f}",
                         abs(decl - calc))


@check("R02", "Exportacao no detalhe e 0111 zerado",
       OPORTUNIDADE, "ALTA", "CFOP 5501/6501/7xxx - receita de exportacao")
def r02(doc):
    exp = 0.0
    for r in doc.todos("C170"):
        c100 = r.pai
        if not c100 or c100["IND_OPER"] != "1":
            continue
        if r["CFOP"] in ("5501", "6501", "5502", "6502") or r["CFOP"].startswith("7"):
            exp += r.n("VL_ITEM")
    r0111 = doc.um("0111")
    if exp > 0 and r0111 and r0111.n("REC_BRU_NCUM_EXP") <= TOL:
        yield Achado(r0111.linha, "0111", "exportacao",
                     f"detalhe tem {exp:,.2f} em CFOP de exportacao, 0111 declara 0,00",
                     exp)


@check("R03", "Debito no detalhe sem bloco de apuracao",
       ESTRUTURA, "ALTA", "M100/M200 (PIS) e M500/M600 (COFINS)")
def r03(doc):
    deb_p = sum(i["vl_p"] for i in _itens_pis_cofins(doc) if i["saida"] is True)
    deb_c = sum(i["vl_c"] for i in _itens_pis_cofins(doc) if i["saida"] is True)
    for regs, valor, nome in ((("M100", "M200"), deb_p, "PIS"),
                              (("M500", "M600"), deb_c, "COFINS")):
        if valor > TOL and not any(doc.todos(x) for x in regs):
            yield Achado(0, "M", nome,
                         f"{valor:,.2f} de {nome} no detalhe e nenhum {'/'.join(regs)} no arquivo",
                         valor)


@check("R04", "M400/M800 nao bate com a receita nao tributada do detalhe",
       RISCO, "MEDIA", "M400/M800 consolidam receitas sem incidencia")
def r04(doc):
    _, nao_trib, por_cst = _receita_por_cst(doc)
    for reg, nome in (("M400", "PIS"), ("M800", "COFINS")):
        tot = sum(r.n("VL_TOT_REC") for r in doc.todos(reg))
        if tot > 0 and abs(tot - nao_trib) > _tol(nao_trib):
            yield Achado(doc.um(reg).linha, reg, nome,
                         f"{reg}={tot:,.2f} x detalhe nao tributado={nao_trib:,.2f}",
                         abs(tot - nao_trib))


@check("R05", "M410/M810 nao fecha com o M400/M800 pai",
       ESTRUTURA, "MEDIA", "M410 detalha o M400; a soma tem que fechar")
def r05(doc):
    for pai_reg, filho_reg in (("M400", "M410"), ("M800", "M810")):
        for pai in doc.todos(pai_reg):
            filhos = [f for f in doc.todos(filho_reg) if f.pai is pai]
            if not filhos:
                continue
            soma = sum(f.n("VL_REC") for f in filhos)
            if abs(soma - pai.n("VL_TOT_REC")) > 0.05:
                yield Achado(pai.linha, pai_reg, f"CST {pai.campos[1]}",
                             f"{pai_reg}={pai.n('VL_TOT_REC'):,.2f} x soma {filho_reg}={soma:,.2f}",
                             abs(soma - pai.n("VL_TOT_REC")))


@check("R06", "Credito escriturado no detalhe sem consolidacao na apuracao",
       OPORTUNIDADE, "ALTA", "C501/C505, D101/D105, F100 x M100/M105/M500/M505")
def r06(doc):
    cred_p = (sum(r.n("VL_PIS") for r in doc.todos("C501"))
              + sum(r.n("VL_PIS") for r in doc.todos("D101"))
              + sum(r.n("VL_PIS") for r in doc.todos("F100") if r["IND_OPER"] == "0"))
    cred_c = (sum(r.n("VL_COFINS") for r in doc.todos("C505"))
              + sum(r.n("VL_COFINS") for r in doc.todos("D105"))
              + sum(r.n("VL_COFINS") for r in doc.todos("F100") if r["IND_OPER"] == "0"))
    for regs, valor, nome in ((("M100", "M105"), cred_p, "PIS"),
                              (("M500", "M505"), cred_c, "COFINS")):
        if valor > TOL and not any(doc.todos(x) for x in regs):
            yield Achado(0, "M", nome,
                         f"{valor:,.2f} de credito de {nome} no detalhe sem {'/'.join(regs)}",
                         valor)


@check("R07", "0111: soma das receitas por natureza diverge do total declarado",
       ESTRUTURA, "MEDIA",
       "0111.REC_BRU_TOTAL deve ser a soma dos demais campos do proprio registro")
def r07(doc):
    r = doc.um("0111")
    if not r:
        return
    soma = (r.n("REC_BRU_NCUM_TRIB_MI") + r.n("REC_BRU_NCUM_NT_MI")
            + r.n("REC_BRU_NCUM_EXP") + r.n("REC_BRU_CUM"))
    total = r.n("REC_BRU_TOTAL")
    if abs(soma - total) > _tol(total):
        yield Achado(r.linha, "0111", "totais",
                     f"soma das partes {soma:,.2f} x REC_BRU_TOTAL declarado {total:,.2f}",
                     abs(soma - total))


@check("R08", "M200/M600: identidades de consolidacao do periodo nao fecham",
       RISCO, "MEDIA",
       "Guia Pratico v1.35, registros M200/M600: "
       "campo 05 (contrib. devida) = campo 02 - campo 03 - campo 04; "
       "campo 08 (contrib. a recolher NC) = campo 05 - campo 06 - campo 07; "
       "campo 13 (total a recolher) = campo 08 + campo 12.")
def r08(doc):
    for reg, nome in (("M200", "PIS"), ("M600", "COFINS")):
        r = doc.um(reg)
        if not r:
            continue

        dev = (r.n("VL_TOT_CONT_NC_PER") - r.n("VL_TOT_CRED_DESC")
               - r.n("VL_TOT_CRED_DESC_ANT"))
        decl_dev = r.n("VL_TOT_CONT_NC_DEV")
        if abs(dev - decl_dev) > _tol(abs(decl_dev)):
            yield Achado(r.linha, reg, f"{nome} nao-cumulativo (devido)",
                         f"campo05 calcula {dev:,.2f}, declarado {decl_dev:,.2f}",
                         abs(dev - decl_dev))

        rec_nc = decl_dev - r.n("VL_RET_NC") - r.n("VL_OUT_DED_NC")
        decl_rec_nc = r.n("VL_CONT_NC_REC")
        if abs(rec_nc - decl_rec_nc) > _tol(abs(decl_rec_nc)):
            yield Achado(r.linha, reg, f"{nome} nao-cumulativo (a recolher)",
                         f"campo08 calcula {rec_nc:,.2f}, declarado {decl_rec_nc:,.2f}",
                         abs(rec_nc - decl_rec_nc))

        total = decl_rec_nc + r.n("VL_CONT_CUM_REC")
        decl_total = r.n("VL_TOT_CONT_REC")
        if abs(total - decl_total) > _tol(abs(decl_total)):
            yield Achado(r.linha, reg, f"{nome} total do periodo",
                         f"campo13 calcula {total:,.2f}, declarado {decl_total:,.2f}",
                         abs(total - decl_total))


@check("R09", "M100/M500: identidades do credito do periodo nao fecham",
       RISCO, "MEDIA",
       "Guia Pratico, registros M100/M500: campo12 (credito disponivel) = "
       "campo08 (credito) + campo09 (ajuste acrescimo) - campo10 (ajuste "
       "reducao) - campo11 (credito diferido); campo15 (saldo credor) = "
       "campo12 - campo14 (credito descontado)")
def r09(doc):
    for reg, campo_dif, nome in (("M100", "VL_CRED_DIF", "PIS"),
                                  ("M500", "VL_CRED_DIFER", "COFINS")):
        for r in doc.todos(reg):
            disp = r.n("VL_CRED") + r.n("VL_AJUS_ACRES") - r.n("VL_AJUS_REDUC") - r.n(campo_dif)
            decl_disp = r.n("VL_CRED_DISP")
            if abs(disp - decl_disp) > _tol(abs(decl_disp)):
                yield Achado(r.linha, reg, f"{nome} {r['COD_CRED']}",
                             f"campo12 calcula {disp:,.2f}, declarado {decl_disp:,.2f}",
                             abs(disp - decl_disp))

            sld = decl_disp - r.n("VL_CRED_DESC")
            decl_sld = r.n("SLD_CRED")
            if abs(sld - decl_sld) > _tol(abs(decl_sld)):
                yield Achado(r.linha, reg, f"{nome} {r['COD_CRED']}",
                             f"campo15 calcula {sld:,.2f}, declarado {decl_sld:,.2f}",
                             abs(sld - decl_sld))


@check("R10", "M100/M500: base de calculo do credito nao bate com o detalhe M105/M505",
       ESTRUTURA, "MEDIA",
       "Guia Pratico: M100.VL_BC_PIS (M500.VL_BC_COFINS) deve ser o somatorio "
       "do campo VL_BC_PIS (VL_BC_COFINS) de todos os M105 (M505) filhos")
def r10(doc):
    for pai_reg, filho_reg, campo, nome in (("M100", "M105", "VL_BC_PIS", "PIS"),
                                             ("M500", "M505", "VL_BC_COFINS", "COFINS")):
        for pai in doc.todos(pai_reg):
            filhos = [f for f in doc.todos(filho_reg) if f.pai is pai]
            if not filhos:
                continue
            soma = sum(f.n(campo) for f in filhos)
            decl = pai.n(campo)
            if abs(soma - decl) > _tol(abs(decl)):
                yield Achado(pai.linha, pai_reg, f"{nome} {pai['COD_CRED']}",
                             f"{pai_reg}.{campo}={decl:,.2f} x soma {filho_reg}={soma:,.2f}",
                             abs(soma - decl))


@check("R11", "1100/1500: identidades do controle de creditos fiscais nao fecham",
       ESTRUTURA, "MEDIA",
       "Guia Pratico, registros 1100/1500: campo08 = campo06 + campo07; "
       "campo12 = campo08 - campo09 - campo10 - campo11; "
       "campo18 = campo12 - campo13 - campo14 - campo15 - campo16 - campo17")
def r11(doc):
    for reg, nome in (("1100", "PIS"), ("1500", "COFINS")):
        for r in doc.todos(reg):
            tot = r.n("VL_CRED_APU") + r.n("VL_CRED_EXT_APU")
            decl_tot = r.n("VL_TOT_CRED_APU")
            if abs(tot - decl_tot) > _tol(abs(decl_tot)):
                yield Achado(r.linha, reg, f"{nome} {r['PER_APU_CRED']}",
                             f"campo08 calcula {tot:,.2f}, declarado {decl_tot:,.2f}",
                             abs(tot - decl_tot))

            disp = (decl_tot - r.n("VL_CRED_DESC_PA_ANT") - r.n("VL_CRED_PER_PA_ANT")
                    - r.n("VL_CRED_DCOMP_PA_ANT"))
            decl_disp = r.n("SD_CRED_DISP_EFD")
            if abs(disp - decl_disp) > _tol(abs(decl_disp)):
                yield Achado(r.linha, reg, f"{nome} {r['PER_APU_CRED']}",
                             f"campo12 calcula {disp:,.2f}, declarado {decl_disp:,.2f}",
                             abs(disp - decl_disp))

            fim = (decl_disp - r.n("VL_CRED_DESC_EFD") - r.n("VL_CRED_PER_EFD")
                   - r.n("VL_CRED_DCOMP_EFD") - r.n("VL_CRED_TRANS") - r.n("VL_CRED_OUT"))
            decl_fim = r.n("SLD_CRED_FIM")
            if abs(fim - decl_fim) > _tol(abs(decl_fim)):
                yield Achado(r.linha, reg, f"{nome} {r['PER_APU_CRED']}",
                             f"campo18 calcula {fim:,.2f}, declarado {decl_fim:,.2f}",
                             abs(fim - decl_fim))


@check("R12", "Credito descontado de periodo anterior (1100/1500) nao bate com o M200/M600",
       RISCO, "MEDIA",
       "Guia Pratico, registro 1100 (Campo 13)/1500 (Campo 13): a soma dos "
       "valores lancados deve corresponder ao campo VL_TOT_CRED_DESC_ANT do "
       "registro M200/M600")
def r12(doc):
    for reg_1, reg_m, nome in (("1100", "M200", "PIS"), ("1500", "M600", "COFINS")):
        registros = doc.todos(reg_1)
        m = doc.um(reg_m)
        if not registros or not m:
            continue
        soma = sum(r.n("VL_CRED_DESC_EFD") for r in registros)
        decl = m.n("VL_TOT_CRED_DESC_ANT")
        if abs(soma - decl) > _tol(abs(decl)):
            yield Achado(m.linha, reg_m, nome,
                         f"soma {reg_1}.VL_CRED_DESC_EFD={soma:,.2f} x "
                         f"{reg_m}.VL_TOT_CRED_DESC_ANT={decl:,.2f}",
                         abs(soma - decl))


@check("R13", "C180: total do item nao bate com o detalhamento C181/C185",
       ESTRUTURA, "MEDIA",
       "Guia Pratico: C180.VL_TOT_ITEM deve ser o somatorio de VL_ITEM dos "
       "C181 (PIS) e, separadamente, dos C185 (COFINS) filhos do mesmo item")
def r13(doc):
    for filho_reg, nome in (("C181", "PIS"), ("C185", "COFINS")):
        for pai in doc.todos("C180"):
            filhos = [f for f in doc.todos(filho_reg) if f.pai is pai]
            if not filhos:
                continue
            soma = sum(f.n("VL_ITEM") for f in filhos)
            decl = pai.n("VL_TOT_ITEM")
            if abs(soma - decl) > _tol(abs(decl)):
                yield Achado(pai.linha, "C180", f"item {pai['COD_ITEM']} ({nome})",
                             f"VL_TOT_ITEM={decl:,.2f} x soma {filho_reg}.VL_ITEM={soma:,.2f}",
                             abs(soma - decl))


@check("R14", "C190: total do item nao bate com o detalhamento C191/C195",
       ESTRUTURA, "MEDIA",
       "Guia Pratico: C190.VL_TOT_ITEM (aquisicoes/devolucoes consolidadas) "
       "deve ser o somatorio de VL_ITEM dos C191 (PIS) e, separadamente, "
       "dos C195 (COFINS) filhos do mesmo item")
def r14(doc):
    for filho_reg, nome in (("C191", "PIS"), ("C195", "COFINS")):
        for pai in doc.todos("C190"):
            filhos = [f for f in doc.todos(filho_reg) if f.pai is pai]
            if not filhos:
                continue
            soma = sum(f.n("VL_ITEM") for f in filhos)
            decl = pai.n("VL_TOT_ITEM")
            if abs(soma - decl) > _tol(abs(decl)):
                yield Achado(pai.linha, "C190", f"item {pai['COD_ITEM']} ({nome})",
                             f"VL_TOT_ITEM={decl:,.2f} x soma {filho_reg}.VL_ITEM={soma:,.2f}",
                             abs(soma - decl))


@check("R15", "M210/M610: identidades da decomposicao por COD_CONT nao fecham",
       ESTRUTURA, "MEDIA",
       "Guia Pratico, leiaute vigente (2019+) dos registros M210/M610: "
       "campo07 (base apos ajustes) = campo04 + campo05 - campo06; "
       "campo16 (total do periodo) = campo11 + campo12 - campo13 - campo14 + campo15")
def r15(doc):
    for reg, nome in (("M210", "PIS"), ("M610", "COFINS")):
        for r in doc.todos(reg):
            bc_ajus = r.n("VL_BC_CONT") + r.n("VL_AJUS_ACRES_BC_" + nome) - r.n("VL_AJUS_REDUC_BC_" + nome)
            decl_bc_ajus = r.n("VL_BC_CONT_AJUS")
            if abs(bc_ajus - decl_bc_ajus) > _tol(abs(decl_bc_ajus)):
                yield Achado(r.linha, reg, f"{nome} {r['COD_CONT']}",
                             f"campo07 calcula {bc_ajus:,.2f}, declarado {decl_bc_ajus:,.2f}",
                             abs(bc_ajus - decl_bc_ajus))

            total = (r.n("VL_CONT_APUR") + r.n("VL_AJUS_ACRES") - r.n("VL_AJUS_REDUC")
                     - r.n("VL_CONT_DIFER") + r.n("VL_CONT_DIFER_ANT"))
            decl_total = r.n("VL_CONT_PER")
            if abs(total - decl_total) > _tol(abs(decl_total)):
                yield Achado(r.linha, reg, f"{nome} {r['COD_CONT']}",
                             f"campo16 calcula {total:,.2f}, declarado {decl_total:,.2f}",
                             abs(total - decl_total))


@check("R16", "M200/M600: total declarado nao bate com a soma do M210/M610 por COD_CONT",
       RISCO, "MEDIA",
       "Guia Pratico: M200.VL_TOT_CONT_NC_PER (M600 idem) e a soma de "
       "VL_CONT_PER dos M210/M610 filhos com COD_CONT nao-cumulativo "
       "(01,02,03,04,32,71); VL_TOT_CONT_CUM_PER e a soma com COD_CONT "
       "cumulativo (31,32,51,52,53,54,72)")
def r16(doc):
    for reg_m, reg_filho, nome in (("M200", "M210", "PIS"), ("M600", "M610", "COFINS")):
        m = doc.um(reg_m)
        filhos = doc.todos(reg_filho)
        if not m or not filhos:
            continue
        for grupo, campo_m, rotulo in ((COD_CONT_NAO_CUMULATIVO, "VL_TOT_CONT_NC_PER", "nao-cumulativo"),
                                        (COD_CONT_CUMULATIVO, "VL_TOT_CONT_CUM_PER", "cumulativo")):
            soma = sum(f.n("VL_CONT_PER") for f in filhos if f["COD_CONT"] in grupo)
            decl = m.n(campo_m)
            if abs(soma - decl) > _tol(abs(decl)):
                yield Achado(m.linha, reg_m, f"{nome} {rotulo}",
                             f"{reg_m}.{campo_m}={decl:,.2f} x soma {reg_filho}.VL_CONT_PER={soma:,.2f}",
                             abs(soma - decl))


def _soma_ajustes_por_pai(doc, pai, filho_reg):
    """Soma VL_AJ dos filhos de ajuste (M110/M220/M510/M620), separado por
    IND_AJ (0=reducao, 1=acrescimo). Devolve (acrescimo, reducao)."""
    filhos = [f for f in doc.todos(filho_reg) if f.pai is pai]
    acres = sum(f.n("VL_AJ") for f in filhos if f["IND_AJ"] == "1")
    reduc = sum(f.n("VL_AJ") for f in filhos if f["IND_AJ"] == "0")
    return acres, reduc


@check("R17", "M100/M500: ajuste de credito declarado nao bate com o detalhamento M110/M510",
       ESTRUTURA, "MEDIA",
       "Guia Pratico, registro M110/M510: a soma de VL_AJ com IND_AJ=1 deve "
       "corresponder a M100/M500.VL_AJUS_ACRES (campo09), e a soma com "
       "IND_AJ=0 a VL_AJUS_REDUC (campo10)")
def r17(doc):
    for pai_reg, filho_reg, nome in (("M100", "M110", "PIS"), ("M500", "M510", "COFINS")):
        for pai in doc.todos(pai_reg):
            filhos = [f for f in doc.todos(filho_reg) if f.pai is pai]
            if not filhos:
                continue
            acres, reduc = _soma_ajustes_por_pai(doc, pai, filho_reg)
            decl_acres, decl_reduc = pai.n("VL_AJUS_ACRES"), pai.n("VL_AJUS_REDUC")
            if abs(acres - decl_acres) > _tol(abs(decl_acres)):
                yield Achado(pai.linha, pai_reg, f"{nome} {pai['COD_CRED']} (acrescimo)",
                             f"VL_AJUS_ACRES={decl_acres:,.2f} x soma {filho_reg}={acres:,.2f}",
                             abs(acres - decl_acres))
            if abs(reduc - decl_reduc) > _tol(abs(decl_reduc)):
                yield Achado(pai.linha, pai_reg, f"{nome} {pai['COD_CRED']} (reducao)",
                             f"VL_AJUS_REDUC={decl_reduc:,.2f} x soma {filho_reg}={reduc:,.2f}",
                             abs(reduc - decl_reduc))


@check("R18", "M210/M610: ajuste de base de calculo declarado nao bate com o detalhamento M215/M615",
       ESTRUTURA, "MEDIA",
       "Guia Pratico, registro M215/M615 (leiaute 2019+ do M210/M610): a "
       "soma de VL_AJ_BC com IND_AJ_BC=1 deve corresponder ao campo "
       "VL_AJUS_ACRES_BC_PIS/COFINS do pai, e a soma com IND_AJ_BC=0 ao "
       "VL_AJUS_REDUC_BC_PIS/COFINS")
def r18(doc):
    for pai_reg, filho_reg, campo_sufixo, nome in (("M210", "M215", "PIS", "PIS"),
                                                     ("M610", "M615", "COFINS", "COFINS")):
        for pai in doc.todos(pai_reg):
            filhos = [f for f in doc.todos(filho_reg) if f.pai is pai]
            if not filhos:
                continue
            acres = sum(f.n("VL_AJ_BC") for f in filhos if f["IND_AJ_BC"] == "1")
            reduc = sum(f.n("VL_AJ_BC") for f in filhos if f["IND_AJ_BC"] == "0")
            campo_acres, campo_reduc = "VL_AJUS_ACRES_BC_" + campo_sufixo, "VL_AJUS_REDUC_BC_" + campo_sufixo
            decl_acres, decl_reduc = pai.n(campo_acres), pai.n(campo_reduc)
            if abs(acres - decl_acres) > _tol(abs(decl_acres)):
                yield Achado(pai.linha, pai_reg, f"{nome} {pai['COD_CONT']} (acrescimo BC)",
                             f"{campo_acres}={decl_acres:,.2f} x soma {filho_reg}={acres:,.2f}",
                             abs(acres - decl_acres))
            if abs(reduc - decl_reduc) > _tol(abs(decl_reduc)):
                yield Achado(pai.linha, pai_reg, f"{nome} {pai['COD_CONT']} (reducao BC)",
                             f"{campo_reduc}={decl_reduc:,.2f} x soma {filho_reg}={reduc:,.2f}",
                             abs(reduc - decl_reduc))


@check("R19", "M210/M610: ajuste da contribuicao declarado nao bate com o detalhamento M220/M620",
       ESTRUTURA, "MEDIA",
       "Guia Pratico, registro M220/M620: a soma de VL_AJ com IND_AJ=1 deve "
       "corresponder a M210/M610.VL_AJUS_ACRES (campo12), e a soma com "
       "IND_AJ=0 a VL_AJUS_REDUC (campo13)")
def r19(doc):
    for pai_reg, filho_reg, nome in (("M210", "M220", "PIS"), ("M610", "M620", "COFINS")):
        for pai in doc.todos(pai_reg):
            filhos = [f for f in doc.todos(filho_reg) if f.pai is pai]
            if not filhos:
                continue
            acres, reduc = _soma_ajustes_por_pai(doc, pai, filho_reg)
            decl_acres, decl_reduc = pai.n("VL_AJUS_ACRES"), pai.n("VL_AJUS_REDUC")
            if abs(acres - decl_acres) > _tol(abs(decl_acres)):
                yield Achado(pai.linha, pai_reg, f"{nome} {pai['COD_CONT']} (acrescimo)",
                             f"VL_AJUS_ACRES={decl_acres:,.2f} x soma {filho_reg}={acres:,.2f}",
                             abs(acres - decl_acres))
            if abs(reduc - decl_reduc) > _tol(abs(decl_reduc)):
                yield Achado(pai.linha, pai_reg, f"{nome} {pai['COD_CONT']} (reducao)",
                             f"VL_AJUS_REDUC={decl_reduc:,.2f} x soma {filho_reg}={reduc:,.2f}",
                             abs(reduc - decl_reduc))


@check("R20", "F525 (regime de caixa, lucro presumido): total detalhado nao bate com F500/F510",
       ESTRUTURA, "MEDIA",
       "Guia Pratico, registro F525: \"O total das receitas relacionadas "
       "nos registros F525 deve corresponder ao total das receitas "
       "recebidas, relacionadas nos registros F500\" -- F510 somado junto "
       "por ser a mesma consolidacao de regime de caixa, so que com "
       "aliquota por unidade de medida de produto (mesmo VL_REC_CAIXA)")
def r20(doc):
    soma_f525 = sum(r.n("VL_REC") for r in doc.todos("F525"))
    soma_caixa = (sum(r.n("VL_REC_CAIXA") for r in doc.todos("F500"))
                  + sum(r.n("VL_REC_CAIXA") for r in doc.todos("F510")))
    if abs(soma_f525 - soma_caixa) > _tol(soma_caixa):
        yield Achado(0, "F525", "regime de caixa (lucro presumido)",
                     f"soma F525.VL_REC={soma_f525:,.2f} x soma F500/F510.VL_REC_CAIXA={soma_caixa:,.2f}",
                     abs(soma_f525 - soma_caixa))
