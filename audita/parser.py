"""Leitor da EFD-Contribuicoes. Preserva numero de linha para rastreabilidade."""
import re
from collections import Counter, defaultdict
from .layouts import LAYOUTS, PAI

# Gramatica SPED para campo tipo N (Ato COTEPE 09/2008 / Guia Pratico):
# digitos, virgula decimal opcional, sinal opcional -- NUNCA ponto (SPED
# nao usa separador de milhar). Um campo como "1234.56" (ponto no lugar de
# virgula, ex.: exportacao de ERP com bug proprio) nao e uma variacao de
# formato valida -- e um campo mal formado.
_NUM_SPED_RE = re.compile(r"^[+-]?\d+(,\d+)?$")


def numero_sped_valido(v):
    """True se v segue a gramatica SPED (ver _NUM_SPED_RE). Vazio conta como
    valido aqui -- ausencia de campo obrigatorio e responsabilidade do
    check E17, nao deste validador de formato."""
    v = (v or "").strip()
    return not v or bool(_NUM_SPED_RE.match(v))


# latin-1 (correto para o TXT da EFD-Contribuicoes) nunca lanca
# UnicodeDecodeError, mesmo lendo um arquivo gravado por engano em UTF-8 --
# o arquivo eh lido sem erro nenhum, mas com "Ã©"/"Ã§"/"Ã£" etc no lugar de
# "é"/"ç"/"ã" (bytes UTF-8 multi-byte reinterpretados um a um como
# Latin-1). Esse padrao praticamente nunca aparece em texto Latin-1
# genuino, entao serve de heuristica para sinalizar o arquivo errado.
_MOJIBAKE_RE = re.compile("[ÃÂ][" + chr(0x80) + "-" + chr(0xbf) + "]")


def num(v):
    """Converte numero no formato SPED (virgula decimal, sem separador de
    milhar) para float. Campo fora da gramatica (ex.: ponto decimal)
    devolve 0.0 em vez de adivinhar o separador -- adivinhar errado inflava
    o valor em 100x silenciosamente. O check E18 sinaliza o achado de
    formato invalido para o campo continuar rastreavel no laudo."""
    if v is None:
        return 0.0
    v = v.strip()
    if not v or not numero_sped_valido(v):
        return 0.0
    return float(v.replace(",", "."))


class Registro:
    __slots__ = ("linha", "reg", "campos", "pai", "_d")

    def __init__(self, linha, reg, campos):
        self.linha = linha
        self.reg = reg
        self.campos = campos
        self.pai = None
        self._d = None

    def __getitem__(self, k):
        if self._d is None:
            lay = LAYOUTS.get(self.reg)
            if lay:
                self._d = {n: (self.campos[i] if i < len(self.campos) else "")
                           for i, n in enumerate(lay)}
            else:
                self._d = {}
        return self._d.get(k, "")

    def n(self, k):
        return num(self[k])

    def __repr__(self):
        return f"<{self.reg} L{self.linha}>"


# A partir desta contagem de ocorrencias do padrao mojibake no arquivo, a
# heuristica considera que o encoding de origem provavelmente nao era
# Latin-1 -- baixo o bastante para pegar um arquivo pequeno, alto o
# bastante para nao disparar por coincidencia de 1-2 bytes.
_LIMIAR_MOJIBAKE = 3


class Documento:
    def __init__(self, caminho):
        self.caminho = caminho
        self.registros = []
        self.por_reg = defaultdict(list)
        self.contagem = Counter()
        self.total_linhas_arquivo = 0
        self.possivel_encoding_incorreto = False
        self._ler()

    def _ler(self):
        # pilha de possiveis pais em aberto
        abertos = {}
        marcas_mojibake = 0
        with open(self.caminho, encoding="latin-1") as f:
            for i, linha in enumerate(f, 1):
                self.total_linhas_arquivo = i
                if marcas_mojibake < _LIMIAR_MOJIBAKE:
                    marcas_mojibake += len(_MOJIBAKE_RE.findall(linha))
                campos = linha.rstrip("\r\n").split("|")
                if len(campos) < 3:
                    continue
                reg = campos[1]
                r = Registro(i, reg, campos[1:-1])
                pai_esperado = PAI.get(reg)
                if pai_esperado:
                    r.pai = abertos.get(pai_esperado)
                abertos[reg] = r
                self.registros.append(r)
                self.por_reg[reg].append(r)
                self.contagem[reg] += 1
        self.possivel_encoding_incorreto = marcas_mojibake >= _LIMIAR_MOJIBAKE

    # --- atalhos ---
    def um(self, reg):
        l = self.por_reg.get(reg)
        return l[0] if l else None

    def todos(self, reg):
        return self.por_reg.get(reg, [])

    @property
    def cabecalho(self):
        return self.um("0000")

    @property
    def competencia(self):
        c = self.cabecalho
        return (c["DT_INI"], c["DT_FIN"]) if c else ("", "")

    @property
    def empresa(self):
        c = self.cabecalho
        return (c["NOME"], c["CNPJ"]) if c else ("", "")

    @property
    def _cod_inc_trib(self):
        r = self.um("0110")
        return r["COD_INC_TRIB"] if r else ""

    @property
    def regime_cumulativo(self):
        """0110.COD_INC_TRIB: 1=nao-cumulativo, 2=cumulativo, 3=ambos"""
        return self._cod_inc_trib == "2"

    @property
    def regime_misto(self):
        """COD_INC_TRIB=3: nao-cumulativo e cumulativo concomitantes no
        mesmo periodo -- as duas aliquotas basicas (0,65/3,0 e 1,65/7,6)
        sao validas simultaneamente (ex.: receita financeira cumulativa
        convivendo com receita operacional nao-cumulativa)."""
        return self._cod_inc_trib == "3"
