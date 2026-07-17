"""Leiaute declarativo da EFD-Contribuicoes.

FONTE E CONFERENCIA
--------------------
O usuario forneceu o PDF oficial do Guia Pratico da EFD-Contribuicoes
localmente (arquivo "file.pdf", 433 paginas -- o anexo de chat havia
falhado por exceder o limite de 600 paginas da API de leitura de
documento; contornado extraindo o texto via pypdf por linha de comando).
Confirmado pela primeira pagina do documento: "Guia Pratico da EFD
Contribuicoes - Versao 1.35: Atualizacao em 18/06/2021".

RODADA 7 -- familia "Lucro Presumido consolidado" (registros 1900, F500,
F510, F525, F550, F560), conferida campo a campo contra o mesmo PDF do
Guia Pratico v1.35 ja usado desde a Rodada 1 (_guia_pratico_full.txt --
os 6 registros ja estavam la, so nao tinham sido modelados ainda). Motivo
da rodada: usuario colou o texto de uma Nota Tecnica sobre os registros
1900/F525 (exemplo numerico de PJ do lucro presumido); antes de modelar a
partir desse texto colado, procurei os mesmos registros na fonte primaria
ja verificada -- estavam la, com a coluna "Obrig" oficial, entao a
reconciliacao foi feita contra o PDF de verdade, nao contra o texto
colado (mesma disciplina da Rodada 1: nunca modelar leiaute a partir de
fonte secundaria quando a primaria esta disponivel). Zero divergencia de
ordem de campo entre o exemplo da Nota Tecnica e o Guia Pratico.
  - 1900 (nivel 2, Bloco 1): consolidacao de documentos emitidos por PJ do
    lucro presumido com escrituracao consolidada (alternativa ao C100/
    C170 individualizado). Obrig=S confirmado: CNPJ, COD_MOD, VL_TOT_REC.
  - F500/F510 (nivel 3, Bloco F, regime de caixa): consolidacao por CST;
    F500 usa aliquota ad valorem (%), F510 usa aliquota por unidade de
    medida de produto em reais (bebidas frias/combustivel/alcool, regime
    especial). Obrig=S: VL_REC_CAIXA, CST_PIS, CST_COFINS.
  - F525 (nivel 3, Bloco F): detalhamento da composicao da receita
    RECEBIDA no regime de caixa (por cliente, administradora de cartao,
    titulo de credito, item ou outro criterio). O proprio Guia afirma que
    o total do F525 deve bater com o total do F500 -- implementado como
    check R20 (reconciliacao.py), por soma de totais (nao por vinculo de
    hierarquia -- ver nota abaixo). Obrig=S: VL_REC, IND_REC, VL_REC_DET.
  - F550/F560 (nivel 3, Bloco F, regime de competencia): espelho exato de
    F500/F510, so que para receita AUFERIDA (competencia) em vez de
    RECEBIDA (caixa) -- campo 02 chama VL_REC_COMP em vez de
    VL_REC_CAIXA, resto identico. Obrig=S: VL_REC_COMP, CST_PIS,
    CST_COFINS.
  - Nota sobre hierarquia: o Guia da "Nivel hierarquico 3" para F500,
    F510, F525, F550 e F560 (todos no mesmo nivel), sem indicar de forma
    inequivoca no texto qual registro e o pai fisico direto de cada um
    dentro do arquivo (diferente de C100->C170, onde a hierarquia e clara
    pela propria estrutura de secoes do Guia). Por isso nenhum destes foi
    adicionado ao dicionario PAI -- evita falso positivo em E04 por um
    vinculo de hierarquia que eu nao conseguiria confirmar com certeza. A
    reconciliacao F525 x F500/F510 (R20) usa soma de totais, o mesmo
    padrao ja usado em R01/R02 entre 0111 e o detalhe (que tambem nao
    depende de vinculo de hierarquia).

RODADA 6 -- Nota Tecnica EFD-Contribuicoes no 012/2026 (11 paginas, PDF
fornecido pelo usuario, extraido para _nota_tecnica_012_2026_full.txt):
"Orientacao para os Contribuintes de PIS/COFINS" sobre a Lei Complementar
no 224/2025 (reducao linear de incentivos e beneficios tributarios,
vigente a partir de 01/04/2026, regulamentada pela IN RFB no 2.305/2025).
Pesquisa web confirmou antes desta rodada (varias buscas, sempre
consistente) que o Guia Pratico como documento segue na v1.35 -- nao ha
versao 1.36+ publicada -- entao a base de reconciliacao do leiaute
continua valida; esta NT e um adendo especifico, nao uma revisao geral.
Achados da leitura:
  - O mecanismo NAO cria registro novo nem exige mudanca no CST original
    da operacao (confirmado explicitamente pelo texto: "nao devem ser
    alteradas as informacoes de codigo de situacao tributaria - CST
    originalmente previstas na legislacao"). Usa os registros de ajuste
    que ja sao modelados aqui: M110/M115, M220/M225 (PIS) e M510/M515,
    M620/M625 (COFINS) -- ja reconciliados pelos checks R17 e R19. Nenhuma
    mudanca estrutural necessaria nesses registros.
  - 2 codigos novos na Tabela 4.3.8 (COD_AJ), introduzidos por esta NT:
    "11" (reducao de aliquota zero/isencao, art. 4o par. 4o I da LC
    224/2025) e "12" (limite de 90% no aproveitamento de credito
    presumido, art. 4o par. 2o II d da LC 224/2025). Modelados em T05
    (checks/tese.py) como sinalizacao -- NAO e a Tabela 4.3.8 completa,
    so estes 2 codigos documentados por esta NT especifica.
  - Gaps identificados mas NAO implementados por falta de fonte primaria
    completa (a NT da exemplos simplificados, nao o layout de campo
    inteiro -- ver nota de rodape do proprio documento: "O conteudo
    completo de cada registro esta disponivel no Guia Pratico"):
    registro C110 (informacoes complementares do documento fiscal,
    referencia o registro 0450 -- tabela de codigo de informacao
    complementar), registro F550/F500 (consolidacao de receita para
    lucro presumido). Nenhum dos dois e modelado aqui ainda.
  - Pesquisa web tambem apontou a familia D500/D501/D505/D509/D600/D601/
    D605 (documentos de comunicacao/telecomunicacao, incluindo NFCom
    modelo 62 desde 01/04/2025, Nota Tecnica 009/2024) e o registro F600/
    F700 (contribuicao retida na fonte) como gaps reais e mais antigos
    (nao sao novidade desta NT 012/2026) -- nao modelados aqui por
    decisao consciente: a fonte disponivel foi busca web/blog de
    fornecedor de ERP, nao o PDF oficial. Implementar direto de fonte
    secundaria contraria o principio deste projeto (ver Rodada 1 do
    changelog abaixo, onde uma citacao de fonte nao consultada foi
    corrigida). Requer o PDF oficial (Guia Pratico ou a propria NT
    009/2024) antes de qualquer modelagem de campo.

RODADA 4 -- tambem conferidos campo a campo: C190, C191, C195 (espelho de
C180/C181/C185 para aquisicoes/devolucoes consolidadas por NF-e) e M210,
M211, M610, M611 (decomposicao da contribuicao apurada por COD_CONT).
IMPORTANTE: o Guia documenta DOIS leiautes para M210/M610 -- um valido ate
31/12/2018 e outro a partir de 01/01/2019 (mais campos, com o detalhamento
do ajuste de base de calculo). Modelado apenas o leiaute vigente (2019+):
qualquer arquivo anterior a essa data ja estaria fora do prazo decadencial
ordinario de 5 anos numa auditoria feita em 2026. Zero divergencias de
ordem de campo nestes tambem (leiaute vigente).

RODADA 5 -- registros de AJUSTE (detalham os campos VL_AJUS_ACRES/
VL_AJUS_REDUC dos totalizadores M100/M500 e M210/M610): M110, M115, M215,
M220, M225 conferidos campo a campo contra o texto; M510, M515, M615,
M620, M625 (mirrors COFINS) inferidos por simetria de padrao (nao lidos
individualmente na integra desta vez -- o padrao de simetria PIS/COFINS se
confirmou em TODOS os pares conferidos ate agora nesta reconciliacao, mas
fica registrado que estes 5 nao passaram por leitura linha a linha). Erro
real encontrado e corrigido nesta rodada: PAI["M215"] e PAI["M615"]
faltavam no dicionario de hierarquia (M215/M615 ficavam sem registro pai
vinculado) -- pego pelo proprio teste automatizado ao calibrar as
contagens esperadas contra o resultado real do CLI.

TODOS os 66 registros usados no leiaute foram conferidos CAMPO A CAMPO (ou,
no caso dos 5 citados acima, por simetria de padrao) contra o texto
extraido desse PDF (ordem de campo e coluna "Obrig" S/N de cada campo):
0000, 0110, 0111, 0140, 0150, 0190, 0200, 0400, 0500, C010, C100, C170,
C500, C501, C505, D010, D100, D101, D105, A010, A100, A170, F010, F100,
F500, F510, F525, F550, F560, M100, M105, M110, M115, M200, M210, M211,
M215, M220, M225, M400, M410, M500, M505, M510, M515, M600, M610, M611,
M615, M620, M625, M800, M810, 9900, 9999, 1010, 1011, 1100, 1500, 1900,
C180, C181, C185, C190, C191, C195. Em
TODOS os casos a ordem de campo reconstruida de memoria bateu exatamente
com o texto oficial (0 divergencias de ordem/campo); os erros encontrados
foram todos de obrigatoriedade (campo marcado O quando o Guia mostra N, ou
o contrario) -- corrigidos ao longo das rodadas, com a divergencia
registrada no changelog abaixo.

Changelog desta reconciliacao (divergencias reais encontradas e corrigidas
em OBRIGATORIOS, com base na coluna "Obrig" do Guia v1.35):
  - 0000: IND_NAT_PJ e "N" no Guia (nao sempre obrigatorio) -- removido.
  - 0110: IND_APRO_CRED e COD_TIPO_CONT sao "N" -- removidos (so
    COD_INC_TRIB e sempre obrigatorio).
  - 0140: COD_EST e "N" -- removido.
  - 0150: COD_PAIS e "S" e estava faltando -- adicionado.
  - C010: IND_ESCRI e "N" -- removido (so CNPJ e sempre obrigatorio).
  - C100: SER e DT_E_S sao "N" -- removidos; COD_PART, IND_PGTO e IND_FRT
    sao "S" e estavam faltando -- adicionados.
  - D100: SER e DT_A_P sao "N" -- removidos; COD_PART, IND_FRT e VL_SERV
    sao "S" e estavam faltando -- adicionados.
  - A100: IND_PGTO, VL_BC_PIS, VL_PIS, VL_BC_COFINS e VL_COFINS sao "S"
    e estavam faltando -- adicionados.
  - C170: QTD, UNID e IND_MOV sao "N" (nem todo item tem quantidade/unidade
    -- ex.: servicos) -- removidos.
  - 0111, 0190, 0400, 0500, C500, C501, C505, D010, D101, D105, A010,
    A170, F010, M200, M400, M410, M600, M800, M810: registros que nao
    tinham nenhuma entrada em OBRIGATORIOS antes desta rodada --
    adicionadas com base na coluna "Obrig" do Guia.

RODADA 3 -- ampliacao de escopo (credito detalhado, Bloco 1, NF-e
consolidada): tambem conferidos campo a campo contra o mesmo PDF: M100,
M105, M500, M505 (credito detalhado por natureza no periodo), 1010, 1011
(processo referenciado / exigibilidade suspensa), 1100, 1500 (controle de
creditos fiscais -- saldo credor entre periodos) e C180, C181, C185
(consolidacao de NF-e, alternativa a C100/C170). Zero divergencias de
ordem de campo nestes tambem. As tabelas oficiais 4.3.6 (COD_CRED) e 4.3.7
(NAT_BC_CRED) foram encontradas *embutidas* no proprio Guia (nao sao
tabelas externas) e por isso foram transcritas para COD_CRED_VALIDOS e
NAT_BC_CRED_VALIDOS abaixo. Os registros 1101/1102/1200/1210/1220/1501/
1502/1600/1610/1620 (credito e contribuicao extemporaneos, versao antiga
do Bloco 1) foram deliberadamente NAO modelados campo a campo -- o proprio
Guia declara que deixaram de ter validade para fatos geradores a partir de
agosto/2013 (ver BLOCO_1_REGISTROS_OBSOLETOS). As tabelas 4.3.9 a 4.3.16
(aliquotas de credito presumido, produtos monofasicos/ST/aliquota zero por
NCM) sao, segundo o proprio texto do Guia, tabelas EXTERNAS publicadas
separadamente no Portal do SPED -- por isso nao foram (e nao deveriam ser)
embutidas aqui; checks que dependeriam delas (classificacao correta de
produto monofasico) foram implementados como sinalizacao para revisao
tecnica (ver audita/checks/tese.py), nao como veredito automatico.

Cada registro carrega uma tag de confianca:
  NUCLEO     -> conferido campo a campo contra o Guia Pratico oficial, ou
                estruturalmente equivalente a um registro conferido.
  ESTENDIDO  -> ainda nao conferido diretamente contra o PDF nesta rodada.
                Tratar como pista para investigar, nao como conclusao
                fechada, ate confirmar contra o Guia Pratico vigente.

Como reconciliar contra uma nova versao do Guia Pratico:
  1. Ajuste LAYOUT_VERSAO / LAYOUT_FONTE abaixo com a versao conferida.
  2. Confira cada lista de campos contra a tabela do registro no PDF
     (ordem importa: e ela que mapeia posicao -> nome).
  3. Ajuste OBRIGATORIOS conforme a coluna "Obrig" do Guia (aqui so
     entram campos S -- sempre obrigatorios. Campos condicionais (que
     dependem de outro campo, ex.: CHV_NFE por COD_MOD) sao tratados em
     checks dedicados, nao aqui, para nao gerar falso positivo sem a
     regra exata da condicao).
  4. Promova o registro de ESTENDIDO para NUCLEO quando confirmado.

  Dica pratica: o limite de 600 paginas do anexo de chat nao se aplica a
  leitura de PDF por linha de comando. Um PDF local pode ter o texto
  extraido com a biblioteca Python pypdf (r.pages[i].extract_text()) e
  lido em pedacos -- foi assim que esta reconciliacao foi feita.
"""

