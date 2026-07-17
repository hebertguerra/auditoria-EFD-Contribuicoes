"""Checks de tese fiscal: monofasico, insumo, imobilizado, amparo judicial.

IMPORTANTE -- por que estes checks sinalizam, nao decidem:
Diferente dos demais grupos (campo obrigatorio, aritmetica, reconciliacao
entre registros), a correcao de uma tese fiscal nao e uma questao de
formato -- depende de fatos do caso concreto e de interpretacao juridica
(essencialidade do insumo, classificacao correta do produto por NCM,
existencia de decisao judicial). O Guia Pratico confirma que as tabelas
de produto por NCM (4.3.9 a 4.3.16 -- aliquotas de credito presumido da
agroindustria, produtos monofasicos/ST/aliquota zero) sao tabelas
EXTERNAS, publicadas separadamente no Portal do SPED, fora do proprio
Guia -- nao ha como conferir aqui, com confianca de estar atualizado, se
um NCM especifico esta corretamente classificado.

Por isso todo achado deste modulo usa severidade BAIXA/MEDIA e a caixa
OPORTUNIDADE, e o texto do achado e sempre uma pergunta para o auditor
responder ("precisa de documentacao/analise"), nunca uma afirmacao de
erro. Nenhum destes checks reprova ou aprova nada sozinho.
"""
from collections import defaultdict
from . import check, Achado, OPORTUNIDADE
from .coerencia import _itens_pis_cofins, _aliquotas_aceitas
from ..layouts import CST_CREDITO

# CST_PIS/CST_COFINS de saida que dependem de classificacao de produto por
# NCM em tabela externa ao Guia Pratico (monofasico, substituicao
# tributaria) -- Tabelas 4.3.10 a 4.3.12.
CST_DEPENDE_TABELA_EXTERNA = {"04", "05"}

# NAT_BC_CRED (Tabela 4.3.7) que representam credito de insumo.
NAT_BC_CRED_INSUMO = {"02", "03"}
# NAT_BC_CRED que representam credito de ativo imobilizado.
NAT_BC_CRED_IMOBILIZADO = {"09", "10"}

TOL_RELEVANCIA = 5000.00  # limiar de materialidade para nao poluir o laudo

# Tabela 4.3.8 (Codigo do Ajuste) -- so estes 2 codigos, introduzidos pela
# Nota Tecnica EFD-Contribuicoes no 012/2026 para a Lei Complementar no
# 224/2025 (reducao linear de incentivos e beneficios tributarios, vigente
# a partir de 01/04/2026). NAO e a tabela 4.3.8 completa -- so o que a NT
# 012/2026 documenta; por isso T05 apenas reconhece/sinaliza estes 2
# codigos quando aparecem, nao valida COD_AJ contra a tabela inteira (que
# o audita nao tem).
COD_AJ_REDUCAO_LINEAR = {
    "11": "reducao linear -- aliquota zero/isencao (LC 224/2025, art. 4o, "
          "par. 4o, I; formula do art. 7o da IN RFB 2.305/2025)",
    "12": "reducao linear -- limite de 90% no aproveitamento de credito "
          "presumido (LC 224/2025, art. 4o, par. 2o, II, d; art. 10 da "
          "IN RFB 2.305/2025)",
}


def _chave_item(r):
    """Melhor identificador disponivel para o item/participante do registro
    (C501/D101/C505/D105 nao tem COD_ITEM/COD_PART proprio -- usa o pai)."""
    if r["COD_ITEM"]:
        return r["COD_ITEM"]
    if r["COD_PART"]:
        return r["COD_PART"]
    if r.pai is not None and r.pai["COD_PART"]:
        return r.pai["COD_PART"]
    return f"L{r.linha}"


def _itens_credito(doc):
    """Registros com NAT_BC_CRED preenchido e CST de credito (por documento).

    So os registros que de fato tem o campo NAT_BC_CRED no leiaute (Tabela
    4.3.7) entram aqui: C501/D101 (so PIS), C505/D105 (so COFINS) e A170/F100
    (PIS e COFINS na mesma linha). C170 nao tem NAT_BC_CRED -- tem COD_NAT,
    que e outro campo (natureza da receita/rubrica, ref. 0400).
    """
    for reg in ("C501", "D101"):
        for r in doc.todos(reg):
            if r["CST_PIS"] in CST_CREDITO and r["NAT_BC_CRED"]:
                yield r, r["NAT_BC_CRED"], r.n("VL_PIS")
    for reg in ("C505", "D105"):
        for r in doc.todos(reg):
            if r["CST_COFINS"] in CST_CREDITO and r["NAT_BC_CRED"]:
                yield r, r["NAT_BC_CRED"], r.n("VL_COFINS")
    for reg in ("A170", "F100"):
        for r in doc.todos(reg):
            if r["CST_PIS"] in CST_CREDITO and r["NAT_BC_CRED"]:
                yield r, r["NAT_BC_CRED"], r.n("VL_PIS")
            if r["CST_COFINS"] in CST_CREDITO and r["NAT_BC_CRED"]:
                yield r, r["NAT_BC_CRED"], r.n("VL_COFINS")


@check("T01", "CST de monofasico/substituicao tributaria depende de tabela externa de NCM",
       OPORTUNIDADE, "BAIXA",
       "Guia Pratico, Tabelas 4.3.10-4.3.12: sao tabelas externas (nao "
       "publicadas no Guia); a classificacao correta do produto por NCM "
       "precisa ser conferida contra a tabela vigente no Portal do SPED")
