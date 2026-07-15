"""Checks estruturais: o arquivo contra ele mesmo. Zero dependencia externa."""
from collections import defaultdict
from . import check, Achado, ESTRUTURA, RISCO
from ..layouts import (PAI, LAYOUTS, COD_SIT_SEM_EFEITO, BLOCO_1_REGISTROS_OBSOLETOS,
                        NAT_BC_CRED_VALIDOS, CST_VALIDOS, COD_CRED_VALIDOS)


def _dv_cnpj(c):
    c = "".join(ch for ch in c if ch.isdigit())
    if len(c) != 14 or c == c[0] * 14:
        return False
    for pos, pesos in ((12, [5,4,3,2,9,8,7,6,5,4,3,2]),
                       (13, [6,5,4,3,2,9,8,7,6,5,4,3,2])):
        s = sum(int(c[i]) * pesos[i] for i in range(pos))
        d = 11 - s % 11
        d = 0 if d > 9 else d
        if int(c[pos]) != d:
            return False
    return True


def _dv_chave(ch):
    ch = "".join(x for x in ch if x.isdigit())
    if len(ch) != 44:
        return False
    peso, s = 2, 0
    for d in reversed(ch[:43]):
        s += int(d) * peso
        peso = 2 if peso == 9 else peso + 1
    r = s % 11
    dv = 0 if r in (0, 1) else 11 - r
    return dv == int(ch[43])


@check("E01", "9900 declara quantidade diferente da existente",
       ESTRUTURA, "ALTA", "Guia Pratico EFD-Contribuicoes - registro 9900")
def e01(doc):
    for r in doc.todos("9900"):
        declarado = int(r["QTD_REG_BLC"] or 0)
        real = doc.contagem.get(r["REG_BLC"], 0)
        if declarado != real:
            yield Achado(r.linha, "9900", r["REG_BLC"],
                         f"declarado {declarado}, existem {real}",
                         abs(declarado - real))


@check("E02", "Totalizador de bloco (X990) nao bate com as linhas do bloco",
       ESTRUTURA, "ALTA", "Guia Pratico - registros de encerramento de bloco")
def e02(doc):
    for reg in list(doc.por_reg):
        if len(reg) == 4 and reg.endswith("990") and reg != "9990":
            b = reg[0]
            r990 = doc.um(reg)
            declarado = int(r990.campos[1] or 0) if len(r990.campos) > 1 else 0
            real = sum(q for r, q in doc.contagem.items() if r.startswith(b))
            if declarado != real:
                yield Achado(r990.linha, reg, f"bloco {b}",
                             f"declarado {declarado}, existem {real}",
                             abs(declarado - real))


@check("E03", "9999 declara total de linhas diferente do arquivo",
       ESTRUTURA, "ALTA", "Guia Pratico - registro 9999")
def e03(doc):
    r = doc.um("9999")
    if not r:
        yield Achado(0, "9999", "", "registro 9999 ausente")
        return
    declarado = int(r["QTD_LIN"] or 0)
    if declarado != doc.total_linhas_arquivo:
        yield Achado(r.linha, "9999", "arquivo",
                     f"declarado {declarado}, arquivo tem {doc.total_linhas_arquivo}",
                     abs(declarado - doc.total_linhas_arquivo))


@check("E04", "Registro filho sem registro pai",
       ESTRUTURA, "ALTA", "Hierarquia do leiaute")
def e04(doc):
    for filho, pai in PAI.items():
        for r in doc.todos(filho):
            if r.pai is None:
                yield Achado(r.linha, filho, "", f"{filho} sem {pai} anterior")


@check("E05", "CNPJ com digito verificador invalido",
       ESTRUTURA, "MEDIA", "Modulo 11")