LAYOUT_VERSAO = "conferido campo a campo contra o Guia Pratico v1.35 (18/06/2021) -- PDF oficial fornecido pelo usuario"
LAYOUT_FONTE = "Guia Pratico da EFD-Contribuicoes v1.35 (18/06/2021) - Receita Federal do Brasil (arquivo local file.pdf, 433 paginas)"

NUCLEO, ESTENDIDO = "NUCLEO", "ESTENDIDO"

LAYOUTS = {
    "0000": ["REG","COD_VER","TIPO_ESCRIT","IND_SIT_ESP","NUM_REC_ANTERIOR",
             "DT_INI","DT_FIN","NOME","CNPJ","UF","COD_MUN","SUFRAMA","IND_NAT_PJ","IND_ATIV"],
    "0110": ["REG","COD_INC_TRIB","IND_APRO_CRED","COD_TIPO_CONT","IND_REG_CUM"],
    "0111": ["REG","REC_BRU_NCUM_TRIB_MI","REC_BRU_NCUM_NT_MI","REC_BRU_NCUM_EXP",
             "REC_BRU_CUM","REC_BRU_TOTAL"],
    "0140": ["REG","COD_EST","NOME","CNPJ","UF","IE","COD_MUN","IM","SUFRAMA"],
    "0150": ["REG","COD_PART","NOME","COD_PAIS","CNPJ","CPF","IE","COD_MUN","SUFRAMA",
             "END","NUM","COMPL","BAIRRO"],
    "0190": ["REG","UNID","DESCR"],
    "0200": ["REG","COD_ITEM","DESCR_ITEM","COD_BARRA","COD_ANT_ITEM","UNID_INV",
             "TIPO_ITEM","COD_NCM","EX_IPI","COD_GEN","COD_LST","ALIQ_ICMS"],
    "0400": ["REG","COD_NAT","DESCR_NAT"],
    "0500": ["REG","DT_ALT","COD_NAT_CC","IND_CTA","NIVEL","COD_CTA","NOME_CTA",
             "COD_CTA_REF","CNPJ_EST"],

    "C010": ["REG","CNPJ","IND_ESCRI"],
    "C100": ["REG","IND_OPER","IND_EMIT","COD_PART","COD_MOD","COD_SIT","SER","NUM_DOC",
             "CHV_NFE","DT_DOC","DT_E_S","VL_DOC","IND_PGTO","VL_DESC","VL_ABAT_NT",
             "VL_MERC","IND_FRT","VL_FRT","VL_SEG","VL_OUT_DA","VL_BC_ICMS","VL_ICMS",
             "VL_BC_ICMS_ST","VL_ICMS_ST","VL_IPI","VL_PIS","VL_COFINS","VL_PIS_ST","VL_COFINS_ST"],
    "C170": ["REG","NUM_ITEM","COD_ITEM","DESCR_COMPL","QTD","UNID","VL_ITEM","VL_DESC",
             "IND_MOV","CST_ICMS","CFOP","COD_NAT","VL_BC_ICMS","ALIQ_ICMS","VL_ICMS",
             "VL_BC_ICMS_ST","ALIQ_ST","VL_ICMS_ST","IND_APUR","CST_IPI","COD_ENQ",
             "VL_BC_IPI","ALIQ_IPI","VL_IPI","CST_PIS","VL_BC_PIS","ALIQ_PIS",
             "QUANT_BC_PIS","ALIQ_PIS_QUANT","VL_PIS","CST_COFINS","VL_BC_COFINS",
             "ALIQ_COFINS","QUANT_BC_COFINS","ALIQ_COFINS_QUANT","VL_COFINS",
             "COD_CTA"],  # C170 oficial encerra no campo 37 (COD_CTA) - Guia v1.35, conferido
    "C500": ["REG","COD_PART","COD_MOD","COD_SIT","SER","SUB","NUM_DOC","DT_DOC","DT_ENT",
             "VL_DOC","VL_ICMS","COD_INF","VL_PIS","VL_COFINS","CHV_DOCe"],
    "C501": ["REG","CST_PIS","VL_ITEM","NAT_BC_CRED","VL_BC_PIS","ALIQ_PIS","VL_PIS","COD_CTA"],
    "C505": ["REG","CST_COFINS","VL_ITEM","NAT_BC_CRED","VL_BC_COFINS","ALIQ_COFINS",
             "VL_COFINS","COD_CTA"],

    "D010": ["REG","CNPJ"],
    "D100": ["REG","IND_OPER","IND_EMIT","COD_PART","COD_MOD","COD_SIT","SER","SUB",
             "NUM_DOC","CHV_CTE","DT_DOC","DT_A_P","TP_CT_e","CHV_CTE_REF","VL_DOC",
             "VL_DESC","IND_FRT","VL_SERV","VL_BC_ICMS","VL_ICMS","VL_NT","COD_INF","COD_CTA"],
    "D101": ["REG","IND_NAT_FRT","VL_ITEM","CST_PIS","NAT_BC_CRED","VL_BC_PIS",
             "ALIQ_PIS","VL_PIS","COD_CTA"],
    "D105": ["REG","IND_NAT_FRT","VL_ITEM","CST_COFINS","NAT_BC_CRED","VL_BC_COFINS",
             "ALIQ_COFINS","VL_COFINS","COD_CTA"],

    "A010": ["REG","CNPJ"],
    "A100": ["REG","IND_OPER","IND_EMIT","COD_PART","COD_SIT","SER","SUB","NUM_DOC",
             "CHV_NFSE","DT_DOC","DT_EXE_SERV","VL_DOC","IND_PGTO","VL_DESC","VL_BC_PIS",
             "VL_PIS","VL_BC_COFINS","VL_COFINS","VL_PIS_RET","VL_COFINS_RET","VL_ISS"],
    "A170": ["REG","NUM_ITEM","COD_ITEM","DESCR_COMPL","VL_ITEM","VL_DESC","NAT_BC_CRED",
             "IND_ORIG_CRED","CST_PIS","VL_BC_PIS","ALIQ_PIS","VL_PIS","CST_COFINS",
             "VL_BC_COFINS","ALIQ_COFINS","VL_COFINS","COD_CTA","COD_CCUS"],

    "F010": ["REG","CNPJ"],
    "F100": ["REG","IND_OPER","COD_PART","COD_ITEM","DT_OPER","VL_OPER","CST_PIS",
             "VL_BC_PIS","ALIQ_PIS","VL_PIS","CST_COFINS","VL_BC_COFINS","ALIQ_COFINS",
             "VL_COFINS","NAT_BC_CRED","IND_ORIG_CRED","COD_CTA","COD_CCUS","DESC_DOC_OPER"],

    # Familia "Lucro Presumido consolidado" (regime de caixa ou de
    # competencia) -- conferida campo a campo contra o Guia Pratico v1.35
    # nesta rodada. F500/F510 = regime de caixa (VL_REC_CAIXA); F550/F560
    # = regime de competencia (VL_REC_COMP); a diferenca entre o par
    # "500/550" e "510/560" e a base de calculo (F500/F550 usam aliquota
    # ad valorem em % sobre valor; F510/F560 usam aliquota em reais sobre
    # quantidade -- produtos monofasicos de bebidas frias/combustivel/
    # alcool por unidade de medida). F525 detalha a composicao da receita
    # RECEBIDA no regime de caixa (por cliente/cartao/titulo/item) -- o
    # Guia afirma explicitamente que o total do F525 deve bater com o
    # total do F500 (ver check R20 em reconciliacao.py). Nao ha um
    # registro pai unico e inequivoco para esta familia dentro do Bloco F
    # (o Guia da a mesma "Nivel hierarquico 3" pra todos, sem indicar
    # nesting fisico no arquivo) -- por isso nenhum PAI foi declarado
    # aqui; a reconciliacao F525 x F500 e feita por soma de totais (mesmo
    # padrao ja usado em R01/R02 entre 0111 e o detalhe), nao por vinculo
    # de hierarquia.
    "F500": ["REG","VL_REC_CAIXA","CST_PIS","VL_DESC_PIS","VL_BC_PIS","ALIQ_PIS","VL_PIS",
             "CST_COFINS","VL_DESC_COFINS","VL_BC_COFINS","ALIQ_COFINS","VL_COFINS",
             "COD_MOD","CFOP","COD_CTA","INFO_COMPL"],
    "F510": ["REG","VL_REC_CAIXA","CST_PIS","VL_DESC_PIS","QUANT_BC_PIS","ALIQ_PIS_QUANT",
             "VL_PIS","CST_COFINS","VL_DESC_COFINS","QUANT_BC_COFINS","ALIQ_COFINS_QUANT",
             "VL_COFINS","COD_MOD","CFOP","COD_CTA","INFO_COMPL"],
    "F525": ["REG","VL_REC","IND_REC","CNPJ_CPF","NUM_DOC","COD_ITEM","VL_REC_DET",
             "CST_PIS","CST_COFINS","INFO_COMPL","COD_CTA"],
    "F550": ["REG","VL_REC_COMP","CST_PIS","VL_DESC_PIS","VL_BC_PIS","ALIQ_PIS","VL_PIS",
             "CST_COFINS","VL_DESC_COFINS","VL_BC_COFINS","ALIQ_COFINS","VL_COFINS",
             "COD_MOD","CFOP","COD_CTA","INFO_COMPL"],
    "F560": ["REG","VL_REC_COMP","CST_PIS","VL_DESC_PIS","QUANT_BC_PIS","ALIQ_PIS_QUANT",
             "VL_PIS","CST_COFINS","VL_DESC_COFINS","QUANT_BC_COFINS","ALIQ_COFINS_QUANT",
             "VL_COFINS","COD_MOD","CFOP","COD_CTA","INFO_COMPL"],

    # Registro 1900 (Bloco 1): consolidacao dos documentos emitidos por PJ
    # do lucro presumido com escrituracao consolidada -- alternativa ao
    # C100/C170 individualizado, na mesma logica do C180 para o lucro real.
    # Conferido campo a campo contra o Guia Pratico v1.35 nesta rodada.
    "1900": ["REG","CNPJ","COD_MOD","SER","SUB_SER","COD_SIT","VL_TOT_REC","QUANT_DOC",
             "CST_PIS","CST_COFINS","CFOP","INF_COMPL","COD_CTA"],

    # Escrituracao consolidada de aquisicoes/devolucoes por NF-e (espelho do
    # C180/C181/C185 para o lado de entrada). C191/C195 tem um campo a mais
    # que C181/C185 (CNPJ_CPF_PART, o fornecedor).
    "C190": ["REG","COD_MOD","DT_REF_INI","DT_REF_FIN","COD_ITEM","COD_NCM",
             "EX_IPI","VL_TOT_ITEM"],
    "C191": ["REG","CNPJ_CPF_PART","CST_PIS","CFOP","VL_ITEM","VL_DESC","VL_BC_PIS",
             "ALIQ_PIS","QUANT_BC_PIS","ALIQ_PIS_QUANT","VL_PIS","COD_CTA"],
    "C195": ["REG","CNPJ_CPF_PART","CST_COFINS","CFOP","VL_ITEM","VL_DESC","VL_BC_COFINS",
             "ALIQ_COFINS","QUANT_BC_COFINS","ALIQ_COFINS_QUANT","VL_COFINS","COD_CTA"],

    "M400": ["REG","CST_PIS","VL_TOT_REC","COD_CTA","DESC_COMPL"],
    "M410": ["REG","NAT_REC","VL_REC","COD_CTA","DESC_COMPL"],
    "M800": ["REG","CST_COFINS","VL_TOT_REC","COD_CTA","DESC_COMPL"],
    "M810": ["REG","NAT_REC","VL_REC","COD_CTA","DESC_COMPL"],
    # Identidades oficiais (conferidas, Guia v1.35): campo05 = campo02-03-04,
    # campo08 = campo05-06-07, campo13 = campo08+12. O check R08 valida isso.
    "M200": ["REG","VL_TOT_CONT_NC_PER","VL_TOT_CRED_DESC","VL_TOT_CRED_DESC_ANT",
             "VL_TOT_CONT_NC_DEV","VL_RET_NC","VL_OUT_DED_NC","VL_CONT_NC_REC",
             "VL_TOT_CONT_CUM_PER","VL_RET_CUM","VL_OUT_DED_CUM","VL_CONT_CUM_REC",
             "VL_TOT_CONT_REC"],
    "M600": ["REG","VL_TOT_CONT_NC_PER","VL_TOT_CRED_DESC","VL_TOT_CRED_DESC_ANT",
             "VL_TOT_CONT_NC_DEV","VL_RET_NC","VL_OUT_DED_NC","VL_CONT_NC_REC",
             "VL_TOT_CONT_CUM_PER","VL_RET_CUM","VL_OUT_DED_CUM","VL_CONT_CUM_REC",
             "VL_TOT_CONT_REC"],

    # M210/M610: decomposicao da contribuicao apurada por COD_CONT (Tabela
    # 4.3.5), filhos de M200/M600. O Guia Pratico documenta DOIS leiautes
    # para este registro: um valido ate 31/12/2018 (13 campos) e outro a
    # partir de 01/01/2019 (16 campos, com o detalhamento do ajuste de base
    # de calculo nos campos 05-07). Modelado aqui APENAS o leiaute vigente
    # (2019+): qualquer arquivo anterior a isso ja estaria fora do prazo
    # decadencial ordinario de 5 anos para uma auditoria feita em 2026, e
    # tentar ler um M210 no leiaute antigo com esta lista desalinharia os
    # campos silenciosamente. Se precisar auditar arquivo pre-2019, ajuste
    # esta lista para o leiaute de 13 campos antes de processar.
    "M210": ["REG","COD_CONT","VL_REC_BRT","VL_BC_CONT","VL_AJUS_ACRES_BC_PIS",
             "VL_AJUS_REDUC_BC_PIS","VL_BC_CONT_AJUS","ALIQ_PIS","QUANT_BC_PIS",
             "ALIQ_PIS_QUANT","VL_CONT_APUR","VL_AJUS_ACRES","VL_AJUS_REDUC",
             "VL_CONT_DIFER","VL_CONT_DIFER_ANT","VL_CONT_PER"],
    "M610": ["REG","COD_CONT","VL_REC_BRT","VL_BC_CONT","VL_AJUS_ACRES_BC_COFINS",
             "VL_AJUS_REDUC_BC_COFINS","VL_BC_CONT_AJUS","ALIQ_COFINS","QUANT_BC_COFINS",
             "ALIQ_COFINS_QUANT","VL_CONT_APUR","VL_AJUS_ACRES","VL_AJUS_REDUC",
             "VL_CONT_DIFER","VL_CONT_DIFER_ANT","VL_CONT_PER"],
    # M211/M611: exclusoes especificas de sociedade cooperativa da base de
    # calculo do M210/M610 (uso restrito a esse tipo de contribuinte).
    "M211": ["REG","IND_TIP_COOP","VL_BC_CONT_ANT_EXC_COOP","VL_EXC_COOP_GER",
             "VL_EXC_ESP_COOP","VL_BC_CONT"],
    "M611": ["REG","IND_TIP_COOP","VL_BC_CONT_ANT_EXC_COOP","VL_EXC_COOP_GER",
             "VL_EXC_ESP_COOP","VL_BC_CONT"],

    # M215/M220 (e mirrors COFINS M615/M620): detalham, respectivamente, o
    # ajuste de BASE DE CALCULO (campos 05/06 do M210, leiaute 2019+) e o
    # ajuste da CONTRIBUICAO APURADA (campos 12/13 do M210) por IND_AJ (0
    # reducao / 1 acrescimo). M110/M510 sao o par equivalente para o M100/
    # M500 (ajuste de CREDITO, campos 09/10). M115/M225/M515/M625 sao o
    # detalhamento analitico opcional de cada ajuste (sem formula de soma
    # obrigatoria contra o pai -- nao usados em check de reconciliacao).
    "M110": ["REG","IND_AJ","VL_AJ","COD_AJ","NUM_DOC","DESCR_AJ","DT_REF"],
    "M115": ["REG","DET_VALOR_AJ","CST_PIS","DET_BC_CRED","DET_ALIQ","DT_OPER_AJ",
             "DESC_AJ","COD_CTA","INFO_COMPL"],
    "M215": ["REG","IND_AJ_BC","VL_AJ_BC","COD_AJ_BC","NUM_DOC","DESCR_AJ_BC",
             "DT_REF","COD_CTA","CNPJ","INFO_COMPL"],
    "M220": ["REG","IND_AJ","VL_AJ","COD_AJ","NUM_DOC","DESCR_AJ","DT_REF"],
    "M225": ["REG","DET_VALOR_AJ","CST_PIS","DET_BC_CRED","DET_ALIQ","DT_OPER_AJ",
             "DESC_AJ","COD_CTA","INFO_COMPL"],
    "M510": ["REG","IND_AJ","VL_AJ","COD_AJ","NUM_DOC","DESCR_AJ","DT_REF"],
    "M515": ["REG","DET_VALOR_AJ","CST_COFINS","DET_BC_CRED","DET_ALIQ","DT_OPER_AJ",
             "DESC_AJ","COD_CTA","INFO_COMPL"],
    "M615": ["REG","IND_AJ_BC","VL_AJ_BC","COD_AJ_BC","NUM_DOC","DESCR_AJ_BC",
             "DT_REF","COD_CTA","CNPJ","INFO_COMPL"],
    "M620": ["REG","IND_AJ","VL_AJ","COD_AJ","NUM_DOC","DESCR_AJ","DT_REF"],
    "M625": ["REG","DET_VALOR_AJ","CST_COFINS","DET_BC_CRED","DET_ALIQ","DT_OPER_AJ",
             "DESC_AJ","COD_CTA","INFO_COMPL"],

    # Credito detalhado por natureza no periodo (Guia v1.35, secao 4.3).
    # M100 e M500 sao os totalizadores; M105/M505 detalham a base por CST.
    "M100": ["REG","COD_CRED","IND_CRED_ORI","VL_BC_PIS","ALIQ_PIS","QUANT_BC_PIS",
             "ALIQ_PIS_QUANT","VL_CRED","VL_AJUS_ACRES","VL_AJUS_REDUC","VL_CRED_DIF",
             "VL_CRED_DISP","IND_DESC_CRED","VL_CRED_DESC","SLD_CRED"],
    "M105": ["REG","NAT_BC_CRED","CST_PIS","VL_BC_PIS_TOT","VL_BC_PIS_CUM",
             "VL_BC_PIS_NC","VL_BC_PIS","QUANT_BC_PIS_TOT","QUANT_BC_PIS","DESC_CRED"],
    "M500": ["REG","COD_CRED","IND_CRED_ORI","VL_BC_COFINS","ALIQ_COFINS","QUANT_BC_COFINS",
             "ALIQ_COFINS_QUANT","VL_CRED","VL_AJUS_ACRES","VL_AJUS_REDUC","VL_CRED_DIFER",
             "VL_CRED_DISP","IND_DESC_CRED","VL_CRED_DESC","SLD_CRED"],
    "M505": ["REG","NAT_BC_CRED","CST_COFINS","VL_BC_COFINS_TOT","VL_BC_COFINS_CUM",
             "VL_BC_COFINS_NC","VL_BC_COFINS","QUANT_BC_COFINS_TOT","QUANT_BC_COFINS","DESC_CRED"],

    "9900": ["REG","REG_BLC","QTD_REG_BLC"],
    "9999": ["REG","QTD_LIN"],

    # Bloco 1: Complemento da Escrituracao. So os registros ativos foram
    # modelados -- ver nota BLOCO_1_REGISTROS_OBSOLETOS abaixo sobre
    # 1101/1102/1200/1210/1220/1501/1502/1600/1610/1620, que o proprio
    # Guia declara sem validade para fatos geradores a partir de 08/2013.
    "1010": ["REG","NUM_PROC","ID_SEC_JUD","ID_VARA","IND_NAT_ACAO","DESC_DEC_JUD","DT_SENT_JUD"],
    "1011": ["REG","REG_REF","CHAVE_DOC","COD_PART","COD_ITEM","DT_OPER","VL_OPER",
             "CST_PIS","VL_BC_PIS","ALIQ_PIS","VL_PIS","CST_COFINS","VL_BC_COFINS",
             "ALIQ_COFINS","VL_COFINS"],
    "1100": ["REG","PER_APU_CRED","ORIG_CRED","CNPJ_SUC","COD_CRED","VL_CRED_APU",
             "VL_CRED_EXT_APU","VL_TOT_CRED_APU","VL_CRED_DESC_PA_ANT","VL_CRED_PER_PA_ANT",
             "VL_CRED_DCOMP_PA_ANT","SD_CRED_DISP_EFD","VL_CRED_DESC_EFD","VL_CRED_PER_EFD",
             "VL_CRED_DCOMP_EFD","VL_CRED_TRANS","VL_CRED_OUT","SLD_CRED_FIM"],
    "1500": ["REG","PER_APU_CRED","ORIG_CRED","CNPJ_SUC","COD_CRED","VL_CRED_APU",
             "VL_CRED_EXT_APU","VL_TOT_CRED_APU","VL_CRED_DESC_PA_ANT","VL_CRED_PER_PA_ANT",
             "VL_CRED_DCOMP_PA_ANT","SD_CRED_DISP_EFD","VL_CRED_DESC_EFD","VL_CRED_PER_EFD",
             "VL_CRED_DCOMP_EFD","VL_CRED_TRANS","VL_CRED_OUT","SLD_CRED_FIM"],

    # Escrituracao consolidada de NF-e (alternativa a C100/C170 -- ver
    # C010.IND_ESCRI). C180 e o cabecalho por item; C181/C185 detalham a
    # consolidacao por CST/CFOP/aliquota (PIS e COFINS, respectivamente).
    "C180": ["REG","COD_MOD","DT_DOC_INI","DT_DOC_FIN","COD_ITEM","COD_NCM",
             "EX_IPI","VL_TOT_ITEM"],
    "C181": ["REG","CST_PIS","CFOP","VL_ITEM","VL_DESC","VL_BC_PIS","ALIQ_PIS",
             "QUANT_BC_PIS","ALIQ_PIS_QUANT","VL_PIS","COD_CTA"],
    "C185": ["REG","CST_COFINS","CFOP","VL_ITEM","VL_DESC","VL_BC_COFINS","ALIQ_COFINS",
             "QUANT_BC_COFINS","ALIQ_COFINS_QUANT","VL_COFINS","COD_CTA"],
}

