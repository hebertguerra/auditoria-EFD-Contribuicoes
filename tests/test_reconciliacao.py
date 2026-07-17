"""Teste unitario do teto absoluto de tolerancia (achado F8).

Sem teto absoluto, o piso relativo de 0,5% escalava sem limite: para um
contribuinte com receita de centenas de milhoes, a tolerancia chegava a
milhoes de reais sem gerar achado.
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from audita.checks.reconciliacao import TOL, TETO_TOLERANCIA, _tol  # noqa: E402


def test_tol_usa_piso_minimo_para_valores_pequenos():
    assert _tol(10) == TOL
    assert _tol(0) == TOL


def test_tol_usa_percentual_relativo_na_faixa_intermediaria():
    esperado = 50_000 * 0.005
    assert TOL < esperado < TETO_TOLERANCIA
    assert _tol(50_000) == esperado


def test_tol_nunca_ultrapassa_o_teto_absoluto():
    """Regressao direta do achado F8: antes desta correcao, 0,5% de
    R$ 500 milhoes (R$ 2,5 milhoes) passava sem gerar achado."""
    assert _tol(500_000_000) == TETO_TOLERANCIA
    assert _tol(500_000_000) < 500_000_000 * 0.005


def test_tol_e_simetrica_para_valores_negativos():
    assert _tol(-50_000) == _tol(50_000)