def e05(doc):
    for reg, campo in (("0000", "CNPJ"), ("0140", "CNPJ"), ("0150", "CNPJ"),
                       ("C010", "CNPJ"), ("D010", "CNPJ"), ("A010", "CNPJ"),
                       ("F010", "CNPJ")):
        for r in doc.todos(reg):
            v = r[campo]
            if v and not _dv_cnpj(v):
                yield Achado(r.linha, reg, r["COD_PART"] or v,
                             f"CNPJ invalido: {v}")


@check("E06", "Chave de NF-e/CT-e com digito verificador invalido",
       ESTRUTURA, "ALTA", "Modulo 11 - chave de acesso")
def e06(doc):
    for reg, campo in (("C100", "CHV_NFE"), ("D100", "CHV_CTE")):
        for r in doc.todos(reg):
            v = r[campo]
            if v and not _dv_chave(v):
                yield Achado(r.linha, reg, r["NUM_DOC"], f"chave invalida: {v}")


@check("E07", "Chave de NF-e incoerente com CNPJ / serie / numero do documento",
       ESTRUTURA, "ALTA", "Composicao da chave de acesso (NT 2005)")
def e07(doc):
    for r in doc.todos("C100"):
        ch = "".join(x for x in r["CHV_NFE"] if x.isdigit())
        if len(ch) != 44:
            continue
        serie_ch, num_ch = ch[22:25], ch[25:34]
        if r["SER"] and int(serie_ch) != int(r["SER"] or 0):
            yield Achado(r.linha, "C100", r["NUM_DOC"],
                         f"serie na chave={int(serie_ch)} vs SER={r['SER']}")
        if r["NUM_DOC"] and int(num_ch) != int(r["NUM_DOC"] or 0):
            yield Achado(r.linha, "C100", r["NUM_DOC"],
                         f"numero na chave={int(num_ch)} vs NUM_DOC={r['NUM_DOC']}")


@check("E08", "Documento com data fora da competencia escriturada",
       ESTRUTURA, "MEDIA", "Guia Pratico - periodo da escrituracao")
def e08(doc):
    ini, fim = doc.competencia
    if not ini:
        return

    def key(d):
        return d[4:8] + d[2:4] + d[0:2] if len(d) == 8 else ""

    ki, kf = key(ini), key(fim)
    for reg, campo in (("C100", "DT_E_S"), ("A100", "DT_DOC"),
                       ("D100", "DT_A_P"), ("F100", "DT_OPER")):
        for r in doc.todos(reg):
            d = r[campo]
            if d and key(d) and not (ki <= key(d) <= kf):
                yield Achado(r.linha, reg, r["NUM_DOC"] or r["COD_PART"],
                             f"{campo}={d} fora de {ini}-{fim}")


@check("E09", "Item usado no documento sem cadastro no 0200",
       ESTRUTURA, "MEDIA", "Guia Pratico - registro 0200")
def e09(doc):
    cad = {r["COD_ITEM"] for r in doc.todos("0200")}
    for reg in ("C170", "A170", "F100"):
        for r in doc.todos(reg):
            c = r["COD_ITEM"]
            if c and c not in cad:
                yield Achado(r.linha, reg, c, "COD_ITEM sem 0200 correspondente")


@check("E10", "Participante usado no documento sem cadastro no 0150",
       ESTRUTURA, "MEDIA", "Guia Pratico - registro 0150")
def e10(doc):
    cad = {r["COD_PART"] for r in doc.todos("0150")}
    for reg in ("C100", "A100", "D100", "F100", "C500"):
        for r in doc.todos(reg):
            c = r["COD_PART"]
            if c and c not in cad:
                yield Achado(r.linha, reg, c, "COD_PART sem 0150 correspondente")


@check("E11", "Item cadastrado no 0200 sem NCM",
       ESTRUTURA, "MEDIA", "Guia Pratico - registro 0200 campo COD_NCM")
def e11(doc):
    usados = {r["COD_ITEM"] for r in doc.todos("C170")}
    for r in doc.todos("0200"):
        if r["COD_ITEM"] in usados and not r["COD_NCM"].strip():
            yield Achado(r.linha, "0200", r["COD_ITEM"],
                         f"sem NCM: {r['DESCR_ITEM'][:40]}")