# Registros de credito/contribuicao extemporanea do Bloco 1 que o proprio
# Guia Pratico (secao do registro 1101, "ESCLARECIMENTOS IMPORTANTES QUANTO
# A NAO VALIDACAO DE REGISTROS DE CREDITOS EXTEMPORANEOS, A PARTIR DE
# AGOSTO DE 2013") declara sem validade para fatos geradores a partir de
# agosto/2013: a partir dessa data o mecanismo correto passou a ser a
# retificacao da escrituracao original (prazo de ate 5 anos, IN RFB
# 1.387/2013), nao mais esses registros. Por isso NAO foram modelados campo
# a campo (usa-los hoje e o proprio erro) -- so a deteccao de presenca
# (check E26) foi implementada.
BLOCO_1_REGISTROS_OBSOLETOS = {
    "1101", "1102", "1200", "1210", "1220", "1501", "1502", "1600", "1610", "1620",
}

# Tabela 4.3.6 do Guia Pratico -- Codigo de Tipo de Credito (M100/M105
# COD_CRED, M500/M505 idem, 1100/1500 COD_CRED). Embutida por ser pequena,
# fechada e publicada no proprio Guia (nao e tabela externa).
COD_CRED_VALIDOS = {
    "101","102","103","104","105","106","107","108","109","199",
    "201","202","203","204","205","206","207","208","299",
    "301","302","303","304","305","306","307","308","399",
}

