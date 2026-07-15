"""Gera um arquivo EFD-Contribuicoes sintetico para teste.

Contadores de bloco (0990/C990/M990/1990), o inventario 9900 e o 9990 sao
calculados dinamicamente a partir das linhas geradas -- so ficam errados
onde e proposital (9999, documentado abaixo). Erros propositais, um por
check que eles exercitam:

  E03  9999 declara total de linhas diferente do arquivo
  E11  0200 PROD002 sem NCM
  E12  C100 NUM_DOC 130 cancelado (COD_SIT=02) com VL_PIS/VL_COFINS no item
  E13  C100 NUM_DOC 123 escriturado duas vezes com a MESMA chave de acesso
  E14  mesma duplicidade acima tambem repete participante/modelo/serie/numero
  E15  C100 NUM_DOC 140, item com VL_PIS negativo
  E16  C100 NUM_DOC 140, DT_DOC posterior a DT_E_S
  E20  C170 do NUM_DOC 123 usa COD_NAT="02", 0400 so cadastra COD_NAT="01"
  E21  mesmo item usa COD_CTA="999999999", 0500 so cadastra COD_CTA="100010001"
  E27  C501 #3 usa NAT_BC_CRED="99", fora da Tabela 4.3.7
  E28  C501 #3 usa CST_PIS="77", fora da tabela de CST
  E29  M500 usa COD_CRED="999", fora da Tabela 4.3.6
  C05  C100 NUM_DOC 150, ALIQ_PIS=2,00 (fora do padrao 1,65)
  C07  C170 item 2 do NUM_DOC 123: CFOP de entrada numa nota de saida
  R01  0111 zerado nas partes divergindo da receita do detalhe
  R07  0111.REC_BRU_TOTAL preenchido sem bater com a soma das partes
  R08  M200/M600: VL_CONT_NC_REC declarado nao bate com a formula
  R09  M100: VL_CRED_DISP e SLD_CRED declarados nao batem com a formula
  R10  M100 x M105: VL_BC_PIS do pai (1000) nao bate com o filho (900)
  R11  1500: VL_TOT_CRED_APU declarado (999,99) nao bate com 06+07 (800)
  R12  soma 1100.VL_CRED_DESC_EFD (500) nao bate com M200.VL_TOT_CRED_DESC_ANT (0)
  R13  C180 NUM_ITEM PROD001: VL_TOT_ITEM (1000) nao bate com soma C185 (900)
  E26  1101 presente -- registro extemporaneo obsoleto (ver Guia, pos-08/2013)
  T01  C170 item PROD003 usa CST 04 (monofasico) -- sinalizacao, nao erro
  T02  C501/C505 com NAT_BC_CRED=02 (insumo) acima do limiar de relevancia
  T03  C501 com NAT_BC_CRED=09 (imobilizado) acima do limiar de relevancia
  T04  C100 NUM_DOC 150 aliquota fora do padrao sem registro 1010 no arquivo
"""
from collections import Counter


def dv_cnpj(base12):
    def calc(nums, pesos):
        s = sum(int(n) * p for n, p in zip(nums, pesos))
        d = 11 - s % 11
        return "0" if d > 9 else str(d)
    p1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    p2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    d1 = calc(base12, p1)
    d2 = calc(base12 + d1, p2)
    return base12 + d1 + d2


def dv_chave(base43):
    peso, s = 2, 0
    for d in reversed(base43):
        s += int(d) * peso
        peso = 2 if peso == 9 else peso + 1
    r = s % 11
    dv = 0 if r in (0, 1) else 11 - r
    return base43 + str(dv)


def chave_nfe(cnpj_emit, numero, serie="001"):
    base = "35" + "2401" + cnpj_emit + "55" + serie + str(numero).zfill(9) + "1" + "12345678"
    return dv_chave(base[:43])


CNPJ = dv_cnpj("112223330001")
CNPJ_PART = dv_cnpj("998887770001")

linhas = []


def add(*campos):
    linhas.append("|" + "|".join(str(c) for c in campos) + "|")


def fechar_bloco(prefixo, registro_fechamento):
    """Conta as linhas do bloco ja escritas e grava o registro de fechamento."""
    conta = sum(1 for l in linhas if l.split("|")[1].startswith(prefixo)) + 1
    add(registro_fechamento, conta)


# ---------------------------------------------------------------- Bloco 0 --
add("0000", "006", "0", "0", "", "01012024", "31012024",
    "EMPRESA TESTE LTDA", CNPJ, "SP", "3550308", "", "01", "1")
add("0110", "1", "1", "1", "")
# partes zeradas mas total preenchido: R01 (nao reflete detalhe) e R07 (soma nao bate)
add("0111", "0,00", "0,00", "0,00", "0,00", "500,00")
add("0140", "001", "MATRIZ", CNPJ, "SP", "111111111111", "3550308", "", "")
add("0150", CNPJ_PART, "FORNECEDOR X", "1058", CNPJ_PART, "", "", "3550308", "",
    "RUA A", "100", "", "CENTRO")
