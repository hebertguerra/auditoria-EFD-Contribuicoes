# audita — auditoria de EFD-Contribuições

Entra o arquivo do SPED, sai um laudo. Não depende de ERP: lê o TXT padrão da Receita.

## Antes de usar em produção: leia isto

O leiaute (`audita/layouts.py`) foi **conferido campo a campo contra o PDF
oficial do Guia Prático da EFD-Contribuições, versão 1.35 (18/06/2021)**.
O usuário forneceu o PDF localmente (433 páginas — o anexo de chat havia
falhado por exceder o limite de 600 páginas da API; contornado extraindo
o texto via `pypdf` por linha de comando). Confirmado pela primeira página
do documento: "Guia Prático da EFD Contribuições – Versão 1.35: Atualização
em 18/06/2021".

**Todos os 60 registros usados no leiaute foram conferidos** (ordem de
campo e obrigatoriedade "S/N" por campo): `0000, 0110, 0111, 0140, 0150,
0190, 0200, 0400, 0500, C010, C100, C170, C500, C501, C505, D010, D100,
D101, D105, A010, A100, A170, F010, F100, M100, M105, M110, M115, M200,
M210, M211, M215, M220, M225, M400, M410, M500, M505, M510, M515, M600,
M610, M611, M615, M620, M625, M800, M810, 9900, 9999, 1010, 1011, 1100,
1500, C180, C181, C185, C190, C191, C195`. Em **todos** os casos a ordem de
campo reconstruída de memória bateu exatamente com o texto oficial (zero
divergências de ordem/campo) — os erros reais encontrados foram todos de
obrigatoriedade (11 campos corrigidos ao todo: campo marcado obrigatório
quando o Guia mostra que é condicional, ou o inverso), corrigidos ao longo
das rodadas (ver "Como um auditor revisaria isto" e o changelog no topo de
`audita/layouts.py`). **Ressalva**: 55 desses foram lidos linha a linha no
PDF; os 5 registros de ajuste espelho-COFINS (`M510, M515, M615, M620,
M625`) foram inferidos por simetria de padrão com os pares PIS
(`M110/M115/M215/M220/M225`) — o padrão se confirmou em 100% dos pares já
lidos nesta reconciliação, mas fica registrado que esses 5 não passaram
por leitura individual (ver changelog em `audita/layouts.py`).

**Atenção a versão de leiaute dentro do próprio registro**: o Guia
documenta *dois* leiautes para M210/M610 — um válido até 31/12/2018 e outro
a partir de 01/01/2019 (mais campos). Só o vigente (2019+) foi modelado
aqui — qualquer arquivo anterior a isso já estaria fora do prazo
decadencial ordinário de 5 anos numa auditoria feita em 2026.

**Isso não elimina a necessidade de reconciliação por engajamento**: a
versão do leiaute em uso pela empresa auditada (campo `COD_VER` do `0000`)
pode ser diferente de v1.35 — confirme antes de tratar o resultado como
evidência pericial fechada. O texto do PDF extraído está em
`_guia_pratico_full.txt` (raiz do projeto) para quem quiser reconferir
contra uma versão mais recente do Guia Prático.

Para deixar rastreável o que foi ou não conferido, cada check carrega uma
tag de confiança que aparece no laudo (tela, PDF e CSV):

- **NÚCLEO** — registro conferido contra o PDF oficial, ou estruturalmente
  equivalente a um registro conferido. Hoje todos os registros usados
  estão neste nível.
- **ESTENDIDO** — reservado para registros que venham a ser adicionados no
  futuro sem conferência direta contra o Guia vigente. Tratar como
  **pista para investigar**, não como conclusão fechada.

Isto é diagnóstico técnico do arquivo, não parecer fiscal.

## Uso

**Windows:** use `python` (não `python3` — no Windows puro, `python3` não é um
comando reconhecido; ele abre a Microsoft Store em vez de rodar o script).
Os exemplos abaixo usam `python`, que funciona em Windows, Mac e Linux.

