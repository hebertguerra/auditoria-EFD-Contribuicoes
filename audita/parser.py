"""Leitor da EFD-Contribuicoes. Preserva numero de linha para rastreabilidade."""
from collections import Counter, defaultdict
from .layouts import LAYOUTS, PAI


def num(v):
    """Converte numero no formato SPED (virgula decimal) para float."""
    if v is None:
        return 0.0
    v = v.strip()
    if not v:
        return 0.0
    try:
        return float(v.replace(".", "").replace(",", "."))
    except ValueError:
        return 0.0


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


class Documento:
    def __init__(self, caminho):
        self.caminho = caminho
        self.registros = []
        self.por_reg = defaultdict(list)
        self.contagem = Counter()
        self.total_linhas_arquivo = 0
        self._ler()

    def _ler(self):
        # pilha de possiveis pais em aberto
        abertos = {}
        with open(self.caminho, encoding="latin-1") as f:
            for i, linha in enumerate(f, 1):
                self.total_linhas_arquivo = i
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
    def regime_cumulativo(self):
        """0110.COD_INC_TRIB: 1=nao-cumulativo, 2=cumulativo, 3=ambos"""
        r = self.um("0110")
        return r["COD_INC_TRIB"] == "2" if r else False