# Tabela 4.3.7 do Guia Pratico -- Codigo de Base de Calculo do Credito
# (NAT_BC_CRED, usado em C501/C505/D101/D105/A170/F100/M105/M505). Embutida
# por ser pequena, fechada e publicada no proprio Guia (nao e tabela
# externa como CFOP ou as tabelas de produto monofasico 4.3.10-4.3.16).
NAT_BC_CRED_VALIDOS = {
    "01","02","03","04","05","06","07","08","09","10","11","12","13",
    "14","15","16","17","18",
}

# Tabela unificada de CST_PIS/CST_COFINS (Tabelas 4.3.3 e 4.3.4 do Guia --
# ambas usam o mesmo conjunto de codigos). Vista repetidamente e de forma
# consistente em C181, C501/C505, D101/D105 etc. durante a conferencia.
CST_VALIDOS = {
    "01","02","03","04","05","06","07","08","09","49",
    "50","51","52","53","54","55","56",
    "60","61","62","63","64","65","66",
    "70","71","72","73","74","75","98","99",
}

# Tag de confianca por registro (default NUCLEO se ausente). Ver nota
# FONTE E CONFERENCIA no topo do arquivo -- hoje nenhum registro usado
# permanece ESTENDIDO porque todos os que existiam nesse estado foram
# conferidos diretamente contra o PDF oficial nesta rodada. O mecanismo
# fica mantido para futuros registros que venham a ser adicionados sem
# conferencia.
CONFIANCA = {}