### Tela web (upload + laudo + PDF/CSV)
```bash
pip install -r requirements.txt
python app.py
```
Abra `http://127.0.0.1:5000`, arraste o TXT do SPED e veja o laudo na tela.
Filtre por severidade e baixe em **PDF** ou **CSV**. O arquivo enviado é
processado em memória e apagado logo após a leitura.

O laudo gerado fica em memória (nunca em disco) e some sozinho depois de
**15 minutos** ou quando o processo passa de 200 laudos retidos ao mesmo
tempo — o que vier primeiro. Isso é proposital: é dado fiscal de terceiro
(sigilo do Art. 198 CTN), não deveria ficar acessível indefinidamente só
porque alguém tem a URL.

Variáveis de ambiente opcionais:

- `AUDITA_SECRET` — chave de assinatura de sessão/flash. Se não definida,
  o processo gera uma chave aleatória a cada subida (nunca um valor fixo
  no código). Defina em produção se quiser que a sessão sobreviva a um
  restart.
- `AUDITA_DEBUG=1` — liga o modo debug do Flask (console interativo do
  Werkzeug) para depuração local. **Nunca** defina isso num ambiente
  exposto: o console permite execução de código no servidor.

### Lote (várias competências de uma vez)
Tanto na tela web (selecione vários arquivos no upload) quanto na linha de
comando, enviar mais de um arquivo de uma vez gera um **laudo em lote**: o
sistema agrupa por CNPJ e ordena por competência sozinho — lidos direto do
`0000` de cada arquivo — sem precisar declarar nada sobre o conjunto que
está sendo enviado. A única coisa que o sistema pede de volta é um aviso
(não um bloqueio) quando os arquivos não formam uma sequência limpa:
competência duplicada, buraco entre períodos, sobreposição, ou CNPJs
diferentes no mesmo envio (nesse caso, agrupados em blocos separados, um
por empresa). O laudo em lote traz um **ranking de reincidência**: quais
checks deram achado em quantos dos períodos enviados — o que separa um
erro pontual de um erro sistêmico repetindo mês a mês. Cada período
também continua navegável individualmente (mesma tela/PDF/CSV de sempre).

### Linha de comando
```bash
python -m audita.cli arquivo.txt laudo.csv

# lote: mais de um .txt = agrupamento automático por CNPJ/competência
python -m audita.cli jan.txt fev.txt mar.txt lote.csv
```

### Arquivo de exemplo
```bash
python gerar_exemplo.py   # cria exemplo_sped.txt com ~15 erros propositais
```
A lista completa dos erros propositais e de qual check cada um exercita
está no docstring de `gerar_exemplo.py`.

Se `pip install` reclamar de permissão ou instalar no lugar errado, confirme
que está usando o mesmo `python` do `pip`: rode `python -m pip install -r
requirements.txt` em vez de `pip install -r requirements.txt` — isso garante
que a instalação vai para o interpretador que você de fato vai usar para
rodar o projeto.

## Estrutura
```
audita/
  app.py         # tela web (Flask): upload, laudo, download PDF/CSV
  templates/     # index (upload) e laudo (resultado, com selo NUCLEO/ESTENDIDO)
  static/        # estilo da interface
  audita/
    layouts.py       # registros declarativos: campos, obrigatoriedade, confianca
    parser.py        # leitor + hierarquia pai/filho + nº de linha
    report.py        # laudo estruturado (usado pela tela, PDF e CSV)
    lote.py           # agrupamento por CNPJ/competência de vários arquivos
    exportar.py       # geração do PDF, do CSV e do CSV consolidado de lote
    checks/
      campos.py         # E17-E19: tipo/formato/obrigatoriedade por campo
      estrutura.py       # E01-E29: arquivo contra ele mesmo
      coerencia.py        # C01-C08: CST x alíquota x valor x CFOP
      reconciliacao.py    # R01-R19: detalhe x bloco M x 0111 x Bloco 1
      tese.py              # T01-T04: sinalização de tese fiscal (não veredito)
    cli.py         # console + CSV
```

## Checks implementados

