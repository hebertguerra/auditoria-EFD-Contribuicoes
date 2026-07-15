"""Registro de checks. Cada check e uma funcao que recebe o Documento e devolve Achados."""
from dataclasses import dataclass, field

REGISTRY = []

RISCO, OPORTUNIDADE, ESTRUTURA = "RISCO", "OPORTUNIDADE", "ESTRUTURA"


@dataclass
class Achado:
    linha: int = 0
    registro: str = ""
    referencia: str = ""     # NF, item, o que identifica no mundo real
    detalhe: str = ""
    valor: float = 0.0


@dataclass
class Check:
    id: str
    titulo: str
    caixa: str
    severidade: str          # ALTA / MEDIA / BAIXA
    base: str                # base legal / tecnica
    fn: object = None
    achados: list = field(default_factory=list)
    confianca: str = "NUCLEO"  # NUCLEO (leiaute conferido) / ESTENDIDO (pendente de conferencia)


def check(id, titulo, caixa, severidade, base, confianca="NUCLEO"):
    def deco(fn):
        REGISTRY.append(Check(id=id, titulo=titulo, caixa=caixa, severidade=severidade,
                              base=base, fn=fn, confianca=confianca))
        return fn
    return deco


def executar(doc):
    resultado = []
    for c in REGISTRY:
        try:
            achados = list(c.fn(doc) or [])
        except Exception as e:
            achados = [Achado(detalhe=f"ERRO NO CHECK: {type(e).__name__}: {e}")]
        resultado.append((c, achados))
    return resultado


from . import estrutura, coerencia, reconciliacao, campos, tese  # noqa: E402,F401