add("0190", "UN", "UNIDADE")
add("0200", "PROD001", "PRODUTO A", "", "", "UN", "00", "84713012", "", "", "", "0,00")
add("0200", "PROD002", "PRODUTO B", "", "", "UN", "00", "", "", "", "", "0,00")  # sem NCM -> E11
add("0200", "PROD003", "PRODUTO C MONOFASICO", "", "", "UN", "00", "27101259", "", "", "", "0,00")
add("0400", "01", "Receita de venda de mercadorias")           # C170 vai usar "02" -> E20
add("0500", "01012024", "01", "01", "1", "100010001", "Receita de Vendas")  # C170 usa outro -> E21
fechar_bloco("0", "0990")

# ---------------------------------------------------------------- Bloco C --
add("C010", CNPJ, "1")

# C100 #1: NF valida, totais do documento batendo com os itens
chave1 = chave_nfe(CNPJ, 123)
add("C100", "1", "0", CNPJ_PART, "55", "00", "1", "123", chave1, "15012024",
    "15012024", "1000,00", "0", "0,00", "0,00", "1000,00", "0", "0,00", "0,00",
    "0,00", "0,00", "0,00", "0,00", "0,00", "0,00", "16,50", "76,00", "0,00", "0,00")
add("C170", "1", "PROD001", "", "10", "UN", "600,00", "0,00", "0", "00", "5102",
    "02", "0,00", "0,00", "0,00", "0,00", "0,00", "0,00", "0", "", "", "0,00",
    "0,00", "0,00", "01", "600,00", "1,65", "0,00", "0,00", "9,90", "01",
    "600,00", "7,60", "0,00", "0,00", "45,60", "999999999", "0,00")
# CFOP de entrada numa nota de saida -> C07
add("C170", "2", "PROD002", "", "5", "UN", "400,00", "0,00", "0", "00", "1102",
    "", "0,00", "0,00", "0,00", "0,00", "0,00", "0,00", "0", "", "", "0,00",
    "0,00", "0,00", "01", "400,00", "1,65", "0,00", "0,00", "6,60", "01",
    "400,00", "7,60", "0,00", "0,00", "30,40", "", "0,00")
# CST 04 (monofasico, aliquota zero) -> T01 (sinalizacao, nao soma PIS/COFINS)
add("C170", "3", "PROD003", "", "1", "UN", "500,00", "0,00", "0", "00", "5102",
    "01", "0,00", "0,00", "0,00", "0,00", "0,00", "0,00", "0", "", "", "0,00",
    "0,00", "0,00", "04", "0,00", "0,00", "0,00", "0,00", "0,00", "04",
    "0,00", "0,00", "0,00", "0,00", "0,00", "100010001", "0,00")

# C100 #2: MESMA chave, participante, modelo, serie e numero do #1 -> E13 + E14
add("C100", "1", "0", CNPJ_PART, "55", "00", "1", "123", chave1, "15012024",
    "15012024", "600,00", "0", "0,00", "0,00", "600,00", "0", "0,00", "0,00",
    "0,00", "0,00", "0,00", "0,00", "0,00", "0,00", "9,90", "45,60", "0,00", "0,00")
add("C170", "1", "PROD001", "", "10", "UN", "600,00", "0,00", "0", "00", "5102",
    "", "0,00", "0,00", "0,00", "0,00", "0,00", "0,00", "0", "", "", "0,00",
    "0,00", "0,00", "01", "600,00", "1,65", "0,00", "0,00", "9,90", "01",
    "600,00", "7,60", "0,00", "0,00", "45,60", "", "0,00")

# C100 #3: documento CANCELADO (COD_SIT=02) com item apurando PIS/COFINS -> E12
chave3 = chave_nfe(CNPJ, 130)
add("C100", "1", "0", CNPJ_PART, "55", "02", "1", "130", chave3, "15012024",
    "15012024", "200,00", "0", "0,00", "0,00", "200,00", "0", "0,00", "0,00",
    "0,00", "0,00", "0,00", "0,00", "0,00", "0,00", "3,30", "15,20", "0,00", "0,00")
add("C170", "1", "PROD001", "", "2", "UN", "200,00", "0,00", "0", "00", "5102",
    "", "0,00", "0,00", "0,00", "0,00", "0,00", "0,00", "0", "", "", "0,00",
    "0,00", "0,00", "01", "200,00", "1,65", "0,00", "0,00", "3,30", "01",
    "200,00", "7,60", "0,00", "0,00", "15,20", "", "0,00")