| Grupo | IDs | O que cobre |
|---|---|---|
| Campos (`campos.py`) | E17-E19 | campo obrigatório vazio; campo N fora do formato SPED; campo D com data inválida |
| Estrutura (`estrutura.py`) | E01-E31 | totalizadores de bloco, hierarquia pai/filho, dígitos verificadores (CNPJ, chave NF-e), item/participante sem cadastro, documento cancelado com valor apurado, chave/documento duplicado, valor negativo, data de emissão incoerente, `COD_NAT`/`COD_CTA` sem cadastro, ordem dos blocos do arquivo, cadastro (`0200`/`0150`) duplicado, retificadora sem `NUM_REC_ANTERIOR`, documento eletrônico sem chave de acesso, registro extemporâneo obsoleto do Bloco 1, `NAT_BC_CRED`/CST/`COD_CRED` fora das tabelas oficiais 4.3.6/4.3.7/4.3.3-4, indício de encoding incorreto na leitura do arquivo (E30), `COD_VER` do arquivo divergente da versão de leiaute modelada (E31) |
| Coerência (`coerencia.py`) | C01-C08 | CST divergente entre PIS/COFINS, CST sem incidência com valor, aritmética base×alíquota, alíquota fora do padrão do regime, CFOP incompatível com o sentido, soma dos itens x cabeçalho |
| Reconciliação (`reconciliacao.py`) | R01-R19 | 0111 x detalhe, exportação sem 0111, débito/crédito no detalhe sem bloco M, M410/M810 x M400/M800, soma interna do 0111 (R07), fórmula de consolidação M200/M600 (R08), crédito no detalhe sem consolidação (R06), identidades M100/M500 (R09), base de cálculo M100/M500 x M105/M505 (R10), identidades 1100/1500 — saldo credor entre períodos (R11), crédito de período anterior 1100/1500 x M200/M600 (R12), C180 x detalhamento C181/C185 (R13), C190 x detalhamento C191/C195 (R14), identidades M210/M610 (R15), M200/M600 x soma M210/M610 por `COD_CONT` (R16), ajuste de crédito M100/M500 x M110/M510 (R17), ajuste de base de cálculo M210/M610 x M215/M615 (R18), ajuste de contribuição M210/M610 x M220/M620 (R19) |
| Tese fiscal (`tese.py`) | T01-T04 | monofásico/ST dependente de tabela externa de NCM, crédito de insumo relevante (essencialidade/relevância — tese STJ), crédito de ativo imobilizado, alíquota fora do padrão sem processo judicial (1010) no arquivo — **sinalização para revisão técnica, não veredito automático** (ver "Como um auditor revisaria isto") |

Checks novos nas últimas rodadas de revisão (ver "Como um auditor revisaria
isto" abaixo): **E22** (ordem dos blocos 0-A-C-D-F-M-1-9), **E23** (cadastro
`0200`/`0150` duplicado), **E24** (retificadora sem `NUM_REC_ANTERIOR`),
**E25** (`CHV_NFE`/`CHV_CTE` ausente para modelo de documento eletrônico),
**E26-E29, R09-R13** (crédito detalhado M100/M105/M500/M505, saldo credor
Bloco 1, consolidação de NF-e C180/C181/C185, tabelas oficiais 4.3.6/4.3.7),
**T01-T04** (tese fiscal), **E30** (indício de encoding incorreto na
leitura do arquivo), **E31** (`COD_VER` do arquivo divergente da versão de
leiaute modelada).

### Testes automatizados
```bash
pip install -r requirements.txt
python gerar_exemplo.py
pytest tests/ -v
```
`tests/test_checks.py` roda todos os checks contra o exemplo sintético e
confere que cada um dispara exatamente nos erros propositais documentados
no docstring de `gerar_exemplo.py` — nem a mais (falso positivo) nem a
menos (check quebrado). Antes desta suíte existir, a única forma de saber
se um check regrediu era ler o console manualmente.