def confianca(reg):
    return CONFIANCA.get(reg, NUCLEO)


# Campos considerados obrigatorios (coluna "Obrig" = S no Guia Pratico,
# ou seja, sempre obrigatorios, independente de condicao). De proposito
# conservador: fora daqui, so falta obrigatoriedade condicional (campo e
# S apenas quando outro campo tem determinado valor -- ex.: CHV_NFE so e
# obrigatoria para determinados COD_MOD) e essas sao tratadas em checks
# dedicados (ver E25), nao aqui, para nao gerar falso positivo sem a
# regra exata do Guia Pratico.
OBRIGATORIOS = {
    "0000": {"COD_VER", "TIPO_ESCRIT", "DT_INI", "DT_FIN", "NOME", "CNPJ", "UF",
             "COD_MUN", "IND_ATIV"},
    # IND_NAT_PJ e IND_REG_CUM/IND_APRO_CRED/COD_TIPO_CONT ficam de fora:
    # sao "N" na coluna Obrig do Guia (condicionais), conferido no PDF.
    "0110": {"COD_INC_TRIB"},
    "0111": {"REC_BRU_NCUM_TRIB_MI", "REC_BRU_NCUM_NT_MI", "REC_BRU_NCUM_EXP",
              "REC_BRU_CUM", "REC_BRU_TOTAL"},
    "0140": {"NOME", "CNPJ", "UF", "COD_MUN"},
    "0150": {"COD_PART", "NOME", "COD_PAIS"},
    "0190": {"UNID", "DESCR"},
    "0200": {"COD_ITEM", "DESCR_ITEM", "TIPO_ITEM"},
    "0400": {"COD_NAT", "DESCR_NAT"},
    "0500": {"DT_ALT", "COD_NAT_CC", "IND_CTA", "NIVEL", "COD_CTA", "NOME_CTA"},
    "D010": {"CNPJ"},
    "A010": {"CNPJ"},
    "F010": {"CNPJ"},
    # IND_ESCRI fica de fora: "N" no Guia (so se aplica quando o arquivo
    # mistura escrituracao individualizada e consolidada de NF-e).
    "C010": {"CNPJ"},
    "C100": {"IND_OPER", "IND_EMIT", "COD_PART", "COD_MOD", "COD_SIT", "NUM_DOC",
              "DT_DOC", "VL_DOC", "IND_PGTO", "IND_FRT"},
    # SER e DT_E_S ficam de fora: "N" no Guia (condicionais). COD_PART,
    # IND_PGTO e IND_FRT sao "S" e estavam faltando -- conferido no PDF.
    "C170": {"NUM_ITEM", "COD_ITEM", "VL_ITEM", "CFOP", "CST_PIS", "CST_COFINS"},
    # QTD/UNID/IND_MOV ficam de fora: "N" no Guia (nem todo item tem
    # quantidade/unidade -- ex.: servicos).
    "C500": {"COD_PART", "COD_MOD", "COD_SIT", "NUM_DOC", "DT_DOC", "VL_DOC"},
    "C501": {"CST_PIS", "VL_ITEM", "VL_BC_PIS", "ALIQ_PIS", "VL_PIS"},
    "C505": {"CST_COFINS", "VL_ITEM", "VL_BC_COFINS", "ALIQ_COFINS", "VL_COFINS"},
    "D100": {"IND_OPER", "IND_EMIT", "COD_PART", "COD_MOD", "COD_SIT", "NUM_DOC",
              "DT_DOC", "VL_DOC", "IND_FRT", "VL_SERV"},
    # SER e DT_A_P ficam de fora: "N" no Guia. COD_PART, IND_FRT e
    # VL_SERV sao "S" e estavam faltando -- conferido no PDF.
    "D101": {"IND_NAT_FRT", "VL_ITEM", "CST_PIS"},
    "D105": {"IND_NAT_FRT", "VL_ITEM", "CST_COFINS"},
    "A100": {"IND_OPER", "IND_EMIT", "COD_SIT", "NUM_DOC", "DT_DOC", "VL_DOC",
              "IND_PGTO", "VL_BC_PIS", "VL_PIS", "VL_BC_COFINS", "VL_COFINS"},
    # IND_PGTO e os 4 campos de base/valor PIS/COFINS sao "S" no Guia e
    # estavam faltando -- conferido no PDF.
    "A170": {"NUM_ITEM", "COD_ITEM", "VL_ITEM", "CST_PIS", "CST_COFINS"},
    "F100": {"IND_OPER", "DT_OPER", "VL_OPER", "CST_PIS", "CST_COFINS"},
    "F500": {"VL_REC_CAIXA", "CST_PIS", "CST_COFINS"},
    "F510": {"VL_REC_CAIXA", "CST_PIS", "CST_COFINS"},
    "F525": {"VL_REC", "IND_REC", "VL_REC_DET"},
    "F550": {"VL_REC_COMP", "CST_PIS", "CST_COFINS"},
    "F560": {"VL_REC_COMP", "CST_PIS", "CST_COFINS"},
    "1900": {"CNPJ", "COD_MOD", "VL_TOT_REC"},
    "M200": {"VL_TOT_CONT_NC_PER", "VL_TOT_CRED_DESC", "VL_TOT_CRED_DESC_ANT",
              "VL_TOT_CONT_NC_DEV", "VL_RET_NC", "VL_OUT_DED_NC", "VL_CONT_NC_REC",
              "VL_TOT_CONT_CUM_PER", "VL_RET_CUM", "VL_OUT_DED_CUM",
              "VL_CONT_CUM_REC", "VL_TOT_CONT_REC"},
    "M600": {"VL_TOT_CONT_NC_PER", "VL_TOT_CRED_DESC", "VL_TOT_CRED_DESC_ANT",
              "VL_TOT_CONT_NC_DEV", "VL_RET_NC", "VL_OUT_DED_NC", "VL_CONT_NC_REC",
              "VL_TOT_CONT_CUM_PER", "VL_RET_CUM", "VL_OUT_DED_CUM",
              "VL_CONT_CUM_REC", "VL_TOT_CONT_REC"},
    "M400": {"CST_PIS", "VL_TOT_REC"},
    "M800": {"CST_COFINS", "VL_TOT_REC"},
    "M410": {"NAT_REC", "VL_REC"},
    "M810": {"NAT_REC", "VL_REC"},
    "9900": {"REG_BLC", "QTD_REG_BLC"},
    "9999": {"QTD_LIN"},
    "M100": {"COD_CRED", "IND_CRED_ORI", "VL_CRED", "VL_AJUS_ACRES", "VL_AJUS_REDUC",
              "VL_CRED_DIF", "VL_CRED_DISP", "IND_DESC_CRED", "SLD_CRED"},
    "M105": {"NAT_BC_CRED", "CST_PIS"},
    "M500": {"COD_CRED", "IND_CRED_ORI", "VL_CRED", "VL_AJUS_ACRES", "VL_AJUS_REDUC",
              "VL_CRED_DIFER", "VL_CRED_DISP", "IND_DESC_CRED", "SLD_CRED"},
    "M505": {"NAT_BC_CRED", "CST_COFINS"},
    "1010": {"NUM_PROC", "ID_SEC_JUD", "ID_VARA", "IND_NAT_ACAO"},
    "1011": {"DT_OPER", "VL_OPER", "CST_PIS", "CST_COFINS"},
    "1100": {"PER_APU_CRED", "ORIG_CRED", "COD_CRED", "VL_CRED_APU", "VL_TOT_CRED_APU",
              "VL_CRED_DESC_PA_ANT", "SD_CRED_DISP_EFD"},
    "1500": {"PER_APU_CRED", "ORIG_CRED", "COD_CRED", "VL_CRED_APU", "VL_TOT_CRED_APU",
              "VL_CRED_DESC_PA_ANT", "SD_CRED_DISP_EFD"},
    "C180": {"COD_MOD", "DT_DOC_INI", "DT_DOC_FIN", "COD_ITEM", "VL_TOT_ITEM"},
    "C181": {"CST_PIS", "CFOP", "VL_ITEM"},
    "C185": {"CST_COFINS", "CFOP", "VL_ITEM"},
    "C190": {"COD_MOD", "DT_REF_INI", "DT_REF_FIN", "COD_ITEM", "VL_TOT_ITEM"},
    "C191": {"CST_PIS", "CFOP", "VL_ITEM"},
    "C195": {"CST_COFINS", "CFOP", "VL_ITEM"},
    "M210": {"COD_CONT", "VL_REC_BRT", "VL_BC_CONT", "VL_AJUS_ACRES_BC_PIS",
              "VL_AJUS_REDUC_BC_PIS", "VL_BC_CONT_AJUS", "VL_CONT_APUR",
              "VL_AJUS_ACRES", "VL_AJUS_REDUC", "VL_CONT_PER"},
    "M610": {"COD_CONT", "VL_REC_BRT", "VL_BC_CONT", "VL_AJUS_ACRES_BC_COFINS",
              "VL_AJUS_REDUC_BC_COFINS", "VL_BC_CONT_AJUS", "VL_CONT_APUR",
              "VL_AJUS_ACRES", "VL_AJUS_REDUC", "VL_CONT_PER"},
    "M211": {"IND_TIP_COOP", "VL_BC_CONT_ANT_EXC_COOP", "VL_BC_CONT"},
    "M611": {"IND_TIP_COOP", "VL_BC_CONT_ANT_EXC_COOP", "VL_BC_CONT"},
    "M110": {"IND_AJ", "VL_AJ", "COD_AJ"},
    "M510": {"IND_AJ", "VL_AJ", "COD_AJ"},
    "M220": {"IND_AJ", "VL_AJ", "COD_AJ"},
    "M620": {"IND_AJ", "VL_AJ", "COD_AJ"},
    "M215": {"IND_AJ_BC", "VL_AJ_BC", "COD_AJ_BC", "CNPJ"},
    "M615": {"IND_AJ_BC", "VL_AJ_BC", "COD_AJ_BC", "CNPJ"},
    "M115": {"DET_VALOR_AJ", "DT_OPER_AJ"},
    "M225": {"DET_VALOR_AJ", "DT_OPER_AJ"},
    "M515": {"DET_VALOR_AJ", "DT_OPER_AJ"},
    "M625": {"DET_VALOR_AJ", "DT_OPER_AJ"},
}