# C100 #4: DT_DOC posterior a DT_E_S (E16) e item com VL_PIS negativo (E15)
chave4 = chave_nfe(CNPJ, 140)
add("C100", "1", "0", CNPJ_PART, "55", "00", "1", "140", chave4, "20012024",
    "15012024", "100,00", "0", "0,00", "0,00", "100,00", "0", "0,00", "0,00",
    "0,00", "0,00", "0,00", "0,00", "0,00", "0,00", "-1,65", "7,60", "0,00", "0,00")
add("C170", "1", "PROD001", "", "1", "UN", "100,00", "0,00", "0", "00", "5102",
    "", "0,00", "0,00", "0,00", "0,00", "0,00", "0,00", "0", "", "", "0,00",
    "0,00", "0,00", "01", "100,00", "1,65", "0,00", "0,00", "-1,65", "01",
    "100,00", "7,60", "0,00", "0,00", "7,60", "", "0,00")

# C100 #5: aliquota de PIS fora do padrao (2,00% em vez de 1,65%), sem
# registro 1010 no arquivo -> C05 (existente) e T04 (sinalizacao nova)
chave5 = chave_nfe(CNPJ, 150)
add("C100", "1", "0", CNPJ_PART, "55", "00", "1", "150", chave5, "20012024",
    "20012024", "300,00", "0", "0,00", "0,00", "300,00", "0", "0,00", "0,00",
    "0,00", "0,00", "0,00", "0,00", "0,00", "0,00", "6,00", "22,80", "0,00", "0,00")
add("C170", "1", "PROD001", "", "3", "UN", "300,00", "0,00", "0", "00", "5102",
    "", "0,00", "0,00", "0,00", "0,00", "0,00", "0,00", "0", "", "", "0,00",
    "0,00", "0,00", "01", "300,00", "2,00", "0,00", "0,00", "6,00", "01",
    "300,00", "7,60", "0,00", "0,00", "22,80", "", "0,00")

# C180/C181/C185: escrituracao consolidada de NF-e (alternativa a C100/C170)
# -- C185 (COFINS) proposital divergente do total do item -> R13
add("C180", "55", "01012024", "31012024", "PROD001", "84713012", "", "1000,00")
add("C181", "01", "5102", "1000,00", "0,00", "1000,00", "1,65", "0,00", "0,00", "16,50", "")
add("C185", "01", "5102", "900,00", "0,00", "900,00", "7,60", "0,00", "0,00", "68,40", "")

# C190/C191/C195: escrituracao consolidada de AQUISICOES por NF-e (espelho
# do C180/C181/C185) -- C195 (COFINS) proposital divergente -> R14
add("C190", "55", "01012024", "31012024", "PROD001", "84713012", "", "2000,00")
add("C191", CNPJ_PART, "50", "1102", "2000,00", "0,00", "2000,00", "1,65", "0,00", "0,00", "33,00", "")
add("C195", CNPJ_PART, "50", "1102", "1800,00", "0,00", "1800,00", "7,60", "0,00", "0,00", "136,80", "")

# C500/C501/C505: aquisicao de energia/agua/gas com credito -- usado para
# exercitar NAT_BC_CRED (insumo -> T02, imobilizado -> T03, invalido -> E27)
# e CST invalido (E28)
add("C500", CNPJ_PART, "06", "00", "", "", "500001", "15012024", "",
    "400000,00", "0,00", "", "6600,00", "30400,00", "")
add("C501", "50", "400000,00", "02", "400000,00", "1,65", "6600,00", "")     # insumo -> T02
add("C501", "50", "350000,00", "09", "350000,00", "1,65", "5775,00", "")    # imobilizado -> T03
add("C501", "77", "1000,00", "99", "1000,00", "1,65", "16,50", "")          # CST/NAT invalidos -> E28/E27
add("C505", "50", "400000,00", "02", "400000,00", "7,60", "30400,00", "")   # insumo (COFINS) -> T02

fechar_bloco("C", "C990")

# ---------------------------------------------------------------- Bloco M --
# M100/M105: VL_CRED_DISP e SLD_CRED declarados nao fecham (R09); a base
# do pai (1000,00) nao bate com a soma do filho M105 (900,00) (R10)
add("M100", "101", "0", "1000,00", "1,65", "0,00", "0,00", "16,50", "0,00", "0,00",
    "0,00", "99,99", "0", "16,50", "0,00")
add("M105", "02", "50", "1000,00", "0,00", "1000,00", "900,00", "0,00", "0,00", "Insumo")
# M110: ajuste de acrescimo de credito (50,00) nao reconhecido no
# VL_AJUS_ACRES do pai (0,00) -> R17
add("M110", "1", "50,00", "05", "", "Ajuste de credito teste", "15012024")

