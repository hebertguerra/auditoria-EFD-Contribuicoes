"""Coerencia interna PIS/COFINS: CST x aliquota x valor x CFOP."""
from collections import defaultdict
from . import check, Achado, RISCO, OPORTUNIDADE
from ..layouts import CST_SEM_DEBITO, ALIQ_BASICA, ALIQ_CUMULATIVO

TOL = 0.02  # tolerancia de centavos


def _itens_pis_cofins(doc):
    """Normaliza C170 / A170 / F100 num formato unico.

    cod_sit carrega a situacao do documento pai (C100/A100) quando existe
    -- usado pelo C06 para nao comparar documento complementar (COD_SIT=06)
    contra documento regular do mesmo item (ver COD_SIT_COMPLEMENTAR)."""
    for r in doc.todos("C170"):
        c100 = r.pai
        yield dict(r=r, reg="C170", ref=f"NF {c100['NUM_DOC']}" if c100 else "",
                   item=r["COD_ITEM"], cfop=r["CFOP"],
                   saida=(c100["IND_OPER"] == "1") if c100 else None,
                   cod_sit=c100["COD_SIT"] if c100 else "",
                   vl_item=r.n("VL_ITEM"),
                   cst_p=r["CST_PIS"], bc_p=r.n("VL_BC_PIS"), al_p=r.n("ALIQ_PIS"), vl_p=r.n("VL_PIS"),
                   cst_c=r["CST_COFINS"], bc_c=r.n("VL_BC_COFINS"), al_c=r.n("ALIQ_COFINS"), vl_c=r.n("VL_COFINS"))
    for r in doc.todos("A170"):
        a100 = r.pai
        yield dict(r=r, reg="A170", ref=f"NFS {a100['NUM_DOC']}" if a100 else "",
                   item=r["COD_ITEM"], cfop="",
                   saida=(a100["IND_OPER"] == "1") if a100 else None,
                   cod_sit=a100["COD_SIT"] if a100 else "",
                   vl_item=r.n("VL_ITEM"),
                   cst_p=r["CST_PIS"], bc_p=r.n("VL_BC_PIS"), al_p=r.n("ALIQ_PIS"), vl_p=r.n("VL_PIS"),
                   cst_c=r["CST_COFINS"], bc_c=r.n("VL_BC_COFINS"), al_c=r.n("ALIQ_COFINS"), vl_c=r.n("VL_COFINS"))
    for r in doc.todos("F100"):
        yield dict(r=r, reg="F100", ref=f"part {r['COD_PART']}",
                   item=r["COD_ITEM"], cfop="",
                   saida=(r["IND_OPER"] == "1"),
                   cod_sit="",  # F100 nao tem conceito de documento complementar
                   vl_item=r.n("VL_OPER"),
                   cst_p=r["CST_PIS"], bc_p=r.n("VL_BC_PIS"), al_p=r.n("ALIQ_PIS"), vl_p=r.n("VL_PIS"),
                   cst_c=r["CST_COFINS"], bc_c=r.n("VL_BC_COFINS"), al_c=r.n("ALIQ_COFINS"), vl_c=r.n("VL_COFINS"))


@check("C01", "CST divergente entre PIS e COFINS no mesmo item",
       RISCO, "ALTA", "PIS e COFINS seguem a mesma tabela de CST (Tabela 4.3.3/4.3.4)")
def c01(doc):
    for i in _itens_pis_cofins(doc):
        if i["cst_p"] and i["cst_c"] and i["cst_p"] != i["cst_c"]:
            yield Achado(i["r"].linha, i["reg"], f"{i['ref']} / item {i['item']}",
                         f"CST_PIS={i['cst_p']} vs CST_COFINS={i['cst_c']}",
                         i["vl_p"] + i["vl_c"])


@check("C02", "CST sem incidencia com contribuicao apurada",
       RISCO, "ALTA", "CST 04/05/06/07/08/09 nao admitem valor apurado")
def c02(doc):
    for i in _itens_pis_cofins(doc):
        if i["cst_p"] in CST_SEM_DEBITO and i["vl_p"] > TOL:
            yield Achado(i["r"].linha, i["reg"], f"{i['ref']} / item {i['item']}",
                         f"CST_PIS={i['cst_p']} com VL_PIS={i['vl_p']:.2f}", i["vl_p"])
        if i["cst_c"] in CST_SEM_DEBITO and i["vl_c"] > TOL:
            yield Achado(i["r"].linha, i["reg"], f"{i['ref']} / item {i['item']}",
                         f"CST_COFINS={i['cst_c']} com VL_COFINS={i['vl_c']:.2f}", i["vl_c"])


@check("C03", "CST tributado sem contribuicao apurada",
       OPORTUNIDADE, "MEDIA", "CST 01/02 exigem base e valor")
def c03(doc):
    for i in _itens_pis_cofins(doc):
        if i["cst_p"] in ("01", "02") and i["vl_p"] <= TOL and i["vl_item"] > 0:
            yield Achado(i["r"].linha, i["reg"], f"{i['ref']} / item {i['item']}",
                         f"CST_PIS={i['cst_p']} com VL_PIS=0 sobre item {i['vl_item']:.2f}")


@check("C04", "VL != base x aliquota (erro aritmetico)",
       RISCO, "ALTA", "Conferencia aritmetica do proprio registro")
def c04(doc):
    for i in _itens_pis_cofins(doc):
        for t, bc, al, vl in (("PIS", i["bc_p"], i["al_p"], i["vl_p"]),
                              ("COFINS", i["bc_c"], i["al_c"], i["vl_c"])):
            if bc > 0 and al > 0:
                esp = round(bc * al / 100, 2)
                if abs(esp - vl) > max(TOL, esp * 0.001):
                    yield Achado(i["r"].linha, i["reg"], f"{i['ref']} / item {i['item']}",
                                 f"{t}: {bc:.2f} x {al}% = {esp:.2f}, escriturado {vl:.2f}",
                                 abs(esp - vl))