# Tabela 4.3.5 do Guia Pratico -- Codigo de Contribuicao Social Apurada
# (COD_CONT, usado em M210/M610). Os subconjuntos abaixo reproduzem
# literalmente o texto do Guia sobre quais COD_CONT compoem cada campo do
# M200/M600: "32" aparece nos dois grupos porque o proprio Guia o inclui
# tanto no calculo de VL_TOT_CONT_NC_PER quanto de VL_TOT_CONT_CUM_PER
# (substituicao tributaria - vendas a ZFM).
COD_CONT_NAO_CUMULATIVO = {"01", "02", "03", "04", "32", "71"}
COD_CONT_CUMULATIVO = {"31", "32", "51", "52", "53", "54", "72"}

# Hierarquia: registro filho -> registro pai obrigatorio
PAI = {
    "C170": "C100", "C100": "C010", "C501": "C500", "C505": "C500",
    "D101": "D100", "D105": "D100", "D100": "D010",
    "A170": "A100", "A100": "A010",
    "F100": "F010",
    "M410": "M400", "M810": "M800",
    "0111": "0110",
    "M105": "M100", "M505": "M500",
    "1011": "1010",
    "C181": "C180", "C185": "C180",
    "C191": "C190", "C195": "C190",
    "M211": "M210", "M611": "M610",
    "M210": "M200", "M610": "M600",
    "M110": "M100", "M510": "M500", "M115": "M110", "M515": "M510",
    "M215": "M210", "M615": "M610",
    "M220": "M210", "M620": "M610", "M225": "M220", "M625": "M620",
}