`tests/test_parser.py`, `tests/test_exportar.py`, `tests/test_app.py` e
`tests/test_reconciliacao.py` cobrem a rodada de hardening pós-auditoria
(gramática numérica do leiaute, regime misto, heurística de encoding,
sanitização de CSV/PDF, TTL de laudos, `secret_key`, modo debug).
`tests/test_versao_leiaute.py` cobre o check `E31` (`COD_VER` x versão de
leiaute modelada). `tests/test_lote.py` cobre o agrupamento automático por
CNPJ/competência e os avisos de consistência entre períodos (duplicata,
buraco, sobreposição) — 120 testes ao todo.

## Como adicionar um check
```python
@check("C09", "Devolução de compra sem estorno de crédito",
       RISCO, "ALTA", "Art. 3º Lei 10.833/2003")
def c09(doc):
    for r in doc.todos("C170"):
        ...
        yield Achado(r.linha, "C170", f"NF {...}", "descrição", valor)
```
Toda saída carrega o número da linha do arquivo. Achado sem rastro não vale.

Se o check depender de um registro marcado `ESTENDIDO` em `layouts.py`,
passe `confianca=ESTENDIDO` no decorador — isso é o que faz o laudo exibir
o aviso de "leiaute pendente de conferência" na tela, no PDF e no CSV.

## Como atualizar o leiaute contra o Guia Prático oficial

1. Ajuste `LAYOUT_VERSAO` / `LAYOUT_FONTE` no topo de `audita/layouts.py`.
2. Confira cada lista de campos em `LAYOUTS` contra a tabela do registro no
   Guia Prático — a ordem importa, é ela que mapeia posição → nome.
3. Ajuste `OBRIGATORIOS` conforme a coluna "Obrigatoriedade": só entram
   campos **O** (obrigatórios em qualquer situação). Campos **OC**
   (obrigatórios condicionais) foram deixados de fora de propósito, para
   não gerar falso positivo sem a regra exata da condição.
4. Promova o registro de `ESTENDIDO` para `NUCLEO` em `CONFIANCA` quando
   confirmado.

Se o PDF oficial exceder o limite de páginas de um anexo de chat (600),
extraia o texto localmente e leia em pedaços — não depende do leiaute
inteiro de uma vez:
```python
from pypdf import PdfReader
r = PdfReader("guia_pratico.pdf")
with open("guia_pratico.txt", "w", encoding="utf-8") as f:
    for p in r.pages:
        f.write(p.extract_text() or "")
```
Foi assim que a reconciliação atual (v1.35) foi feita — ver
`_guia_pratico_full.txt` na raiz do projeto.

## Como um auditor revisaria isto

Avaliação honesta do estado do projeto, na ordem em que um auditor
experiente as levantaria:

1. **Integridade da citação de fonte (corrigido, depois confirmado).**
   `audita/layouts.py` chegou a afirmar "conferido campo a campo contra o
   Guia Prático v1.35" sem nunca ter lido o PDF nesta sessão — citação de
   fonte não consultada, o tipo de coisa que derruba um laudo em
   contraditório. Isso foi corrigido primeiro (registros voltaram a
   `ESTENDIDO`, alegação removida) e, na sequência, o usuário forneceu o
   PDF real localmente. A conferência campo a campo foi então feita de
   verdade (ver "Antes de usar em produção" acima), em duas rodadas: a
   primeira nos 10 registros que tinham virado `ESTENDIDO` por precaução
   (0400, 0500, C501/C505, D101/D105, A170, F100, M410/M810) mais os
   centrais mais usados (0000, 0110, 0111, C170, M200, M400, 9900, 9999);
   a segunda nos 10 registros que ainda não tinham sido reconferidos
   individualmente (C010, C100, C500, D010, D100, A010, A100, F010, M600,
   M800). Resultado agregado: **32 de 32 registros com ordem de campo 100%
   correta** (zero divergências) e **11 erros reais de obrigatoriedade**
   corrigidos em `OBRIGATORIOS` (campo tratado como sempre-obrigatório
   quando o Guia marca como condicional, ou vice-versa — ex.: `C100.SER`
   estava exigido quando na verdade é condicional, e `C100.COD_PART`
   não estava exigido quando na verdade é sempre obrigatório) — ver o
   changelog no topo de `audita/layouts.py`.