def _aliquotas_aceitas(doc):
    """Aliquotas basicas validas para CST 01 no regime da escrituracao.

    COD_INC_TRIB=3 ("ambos") permite as duas aliquotas basicas convivendo
    no mesmo periodo (ex.: receita financeira cumulativa e receita
    operacional nao-cumulativa) -- reduzir isso a um unico regime gerava
    falso positivo de "aliquota fora do padrao" para contribuinte de
    regime misto."""
    if doc.regime_misto:
        return {"PIS": {ALIQ_BASICA["PIS"], ALIQ_CUMULATIVO["PIS"]},
                "COFINS": {ALIQ_BASICA["COFINS"], ALIQ_CUMULATIVO["COFINS"]}}
    padrao = ALIQ_CUMULATIVO if doc.regime_cumulativo else ALIQ_BASICA
    return {"PIS": {padrao["PIS"]}, "COFINS": {padrao["COFINS"]}}


@check("C05", "Aliquota fora do padrao do regime",
       RISCO, "MEDIA", "Aliquotas basicas: 1,65/7,6 (nao-cumulativo) e 0,65/3,0 (cumulativo)")
def c05(doc):
    aceitas = _aliquotas_aceitas(doc)
    for i in _itens_pis_cofins(doc):
        for t, cst, al in (("PIS", i["cst_p"], i["al_p"]),
                           ("COFINS", i["cst_c"], i["al_c"])):
            if cst == "01" and al > 0 and not any(abs(al - a) <= 0.001 for a in aceitas[t]):
                esperado = "/".join(f"{a}%" for a in sorted(aceitas[t]))
                yield Achado(i["r"].linha, i["reg"], f"{i['ref']} / item {i['item']}",
                             f"{t} CST 01 com aliquota {al}% (esperado {esperado})")


# Tabela SPED "Situacao do Documento" (COD_SIT do C100/A100) -- 06 =
# Documento Fiscal Complementar. Um complementar retifica/completa valor
# de uma NF-e anterior e pode legitimamente carregar CST diferente do
# documento original (ex.: suspensao da contribuicao vs sem incidencia)
# sem que isso seja erro de parametrizacao do item -- sao naturezas de
# documento distintas. Descoberto numa investigacao real (auditoria de
# arquivo de producao): 2 de 88 saidas do mesmo item tinham CST 09
# (suspensao) contra CST 08 (sem incidencia) nas outras 86; as 2 eram
# COD_SIT=06, as 86 eram COD_SIT=00 (documento regular) -- falso positivo
# antes desta correcao, porque o check comparava as duas categorias juntas.
COD_SIT_COMPLEMENTAR = "06"


@check("C06", "Mesmo item com CST diferente na competencia (documento regular)",
       RISCO, "ALTA",
       "Cadastro/parametrizacao inconsistente do produto -- documento "
       "complementar (COD_SIT=06) e comparado separadamente do documento "
       "regular, pois pode legitimamente ter CST diferente")
def c06(doc):
    mapa = defaultdict(lambda: defaultdict(list))
    for i in _itens_pis_cofins(doc):
        if not i["item"] or i["saida"] is None:
            continue
        categoria = "complementar" if i["cod_sit"] == COD_SIT_COMPLEMENTAR else "regular"
        chave = (i["item"], "saida" if i["saida"] else "entrada", categoria)
        mapa[chave][i["cst_p"]].append(i)
    for (item, sentido, categoria), csts in mapa.items():
        if len(csts) > 1:
            amostra = next(iter(next(iter(csts.values()))))
            rotulo = " -- documentos complementares" if categoria == "complementar" else ""
            yield Achado(amostra["r"].linha, amostra["reg"], f"item {item} ({sentido}){rotulo}",
                         "CST_PIS varia: " + ", ".join(
                             f"{c}({len(v)}x)" for c, v in sorted(csts.items())))


@check("C07", "CFOP incompativel com o sentido da operacao",
       RISCO, "ALTA", "CFOP 1/2/3 = entrada; 5/6/7 = saida")
def c07(doc):
    for r in doc.todos("C170"):
        c100 = r.pai
        if not c100 or not r["CFOP"]:
            continue
        saida = c100["IND_OPER"] == "1"
        g = r["CFOP"][0]
        if saida and g in "123":
            yield Achado(r.linha, "C170", f"NF {c100['NUM_DOC']}",
                         f"saida com CFOP de entrada: {r['CFOP']}")
        if not saida and g in "567":
            yield Achado(r.linha, "C170", f"NF {c100['NUM_DOC']}",
                         f"entrada com CFOP de saida: {r['CFOP']}")


@check("C08", "Soma dos itens diverge do total do documento",
       RISCO, "MEDIA", "C100.VL_PIS/VL_COFINS x soma dos C170")
def c08(doc):
    for c100 in doc.todos("C100"):
        itens = [r for r in doc.todos("C170") if r.pai is c100]
        if not itens:
            continue
        for campo, chave in (("VL_PIS", "VL_PIS"), ("VL_COFINS", "VL_COFINS")):
            cab = c100.n(campo)
            soma = sum(r.n(chave) for r in itens)
            if abs(cab - soma) > 0.05:
                yield Achado(c100.linha, "C100", f"NF {c100['NUM_DOC']}",
                             f"{campo}: cabecalho {cab:.2f} x itens {soma:.2f}",
                             abs(cab - soma))