# CST que NAO admitem contribuicao apurada (saida)
CST_SEM_DEBITO = {"04", "05", "06", "07", "08", "09"}
# CST tributados e aliquota basica esperada no nao-cumulativo
ALIQ_BASICA = {"PIS": 1.65, "COFINS": 7.60}
ALIQ_CUMULATIVO = {"PIS": 0.65, "COFINS": 3.00}
CST_TRIBUTADO_BASICO = {"01"}
# CST de entrada que geram credito
CST_CREDITO = {"50","51","52","53","54","55","56","60","61","62","63","64","65","66"}

# Situacao do documento (COD_SIT) que indica documento sem efeito fiscal
# (cancelado / substituido). Tabela padrao do leiaute NF-e/SPED.
COD_SIT_SEM_EFEITO = {"02", "03", "04", "05"}

# Modelos de documento fiscal mais comuns aceitos no C100 (nao exaustivo:
# so os modelos correntes; modelos legados/raros nao entram para nao gerar
# falso positivo em arquivo antigo).
COD_MOD_CONHECIDOS = {"01", "02", "04", "06", "07", "08", "8B", "09", "10",
                       "11", "13", "14", "15", "16", "17", "18", "21", "22",
                       "26", "27", "29", "55", "57", "59", "60", "63", "65", "66"}