@check("E12", "Documento cancelado/substituido com valor de PIS/COFINS no item",
       ESTRUTURA, "ALTA",
       "COD_SIT 02/03/04/05 (cancelado/substituido) nao produz efeito fiscal; "
       "nao deveria gerar debito/credito de PIS/COFINS")
def e12(doc):
    for r in doc.todos("C170"):
        c100 = r.pai
        if not c100 or c100["COD_SIT"] not in COD_SIT_SEM_EFEITO:
            continue
        vp, vc = r.n("VL_PIS"), r.n("VL_COFINS")
        if vp > 0 or vc > 0:
            yield Achado(r.linha, "C170", f"NF {c100['NUM_DOC']} (COD_SIT={c100['COD_SIT']})",
                         f"VL_PIS={vp:.2f} VL_COFINS={vc:.2f} em documento sem efeito fiscal",
                         vp + vc)


@check("E13", "Chave de NF-e escriturada em mais de um C100",
       ESTRUTURA, "ALTA",
       "A chave de acesso e unica por NF-e; repeticao indica debito/credito em duplicidade")
def e13(doc):
    vistos = defaultdict(list)
    for r in doc.todos("C100"):
        ch = "".join(x for x in r["CHV_NFE"] if x.isdigit())
        if len(ch) == 44:
            vistos[ch].append(r)
    for ch, regs in vistos.items():
        if len(regs) > 1:
            linhas = ", ".join(f"L{r.linha}" for r in regs)
            yield Achado(regs[0].linha, "C100", ch[:10] + "...",
                         f"chave repetida {len(regs)}x: {linhas}",
                         sum(r.n("VL_PIS") + r.n("VL_COFINS") for r in regs))


@check("E14", "Documento duplicado (mesmo participante + modelo + serie + numero)",
       ESTRUTURA, "MEDIA",
       "COD_PART/COD_MOD/SER/NUM_DOC deveria identificar um unico documento no periodo")
def e14(doc):
    vistos = defaultdict(list)
    for r in doc.todos("C100"):
        chave = (r["COD_PART"], r["COD_MOD"], r["SER"], r["NUM_DOC"])
        if all(chave):
            vistos[chave].append(r)
    for chave, regs in vistos.items():
        if len(regs) > 1:
            linhas = ", ".join(f"L{r.linha}" for r in regs)
            yield Achado(regs[0].linha, "C100", f"NF {chave[3]}",
                         f"documento repetido {len(regs)}x: {linhas}")


@check("E15", "Valor numerico negativo em campo do leiaute SPED que nao admite sinal",
       ESTRUTURA, "MEDIA",
       "Campos VL_/QTD_/ALIQ_/QUANT_ do SPED sao sempre positivos; "
       "ajuste de sentido e feito pela natureza do lancamento, nao por sinal negativo")
def e15(doc):
    for reg, campos_reg in LAYOUTS.items():
        alvo = [n for n in campos_reg if n.startswith(("VL_", "QTD_", "ALIQ_", "QUANT_"))]
        if not alvo:
            continue
        for r in doc.todos(reg):
            for nome in alvo:
                v = r[nome].strip()
                if v.startswith("-"):
                    yield Achado(r.linha, reg, nome, f"{nome}={v}")


@check("E16", "Data de emissao posterior a data de entrada/saida do mesmo documento",
       ESTRUTURA, "MEDIA", "DT_DOC nao pode ser posterior a DT_E_S/DT_A_P/DT_EXE_SERV")
def e16(doc):
    def key(d):
        return d[4:8] + d[2:4] + d[0:2] if len(d) == 8 else ""

    for reg, campo in (("C100", "DT_E_S"), ("D100", "DT_A_P"), ("A100", "DT_EXE_SERV")):
        for r in doc.todos(reg):
            ke, ko = key(r["DT_DOC"]), key(r[campo])
            if ke and ko and ke > ko:
                yield Achado(r.linha, reg, r["NUM_DOC"],
                             f"DT_DOC={r['DT_DOC']} posterior a {campo}={r[campo]}")