2. **Sem rede de segurança contra regressão (corrigido nesta rodada).**
   Não havia teste automatizado — a única forma de saber se um check
   quebrou era ler o console à mão depois de cada mudança. Adicionado
   `tests/test_checks.py` (pytest): roda a bateria completa contra o
   exemplo sintético e confere check a check que cada um dispara
   exatamente nos erros propositais documentados, nem mais nem menos.
3. **Lacunas estruturais reais, cobertas ao longo das rodadas:**
   - **E22** — ordem dos blocos do arquivo (0, A, C, D, F, M, 1, 9). O
     validador oficial da Receita rejeita arquivo fora dessa ordem; até
     agora o projeto não checava isso.
   - **E23** — `COD_ITEM`/`COD_PART` duplicado nos cadastros (0200/0150).
     Cadastro duplicado é uma causa comum de erro de rateio de crédito.
   - **E24** — escrituração retificadora (`TIPO_ESCRIT=1`) sem
     `NUM_REC_ANTERIOR`, o recibo do arquivo substituído. Sem essa
     referência a retificação é rejeitada.
   - **E25** — documento com `COD_MOD` de NF-e/NFC-e (55/65) ou CT-e (57)
     sem a chave de acesso correspondente preenchida.
   - **M100/M105/M500/M505 modelados e reconciliados (R09, R10)** — o
     crédito detalhado por natureza dentro do período agora é conferido de
     verdade: identidade `VL_CRED_DISP`/`SLD_CRED` (R09) e base de cálculo
     do pai batendo com a soma dos filhos M105/M505 (R10). Antes, `R06` só
     detectava a *ausência* desses registros; agora reconcilia valores.
   - **Bloco 1 modelado nos registros ativos (1010, 1011, 1100, 1500)** —
     controle de saldo credor entre períodos, com identidades internas
     conferidas (R11) e cruzamento com `M200.VL_TOT_CRED_DESC_ANT` /
     `M600.VL_TOT_CRED_DESC_ANT` (R12). Os registros de crédito/contribuição
     extemporânea da versão antiga do Bloco 1 (`1101, 1102, 1200, 1210,
     1220, 1501, 1502, 1600, 1610, 1620`) foram **deliberadamente não
     modelados campo a campo**: o próprio Guia Prático declara que
     deixaram de ter validade para fatos geradores a partir de agosto/2013
     (o mecanismo correto passou a ser a retificação da escrituração
     original) — em vez disso, `E26` sinaliza a presença de qualquer um
     deles como anomalia.
   - **C180/C181/C185 modelados e reconciliados (R13)** — escrituração
     consolidada de NF-e de *vendas* (alternativa a C100/C170), com o total
     do item conferido contra o detalhamento por CST/CFOP.
   - **C190/C191/C195 modelados e reconciliados (R14)** — o mesmo mecanismo,
     agora para o lado de *aquisições e devoluções* consolidadas por NF-e
     (assimetria que existia até a rodada anterior: só o lado de vendas
     estava coberto).
   - **M210/M610 modelados e reconciliados (R15, R16)** — decomposição da
     contribuição apurada por `COD_CONT` (alíquota básica, diferenciada,
     substituição tributária, SCP etc.), filhos de M200/M600. Identidades
     internas conferidas (R15) e o total declarado em `M200.VL_TOT_CONT_NC_PER`/
     `VL_TOT_CONT_CUM_PER` (e o par em M600) cruzado contra a soma dos
     `M210`/`M610` filhos, agrupados pelo `COD_CONT` de cada regime (R16).
     Descoberta relevante durante a conferência: o Guia documenta **dois
     leiautes** para este registro (um até 31/12/2018, outro a partir de
     01/01/2019) — só o vigente foi modelado, com justificativa registrada
     no comentário de `audita/layouts.py` (decadência de 5 anos).
   - **Registros de ajuste modelados e reconciliados (R17, R18, R19)** —
     M110/M510 (ajuste de crédito, filhos de M100/M500), M215/M615 (ajuste
     de base de cálculo, filhos de M210/M610) e M220/M620 (ajuste da
     contribuição apurada, também filhos de M210/M610). Cada um soma
     `VL_AJ`/`VL_AJ_BC` por `IND_AJ` (0=redução, 1=acréscimo) e confere
     contra os campos agregados do registro pai. **Durante essa
     implementação a própria suíte de testes pegou um bug real**: o
     dicionário `PAI` em `layouts.py` não tinha as entradas
     `"M215": "M210"` / `"M615": "M610"`, então esses registros ficavam
     sem pai vinculado e o check `R18` não disparava mesmo com dado
     propositalmente inconsistente na fixture — só apareceu porque o
     resultado real do CLI não bateu com a contagem esperada calibrada no
     teste. Exatamente o cenário que a suíte automatizada (ver item 2)
     foi criada para pegar.
   - **Tabelas oficiais 4.3.6 (`COD_CRED`, 30 códigos) e 4.3.7
     (`NAT_BC_CRED`, 18 códigos) embutidas** (`E27`, `E29`) — encontradas
     *dentro* do próprio Guia Prático durante a conferência (não são
     tabelas externas, diferente do que se supunha antes). O conjunto de
     CST válidos (32 códigos, tabelas 4.3.3/4.3.4) também passou a ser
     conferido (`E28`).
   - **Checks de tese fiscal (T01-T04)** — monofásico/ST, insumo (tese STJ
     REsp 1.221.170/PR), ativo imobilizado e alíquota divergente sem
     amparo judicial documentado (registro 1010). Implementados como
     **sinalização para revisão**, não veredito: o próprio Guia Prático
     confirma que as tabelas de produto por NCM (4.3.9 a 4.3.16) são
     tabelas *externas*, publicadas separadamente no Portal do SPED — não
     há como conferir aqui, com confiança de estar atualizado, se um NCM
     específico está corretamente classificado como monofásico. Ver o
     docstring de `audita/checks/tese.py` para a justificativa completa.
