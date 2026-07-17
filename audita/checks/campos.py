"""Validacao estrutural por campo: tipo, formato e obrigatoriedade.

Cobre o que da para conferir sem ambiguidade contra o proprio leiaute:
- campo tipo N (numerico) com conteudo que nao e numero no formato SPED;
- campo tipo D (data) com formato invalido ou data impossivel (32/13 etc);
- campo marcado como obrigatorio em qualquer situacao (OBRIGATORIOS) vazio.

Nao cobre obrigatoriedade condicional (OC) -- ver nota em layouts.py sobre
por que isso foi deixado de fora (evitar falso positivo sem a regra exata
de quando o campo passa a ser exigido).
"""
from . import check, Achado, ESTRUTURA
from ..layouts import LAYOUTS, OBRIGATORIOS
from ..parser import numero_sped_valido as numero_valido


def tipo_campo(nome):
    if nome.startswith(("VL_", "QTD_", "QUANT_", "ALIQ_")):
        return "N"
    if nome.startswith("DT_"):
        return "D"
    return "C"


def data_valida(v):
    v = (v or "").strip()
    if not v:
        return True
    if len(v) != 8 or not v.isdigit():
        return False
    dia, mes, ano = int(v[0:2]), int(v[2:4]), int(v[4:8])
    if not (1 <= mes <= 12) or not (1900 <= ano <= 2100):
        return False
    bissexto = ano % 4 == 0 and (ano % 100 != 0 or ano % 400 == 0)
    dias_mes = [31, 29 if bissexto else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return 1 <= dia <= dias_mes[mes - 1]


@check("E17", "Campo obrigatorio vazio",
       ESTRUTURA, "ALTA", "Leiaute EFD-Contribuicoes - campos obrigatorios em qualquer instancia do registro")
def e17(doc):
    for reg, campos_obrig in OBRIGATORIOS.items():
        for r in doc.todos(reg):
            for nome in campos_obrig:
                if not r[nome].strip():
                    yield Achado(r.linha, reg, nome, f"{nome} obrigatorio esta vazio")


@check("E18", "Campo numerico com conteudo fora do formato SPED",
       ESTRUTURA, "ALTA", "Leiaute EFD-Contribuicoes - campos tipo N (numero com virgula decimal)")
def e18(doc):
    for reg, campos_reg in LAYOUTS.items():
        alvo = [n for n in campos_reg if tipo_campo(n) == "N"]
        if not alvo:
            continue
        for r in doc.todos(reg):
            for nome in alvo:
                v = r[nome]
                if v and not numero_valido(v):
                    yield Achado(r.linha, reg, nome, f"{nome}={v!r} nao e numero SPED valido")


@check("E19", "Campo de data em formato ou valor invalido",
       ESTRUTURA, "ALTA", "Leiaute EFD-Contribuicoes - campos tipo D (DDMMAAAA)")
def e19(doc):
    for reg, campos_reg in LAYOUTS.items():
        alvo = [n for n in campos_reg if tipo_campo(n) == "D"]
        if not alvo:
            continue
        for r in doc.todos(reg):
            for nome in alvo:
                v = r[nome]
                if v and not data_valida(v):
                    yield Achado(r.linha, reg, nome, f"{nome}={v!r} nao e data DDMMAAAA valida")