@check("E20", "COD_NAT usado no C170 sem cadastro correspondente no 0400",
       ESTRUTURA, "BAIXA", "registro 0400 (natureza da receita/rubrica)")
def e20(doc):
    cad = {r["COD_NAT"] for r in doc.todos("0400")}
    if not cad:
        return
    for r in doc.todos("C170"):
        c = r["COD_NAT"]
        if c and c not in cad:
            yield Achado(r.linha, "C170", c, "COD_NAT sem 0400 correspondente")


@check("E21", "COD_CTA usado sem cadastro correspondente no 0500",
       ESTRUTURA, "BAIXA", "registro 0500 (plano de contas)")
def e21(doc):
    cad = {r["COD_CTA"] for r in doc.todos("0500")}
    if not cad:
        return
    for reg in ("C170", "D101", "D105", "A170", "F100", "M400", "M800"):
        for r in doc.todos(reg):
            c = r["COD_CTA"]
            if c and c not in cad:
                yield Achado(r.linha, reg, c, "COD_CTA sem 0500 correspondente")


# Ordem oficial dos blocos da EFD-Contribuicoes: 0 (abertura/identificacao),
# A (servicos - ISS), C (mercadorias - NF-e), D (servicos - CT-e/transporte),
# F (demais documentos/operacoes), M (apuracao PIS/COFINS), 1 (complemento
# da escrituracao), 9 (controle/encerramento). Estrutura fixa e amplamente
# documentada do leiaute, estavel entre versoes.
_ORDEM_BLOCO = {"0": 0, "A": 1, "C": 2, "D": 3, "F": 4, "M": 5, "1": 6, "9": 7}


@check("E22", "Registro fora da ordem oficial de blocos do arquivo",
       ESTRUTURA, "ALTA",
       "Guia Pratico - ordem fixa dos blocos: 0, A, C, D, F, M, 1, 9")
def e22(doc):
    maior_idx, maior_bloco, maior_linha = -1, None, 0
    for r in doc.registros:
        idx = _ORDEM_BLOCO.get(r.reg[0])
        if idx is None:
            continue
        if idx < maior_idx:
            yield Achado(r.linha, r.reg, "",
                         f"bloco {r.reg[0]} apos bloco {maior_bloco} "
                         f"(L{maior_linha}) -- ordem esperada 0,A,C,D,F,M,1,9")
        else:
            maior_idx, maior_bloco, maior_linha = idx, r.reg[0], r.linha


@check("E23", "Codigo de cadastro duplicado (0200/0150)",
       ESTRUTURA, "MEDIA",
       "COD_ITEM (0200) e COD_PART (0150) sao chave unica do cadastro no periodo")
def e23(doc):
    for reg, campo in (("0200", "COD_ITEM"), ("0150", "COD_PART")):
        vistos = defaultdict(list)
        for r in doc.todos(reg):
            v = r[campo]
            if v:
                vistos[v].append(r)
        for v, regs in vistos.items():
            if len(regs) > 1:
                linhas = ", ".join(f"L{r.linha}" for r in regs)
                yield Achado(regs[0].linha, reg, v,
                             f"{campo} cadastrado {len(regs)}x: {linhas}")


@check("E24", "Escrituracao retificadora sem referencia ao arquivo original",
       ESTRUTURA, "ALTA",
       "Guia Pratico - registro 0000: TIPO_ESCRIT=1 (retificadora) exige "
       "NUM_REC_ANTERIOR preenchido com o recibo do arquivo substituido")
def e24(doc):
    r = doc.um("0000")
    if r and r["TIPO_ESCRIT"] == "1" and not r["NUM_REC_ANTERIOR"].strip():
        yield Achado(r.linha, "0000", "", "TIPO_ESCRIT=1 sem NUM_REC_ANTERIOR")