4. **Lacunas estruturais que permanecem (não implementadas, por decisão
   explícita e não por descuido):**
   - **Bloco P** (Contribuição Previdenciária sobre a Receita Bruta —
     CPRB) existe no mesmo Guia Prático e não é lido — fora do escopo
     deste projeto (PIS/COFINS), mencionado aqui só para deixar claro que
     é omissão consciente, não desconhecimento.
   - Blocos A/D/F cobertos só nos registros essenciais; variantes de
     ECF consolidado (`C400/C490`) e de bebidas frias por marca comercial
     (`0208`, regime descontinuado desde maio/2015) não implementadas.
   - `M210/M610` no **leiaute anterior a 01/01/2019** (13 campos, sem o
     detalhamento de ajuste de base de cálculo) não é suportado — só o
     vigente. Um arquivo pré-2019 processado por engano teria os campos
     desalinhados silenciosamente (ver comentário em `audita/layouts.py`).
   - Tabela oficial de CFOP completa (milhares de códigos, mantida pelo
     CONFAZ fora do Guia Prático) não foi embutida — risco real de ficar
     desatualizada; os checks existentes (`C07`) usam apenas o primeiro
     dígito (grupo entrada/saída), não a tabela semântica completa.
   - Tabelas 4.3.9 a 4.3.16 do Guia (alíquotas de crédito presumido da
     agroindústria, produtos monofásicos/substituição tributária/alíquota
     zero por NCM) são externas ao Guia Prático — não embutidas, por
     decisão consciente (ver item 3 acima sobre T01-T04).
   - Confiança é hoje por *check*, não por *achado*: se um registro
     `ESTENDIDO` for adicionado no futuro, um achado de `E18`/`E19` nesse
     registro herda o risco do registro, não necessariamente o rótulo do
     check (que roda genericamente sobre todo `LAYOUTS`) — leia a coluna
     `registro` do achado, não só o selo do check.