# M500/M505: internamente consistentes, mas COD_CRED invalido -> E29
add("M500", "999", "0", "900,00", "7,60", "0,00", "0,00", "68,40", "0,00", "0,00",
    "0,00", "68,40", "0", "68,40", "0,00")
add("M505", "02", "50", "900,00", "0,00", "900,00", "900,00", "0,00", "0,00", "Insumo")
# M510: ajuste de reducao de credito (30,00) nao reconhecido no
# VL_AJUS_REDUC do pai (0,00) -> R17
add("M510", "0", "30,00", "06", "", "Estorno de credito teste", "15012024")

# Consolidacao do periodo com formula que nao fecha -> R08
add("M200", "100,00", "0,00", "0,00", "0,00", "0,00", "0,00", "1,00",
    "0,00", "0,00", "0,00", "0,00", "1,00")
add("M600", "100,00", "0,00", "0,00", "0,00", "0,00", "0,00", "1,00",
    "0,00", "0,00", "0,00", "0,00", "1,00")

# M210 (leiaute 2019+): internamente consistente (campo07 e campo16 batem),
# mas o VL_CONT_PER (16,50) nao bate com M200.VL_TOT_CONT_NC_PER (100,00) -> R16
add("M210", "01", "1000,00", "1000,00", "0,00", "0,00", "1000,00", "1,65", "0,00",
    "0,00", "16,50", "0,00", "0,00", "0,00", "0,00", "16,50")
# M215: ajuste de acrescimo de base de calculo (40,00) nao reconhecido no
# VL_AJUS_ACRES_BC_PIS do pai (0,00) -> R18
add("M215", "1", "40,00", "01", "", "Ajuste BC teste", "15012024", "", CNPJ, "")
# M220: ajuste de acrescimo de contribuicao (10,00) nao reconhecido no
# VL_AJUS_ACRES do pai (0,00) -> R19
add("M220", "1", "10,00", "05", "", "Ajuste contribuicao teste", "15012024")

# M610: campo07 (VL_BC_CONT_AJUS) declarado nao bate com a formula -> R15
# (e o VL_CONT_PER tambem diverge do M600.VL_TOT_CONT_NC_PER -> R16)
add("M610", "01", "800,00", "800,00", "0,00", "0,00", "999,99", "7,60", "0,00",
    "0,00", "60,80", "0,00", "0,00", "0,00", "0,00", "60,80")
# M615: ajuste de reducao de base de calculo (20,00) nao reconhecido no
# VL_AJUS_REDUC_BC_COFINS do pai (0,00) -> R18
add("M615", "0", "20,00", "02", "", "Ajuste BC teste", "15012024", "", CNPJ, "")
# M620: ajuste de reducao de contribuicao (5,00) nao reconhecido no
# VL_AJUS_REDUC do pai (0,00) -> R19
add("M620", "0", "5,00", "06", "", "Estorno contribuicao teste", "15012024")
fechar_bloco("M", "M990")

# ---------------------------------------------------------------- Bloco 1 --
# 1100 (PIS): internamente consistente, mas o credito descontado em periodo
# anterior (500,00) nao bate com M200.VL_TOT_CRED_DESC_ANT (0,00) -> R12
add("1100", "122023", "01", "", "101", "500,00", "0,00", "500,00", "0,00", "0,00",
    "0,00", "500,00", "500,00", "0,00", "0,00", "0,00", "0,00", "0,00")
# 1500 (COFINS): VL_TOT_CRED_APU declarado (999,99) nao bate com 06+07 (800,00) -> R11
add("1500", "122023", "01", "", "201", "800,00", "0,00", "999,99", "0,00", "0,00",
    "0,00", "999,99", "0,00", "0,00", "0,00", "0,00", "0,00", "999,99")
# registro extemporaneo obsoleto (sem validade desde 08/2013) -> E26
add("1101", "0")
fechar_bloco("1", "1990")

# ---------------------------------------------------------------- Bloco 9 --
contagem_pre9900 = Counter(l.split("|")[1] for l in linhas)
tipos_9900 = sorted(contagem_pre9900) + ["9900"]
qtd_9900 = len(tipos_9900)
for t in sorted(contagem_pre9900):
    add("9900", t, contagem_pre9900[t])
add("9900", "9900", qtd_9900)
add("9990", qtd_9900 + 2)   # linhas 9900 + a propria 9990 + a 9999
add("9999", "1")            # proposital ERRADO -> demonstra E03

conteudo = "\n".join(linhas) + "\n"
with open("exemplo_sped.txt", "w", encoding="latin-1") as f:
    f.write(conteudo)
print(f"exemplo_sped.txt gerado com {len(linhas)} linhas")
print(f"CNPJ={CNPJ}  CNPJ_PART={CNPJ_PART}")
print(f"chaves: {chave1} (dup.) / {chave3} (cancelada) / {chave4} (data/negativo) / {chave5} (aliquota)")