# Modelos de documento eletronico cuja chave de acesso e obrigatoria.
_MODELO_EXIGE_CHV_NFE = {"55", "65"}
_MODELO_EXIGE_CHV_CTE = {"57"}


@check("E25", "Documento eletronico sem chave de acesso",
       ESTRUTURA, "ALTA",
       "COD_MOD 55/65 (NF-e/NFC-e) exige CHV_NFE; COD_MOD 57 (CT-e) exige CHV_CTE")
def e25(doc):
    for r in doc.todos("C100"):
        if r["COD_MOD"] in _MODELO_EXIGE_CHV_NFE and not r["CHV_NFE"].strip():
            yield Achado(r.linha, "C100", r["NUM_DOC"],
                         f"COD_MOD={r['COD_MOD']} sem CHV_NFE")
    for r in doc.todos("D100"):
        if r["COD_MOD"] in _MODELO_EXIGE_CHV_CTE and not r["CHV_CTE"].strip():
            yield Achado(r.linha, "D100", r["NUM_DOC"],
                         f"COD_MOD={r['COD_MOD']} sem CHV_CTE")


@check("E26", "Registro de credito/contribuicao extemporanea do Bloco 1 sem validade atual",
       ESTRUTURA, "MEDIA",
       "Guia Pratico, secao do registro 1101: registros 1101/1102/1200/1210/1220/"
       "1501/1502/1600/1610/1620 nao sao mais validados pelo PVA para fatos "
       "geradores a partir de agosto/2013 -- o mecanismo correto e a retificacao "
       "da escrituracao original (prazo de ate 5 anos, IN RFB 1.387/2013)")
def e26(doc):
    for reg in sorted(BLOCO_1_REGISTROS_OBSOLETOS):
        for r in doc.todos(reg):
            yield Achado(r.linha, reg, "",
                         f"{reg} presente -- registro extemporaneo sem validade "
                         "para fatos geradores a partir de 08/2013; use retificacao")


@check("E27", "NAT_BC_CRED fora da tabela oficial de base de calculo do credito",
       ESTRUTURA, "MEDIA", "Guia Pratico, Tabela 4.3.7 - Base de Calculo do Credito")
def e27(doc):
    for reg, campos_reg in LAYOUTS.items():
        if "NAT_BC_CRED" not in campos_reg:
            continue
        for r in doc.todos(reg):
            v = r["NAT_BC_CRED"].strip()
            if v and v not in NAT_BC_CRED_VALIDOS:
                yield Achado(r.linha, reg, v, f"NAT_BC_CRED={v} fora da Tabela 4.3.7")


@check("E28", "CST fora do conjunto oficial de codigos de situacao tributaria",
       ESTRUTURA, "MEDIA", "Guia Pratico, Tabelas 4.3.3 (PIS) e 4.3.4 (COFINS)")
def e28(doc):
    for reg, campos_reg in LAYOUTS.items():
        alvo = [n for n in campos_reg if n in ("CST_PIS", "CST_COFINS")]
        if not alvo:
            continue
        for r in doc.todos(reg):
            for nome in alvo:
                v = r[nome].strip()
                if v and v not in CST_VALIDOS:
                    yield Achado(r.linha, reg, v, f"{nome}={v} fora da tabela de CST")


@check("E29", "COD_CRED fora da tabela oficial de tipo de credito",
       ESTRUTURA, "BAIXA", "Guia Pratico, Tabela 4.3.6 - Codigo de Tipo de Credito")
def e29(doc):
    for reg, campos_reg in LAYOUTS.items():
        if "COD_CRED" not in campos_reg:
            continue
        for r in doc.todos(reg):
            v = r["COD_CRED"].strip()
            if v and v not in COD_CRED_VALIDOS:
                yield Achado(r.linha, reg, v, f"COD_CRED={v} fora da Tabela 4.3.6")