5. **Hardening pós-auditoria de segurança e correção de bugs reais
   (rodada atual).** Uma auditoria técnica externa cobrindo tanto o motor
   de checks fiscais quanto a aplicação web (`app.py`) levantou 11 achados;
   10 foram corrigidos nesta rodada (o 11º, tabela CFOP completa, ficou
   registrado como decisão consciente — ver item 4 acima). Resumo:
   - **Bug real de exatidão numérica**: `num()` tratava qualquer ponto
     como separador de milhar — um campo malformado no formato americano
     (`"1234.56"`) virava `123456.0`, cem vezes maior, sem gerar achado
     algum. A gramática numérica do leiaute SPED (dígitos + vírgula
     decimal, nunca ponto) agora é validada de verdade em `parser.py`
     (`numero_sped_valido`), compartilhada com o check E18; campo fora da
     gramática vira `0.0` em vez de adivinhado, e continua rastreável no
     laudo.
   - **Falso positivo de regime misto**: `COD_INC_TRIB=3` (não-cumulativo
     e cumulativo concomitantes, previsto no Guia Prático) era reduzido a
     "100% não-cumulativo", gerando alerta falso de alíquota fora do
     padrão (C05/T04) para contribuinte com receita financeira e
     operacional no mesmo período — regime legítimo e comum. Corrigido
     com a propriedade `Documento.regime_misto` e `_aliquotas_aceitas()`.
   - **Tolerância de reconciliação sem teto absoluto**: os checks
     R01-R19 toleravam até 0,5% de divergência sem teto, o que para um
     contribuinte de grande porte liberava milhões de reais de
     divergência sem gerar achado. Adicionado teto absoluto de
     R$ 10.000 (`TETO_TOLERANCIA` em `reconciliacao.py`).
   - **Segurança da aplicação web**: modo debug do Flask (console
     interativo do Werkzeug, risco de execução de código) agora exige
     opt-in explícito via `AUDITA_DEBUG=1`; `secret_key` nunca mais cai
     num valor fixo público no código-fonte; laudos em memória (dado
     fiscal sigiloso de terceiro, Art. 198 CTN) expiram em 15 min e
     respeitam um teto de 200 laudos retidos; upload malformado não vaza
     mais descritor de arquivo.
   - **Exportação segura**: CSV agora neutraliza células que começam com
     `= + - @` (CSV/Formula Injection) e o PDF escapa todo texto vindo do
     arquivo SPED antes de repassar ao parser de marcação do reportlab.
   - **Encoding mascarado**: novo check `E30` sinaliza quando o arquivo
     tem indício de ter sido gravado em UTF-8 e lido como Latin-1 (nomes/
     descrições corrompidos silenciosamente).

   Cada correção ganhou teste automatizado dedicado (ver "Testes
   automatizados" acima) — a suíte foi de 65 para 96 testes nesta rodada,
   e um deles pegou um engano real numa primeira tentativa de correção
   (expectativa errada sobre o que `xml.sax.saxutils.escape()` escapa),
   corrigido antes de fechar.

6. **A premissa "leiaute conferido contra o Guia Prático v1.35" nunca era
   checada contra o próprio arquivo (corrigido nesta rodada).** O README
   já avisava "a versão do leiaute em uso pela empresa auditada (campo
   `COD_VER` do `0000`) pode ser diferente — confirme antes de tratar o
   resultado como evidência pericial fechada", mas isso ficava só no
   manual: o código lia `COD_VER` e nunca comparava com nada. Investigando
   o texto extraído do Guia Prático (`_guia_pratico_full.txt`, Tabela
   3.1.1, página 57) para resolver isso direito, veio à tona uma distinção
   que não estava documentada em lugar nenhum do projeto: **a versão do
   Guia Prático como documento ("versão 1.35") e a versão do leiaute
   propriamente dito (campo `COD_VER`, tabela própria com códigos 001 a
   006) são numerações independentes** — o Guia é revisado com
   esclarecimentos sem necessariamente mudar a estrutura do arquivo.
   `gerar_exemplo.py` já usava `COD_VER="006"` (leiaute 3.2.0, vigente
   desde 01/01/2020), confirmando que é essa a versão estrutural contra a
   qual `layouts.py` foi de fato modelado (é a versão 006 que introduz o
   registro `1011` e o campo `CHV_DOCe` do `C500`, ambos já modelados; a
   005 já tinha introduzido o leiaute vigente do `M210`/`M610`). Novo
   check **E31**: compara `0000.COD_VER` contra essa versão modelada e
   diferencia três casos — código 001-004 (leiaute antigo de `M210`/`M610`,
   risco real de campo desalinhado, já documentado antes só como comentário
   de código), código 005 (leiaute de `M210`/`M610` compatível, mas sem os
   registros da versão 006) e código fora da Tabela 3.1.1 conhecida
   (possível versão publicada depois desta reconciliação — sinalização,
   não afirmação de erro).