def t01(doc):
    contagem = defaultdict(lambda: [0, 0.0])
    for r in doc.todos("C170"):
        for campo, tipo in (("CST_PIS", "PIS"), ("CST_COFINS", "COFINS")):
            if r[campo] in CST_DEPENDE_TABELA_EXTERNA:
                item = r["COD_ITEM"]
                contagem[(item, tipo, r[campo])][0] += 1
                contagem[(item, tipo, r[campo])][1] += r.n("VL_ITEM")
    for (item, tipo, cst), (n, valor) in contagem.items():
        yield Achado(0, "C170", f"item {item} ({tipo})",
                     f"CST {cst} usado {n}x (R$ {valor:,.2f}) -- confirmar classificacao "
                     "do NCM contra a tabela de produtos monofasicos/ST vigente",
                     valor)


@check("T02", "Credito de insumo com valor relevante -- confirmar essencialidade/relevancia",
       OPORTUNIDADE, "MEDIA",
       "Lei 10.637/2002 art. 3o, II e Lei 10.833/2003 art. 3o, II c/c REsp "
       "1.221.170/PR (STJ, tema repetitivo 779): credito de insumo exige "
       "teste de essencialidade ou relevancia para a atividade, nao apenas "
       "aquisicao de bem/servico aplicado no processo")
def t02(doc):
    por_item = defaultdict(float)
    for r, nat, valor in _itens_credito(doc):
        if nat in NAT_BC_CRED_INSUMO:
            por_item[_chave_item(r)] += valor
    for item, valor in por_item.items():
        if valor > TOL_RELEVANCIA:
            yield Achado(0, "credito", item,
                         f"R$ {valor:,.2f} em credito de insumo (NAT_BC_CRED 02/03) -- "
                         "confirmar essencialidade/relevancia (tese STJ) e documentar",
                         valor)


@check("T03", "Credito de ativo imobilizado -- confirmar regra de apropriacao",
       OPORTUNIDADE, "MEDIA",
       "Lei 10.637/2002 art. 3o, VI e paragrafo 14, Lei 10.833/2003 art. 3o, VI e paragrafo 14, "
       "IN RFB 1.911/2019 art. 205-206: credito sobre ativo imobilizado segue "
       "regra propria (encargos de depreciacao/amortizacao, ou opcionalmente "
       "o valor de aquisicao em parcela unica nos casos previstos em lei)")
def t03(doc):
    por_item = defaultdict(float)
    for r, nat, valor in _itens_credito(doc):
        if nat in NAT_BC_CRED_IMOBILIZADO:
            por_item[_chave_item(r)] += valor
    for item, valor in por_item.items():
        if valor > TOL_RELEVANCIA:
            yield Achado(0, "credito", item,
                         f"R$ {valor:,.2f} em credito de ativo imobilizado (NAT_BC_CRED "
                         "09/10) -- confirmar se a apropriacao segue a regra legal "
                         "aplicavel ao bem (depreciacao x valor de aquisicao)",
                         valor)


@check("T04", "Aliquota fora do padrao sem processo judicial (1010) registrado no arquivo",
       OPORTUNIDADE, "MEDIA",
       "Guia Pratico, registro 1010: tratamento tributario diverso do "
       "previsto em lei, com lastro em decisao judicial, deve estar "
       "documentado no registro 1010 da propria escrituracao")
def t04(doc):
    if doc.todos("1010"):
        return
    aceitas = _aliquotas_aceitas(doc)
    vistos = set()
    for i in _itens_pis_cofins(doc):
        for t, cst, al in (("PIS", i["cst_p"], i["al_p"]), ("COFINS", i["cst_c"], i["al_c"])):
            if (cst == "01" and al > 0 and (t, al) not in vistos
                    and not any(abs(al - a) <= 0.001 for a in aceitas[t])):
                vistos.add((t, al))
                esperado = "/".join(f"{a}%" for a in sorted(aceitas[t]))
                yield Achado(i["r"].linha, i["reg"], t,
                             f"{t} CST 01 com aliquota {al}% fora do padrao "
                             f"({esperado}) e nenhum registro 1010 (processo judicial) "
                             "no arquivo -- confirmar amparo legal da divergencia")


@check("T05", "Ajuste de reducao linear de incentivos/beneficios (LC 224/2025) identificado",
       OPORTUNIDADE, "BAIXA",
       "Lei Complementar no 224/2025, IN RFB no 2.305/2025 (Anexo Unico "
       "atualizado pela IN RFB no 2.307/2026 -- lista de incentivos "
       "preservados da reducao, nao afeta o mecanismo de escrituracao) e "
       "Nota Tecnica EFD-Contribuicoes no 012/2026 -- vigente a partir de "
       "01/04/2026. O CST original da operacao (ex.: 06/07) nao muda; o "
       "ajuste e feito via M110/M220 (PIS) e M510/M620 (COFINS), que o "
       "audita ja reconcilia (R17/R19) -- este check so identifica quando "
       "o mecanismo esta em uso, nao valida o calculo")
def t05(doc):
    for reg, nome in (("M220", "PIS"), ("M620", "COFINS"),
                       ("M110", "PIS"), ("M510", "COFINS")):
        for r in doc.todos(reg):
            cod_aj = r["COD_AJ"].strip()
            explicacao = COD_AJ_REDUCAO_LINEAR.get(cod_aj)
            if explicacao:
                yield Achado(r.linha, reg, nome,
                             f"COD_AJ={cod_aj} -- {explicacao} -- confirmar memoria "
                             "de calculo conforme a IN RFB 2.305/2025",
                             r.n("VL_AJ"))