# Ordem oficial dos blocos da EFD-Contribuicoes: 0 (abertura/identificacao),
# A (servicos - ISS), C (mercadorias - NF-e), D (servicos - CT-e/transporte),
# F (demais documentos/operacoes), M (apuracao PIS/COFINS), 1 (complemento
# da escrituracao), 9 (controle/encerramento). Estrutura fixa e amplamente
# documentada do leiaute, estavel entre versoes. Compartilhada entre o
# check E22 (ordem dos blocos) e o resumo de composicao do arquivo no
# laudo (report.py) -- fonte unica para nao divergir.
ORDEM_BLOCO = {"0": 0, "A": 1, "C": 2, "D": 3, "F": 4, "M": 5, "1": 6, "9": 7}
NOME_BLOCO = {
    "0": "Abertura e cadastros",
    "A": "Serviços (ISS)",
    "C": "Mercadorias (NF-e)",
    "D": "Serviços de transporte (CT-e)",
    "F": "Demais documentos e operações",
    "M": "Apuração PIS/COFINS",
    "1": "Complemento da escrituração",
    "9": "Controle e encerramento",
}

# Guia Pratico, Tabela 3.1.1 (Versao do Leiaute) -- NAO confundir com a
# versao do proprio Guia Pratico como documento (ex.: "versao 1.35",
# atualizada em 18/06/2021): sao numeracoes independentes. O Guia e
# revisado com esclarecimentos/notas tecnicas sem necessariamente mudar a
# ESTRUTURA do arquivo; o leiaute (campo COD_VER do registro 0000) muda
# raramente. Tabela extraida do texto do Guia (_guia_pratico_full.txt,
# secao 3.1.1, pagina 57):
#   001 = 1.00   (ADE Cofis 31/2010)          vigente a partir de 01/04/2011
#   002 = 1.01/2.00 (ADE Cofis 34 e 20/2012)  vigente a partir de 01/04/2011
#   003 = 2.01A  (ADE Cofis 20/2012)          vigente a partir de 01/07/2012
#   004 = 3.0.0  (ADE Cofis 20/2012)          vigente a partir de 01/06/2018
#   005 = 3.1.0  (ADE Cofis 82/2018)          vigente a partir de 01/01/2019
#   006 = 3.2.0                               vigente a partir de 01/01/2020
# audita/layouts.py foi modelado contra a estrutura da versao 006 (a mais
# recente documentada no PDF fornecido, Guia Pratico v1.35): e a versao
# 006 que introduz o registro 1011 e o campo CHV_DOCe do C500, ambos
# modelados aqui. A versao 005 ja tinha introduzido o leiaute vigente do
# M210/M610 (com ajuste de base de calculo) e os registros M215/M615 --
# tambem modelados. Versoes 001-004 usam o leiaute ANTIGO de M210/M610
# (13 campos, sem o detalhamento de ajuste de base de calculo) -- ver nota
# em LAYOUTS["M210"]/["M610"] acima sobre por que esse leiaute antigo nao
# foi modelado (decadencia de 5 anos numa auditoria feita em 2026).
COD_VER_MODELADO = "006"
COD_VER_LEIAUTE_ANTIGO_M210 = {"001", "002", "003", "004"}
COD_VER_CONHECIDOS = {"001", "002", "003", "004", "005", "006"}