7. **Auditoria sempre foi arquivo por arquivo, sem visão de tendência
   entre competências (corrigido nesta rodada).** Um erro de parametrização
   sistêmico (ex.: o mesmo CFOP errado usado o ano inteiro) e um evento
   isolado de um período geravam o mesmo tipo de achado num laudo único —
   nada distinguia repetição de acidente. Adicionado processamento em
   **lote** (`audita/lote.py`): enviar mais de um arquivo de uma vez (tela
   ou CLI) agrupa automaticamente por CNPJ e ordena por competência, os
   dois lidos direto do registro `0000` de cada arquivo — **o usuário não
   declara nada sobre o conjunto que está enviando**, nem em que ordem
   selecionar os arquivos. Avisos (não bloqueios — o lote é processado de
   qualquer forma) cobrem os casos em que os arquivos não formam uma
   sequência limpa: competência duplicada, buraco entre períodos,
   sobreposição, ou CNPJs diferentes no mesmo envio. O valor real está no
   **ranking de reincidência** por grupo: cada check com achado ganha uma
   contagem "N de M períodos", ordenado por reincidência antes de
   severidade — é isso que separa erro sistêmico de acidente pontual, e é
   exatamente o tipo de padrão que passa despercebido quando cada
   competência é revisada isoladamente. Cada período continua navegável
   individualmente (mesma tela/PDF/CSV de sempre); o CSV consolidado do
   lote é novo (`para_csv_lote`, com colunas Competência/Arquivo à frente).

8. **C06 comparava documento complementar contra documento regular
   (falso positivo, corrigido nesta rodada).** Descoberto auditando um
   arquivo real de produção: um item com 88 saídas tinha CST 08
   ("Operação sem Incidência", Tabela 4.3.3) em 86 documentos regulares
   (`COD_SIT=00`) e CST 09 ("Operação com Suspensão") nos outros 2, que
   eram **Documento Fiscal Complementar** (`COD_SIT=06`, Tabela SPED de
   Situação do Documento). O check `C06` ("mesmo item, CST diferente")
   comparava as duas categorias juntas, gerando achado de "parametrização
   inconsistente" para uma diferença que é, na verdade, legítima —
   documento complementar retifica/completa valor de uma NF-e anterior e
   pode ter natureza tributária própria, diferente do documento original.
   `_itens_pis_cofins` (`coerencia.py`) passou a carregar `cod_sit` do
   documento pai (`C100`/`A100`); `C06` agora agrupa por
   `(item, sentido, categoria)`, onde `categoria` separa `COD_SIT=06`
   (complementar) do resto (regular) — documentos complementares entre si
   continuam comparados (`tests/test_coerencia.py` cobre esse caso: CST
   diferente entre dois complementares do mesmo item ainda dispara), só
   não são mais comparados contra documento regular. No arquivo real que
   motivou a correção, o achado espúrio desapareceu (449 → 448 ocorrências
   totais) sem alterar nenhum outro check.

9. **Isto é diagnóstico técnico do arquivo, não parecer fiscal — e os
   checks T01-T04 são sinalização para revisão humana, não substituem
   análise jurídica.**
