"""Testes unitarios/funcionais da aplicacao web (app.py).

Cobre as correcoes da rodada de hardening pos-auditoria:
- F1: debug do Flask nunca liga por padrao.
- F5: laudos em memoria expiram por TTL e respeitam um limite maximo.
- F6: secret_key nunca cai no valor fixo antigo do repositorio.
- F11: falha no upload nao deixa arquivo temporario nem descritor pendente.

E o upload em lote (multiplos arquivos no mesmo POST /auditar):
- 1 arquivo continua indo para /laudo/<token> exatamente como antes.
- >1 arquivo vai para /lote/<token>, com cada periodo tambem navegavel
  individualmente em /laudo/<token>.
"""
import io
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import app as appmod  # noqa: E402


def _sped_minimo_bytes(cnpj, dt_ini, dt_fim, nome="EMPRESA TESTE", qtd_lin_errada=False):
    """Bytes de um arquivo minimo, valido o bastante para virar Documento.
    qtd_lin_errada=True dispara o check E03 de proposito (util para testar
    exportacao/paginas que dependem de haver pelo menos um achado)."""
    linha_9999 = "|9999|" + ("99" if qtd_lin_errada else "2") + "|"
    linhas = [
        f"|0000|006|0|||{dt_ini}|{dt_fim}|{nome}|{cnpj}|SP|3550308|||1|0|",
        linha_9999,
    ]
    return ("\n".join(linhas) + "\n").encode("latin-1")


@pytest.fixture(autouse=True)
def _laudos_limpos():
    """Isola cada teste: LAUDOS/LOTES sao dicts globais no modulo."""
    appmod.LAUDOS.clear()
    appmod.LOTES.clear()
    yield
    appmod.LAUDOS.clear()
    appmod.LOTES.clear()


@pytest.fixture
def client():
    appmod.app.config["TESTING"] = True
    return appmod.app.test_client()


# --- F6: secret_key ----------------------------------------------------------

def test_secret_key_nao_e_o_valor_fixo_antigo_do_repositorio():
    assert appmod.app.secret_key != "audita-dev-key"
    assert len(appmod.app.secret_key) >= 32


def test_secret_key_respeita_env_var_quando_definida():
    """Roda em subprocesso: secret_key e fixada na importacao do modulo,
    entao so um processo novo reflete a variavel de ambiente."""
    saida = subprocess.run(
        [sys.executable, "-c",
         "import app; print(app.app.secret_key)"],
        cwd=RAIZ, capture_output=True, text=True,
        env={**__import__("os").environ, "AUDITA_SECRET": "chave-fixada-no-teste"},
        check=True,
    )
    assert saida.stdout.strip() == "chave-fixada-no-teste"


# --- F1: debug -----------------------------------------------------------------

def test_debug_desabilitado_por_padrao(monkeypatch):
    monkeypatch.delenv("AUDITA_DEBUG", raising=False)
    assert appmod._debug_habilitado() is False


def test_debug_habilitado_via_env_explicita(monkeypatch):
    monkeypatch.setenv("AUDITA_DEBUG", "1")
    assert appmod._debug_habilitado() is True


def test_debug_qualquer_outro_valor_fica_desabilitado(monkeypatch):
    monkeypatch.setenv("AUDITA_DEBUG", "true")  # so "1" liga -- sem ambiguidade
    assert appmod._debug_habilitado() is False


# --- F5: TTL e limite de laudos em memoria -----------------------------------

def test_limpar_laudos_expirados_remove_apenas_os_vencidos():
    agora = time.time()
    appmod.LAUDOS["velho"] = ({"x": 1}, agora - appmod.LAUDO_TTL_SEGUNDOS - 1)
    appmod.LAUDOS["novo"] = ({"x": 2}, agora)
    appmod._limpar_laudos_expirados()
    assert "velho" not in appmod.LAUDOS
    assert "novo" in appmod.LAUDOS


def test_limpar_laudos_respeita_limite_maximo_retido():
    agora = time.time()
    for i in range(appmod.LAUDOS_MAX_RETIDOS + 15):
        appmod.LAUDOS[f"tok{i}"] = ({"x": i}, agora + i)  # mais recente = i maior
    appmod._limpar_laudos_expirados()
    assert len(appmod.LAUDOS) == appmod.LAUDOS_MAX_RETIDOS
    assert "tok0" not in appmod.LAUDOS  # mais antigo descartado primeiro
    assert f"tok{appmod.LAUDOS_MAX_RETIDOS + 14}" in appmod.LAUDOS  # mais novo fica


def test_rota_laudo_com_token_inexistente_redireciona_sem_erro(client):
    r = client.get("/laudo/token-inexistente")
    assert r.status_code == 302


def test_rota_download_com_token_expirado_retorna_404(client):
    appmod.LAUDOS["expirado"] = ({"x": 1}, time.time() - appmod.LAUDO_TTL_SEGUNDOS - 1)
    r = client.get("/download/expirado/csv")
    assert r.status_code == 404
    assert "expirado" not in appmod.LAUDOS  # limpo pela propria checagem


# --- F11: upload malformado nao vaza recurso ---------------------------------

def test_upload_com_falha_no_save_nao_derruba_a_aplicacao(client, tmp_path):
    """Simula arquivo.save() falhando (disco cheio, permissao etc.) --
    antes da correcao, o fd de mkstemp so era fechado DEPOIS do save(), e
    uma excecao aqui pulava o os.close() (vazamento de descritor a cada
    falha). Agora o fd fecha logo apos o mkstemp, antes de qualquer chance
    de excecao."""
    with patch("werkzeug.datastructures.FileStorage.save",
               side_effect=OSError("disco cheio (simulado)")):
        data = {"arquivo": (open(__file__, "rb"), "arquivo.txt")}
        r = client.post("/auditar", data=data, content_type="multipart/form-data")
    assert r.status_code == 302  # redireciona com flash, sem 500


def test_upload_sem_arquivo_nao_processa(client):
    r = client.post("/auditar", data={}, content_type="multipart/form-data")
    assert r.status_code == 302
    assert len(appmod.LAUDOS) == 0


# --- upload em lote (multiplos arquivos no mesmo POST) -----------------------

def test_upload_de_um_arquivo_continua_indo_para_laudo_unico(client):
    """Regressao: o fluxo de sempre (1 arquivo) nao pode mudar so porque
    o suporte a lote foi adicionado."""
    dados = _sped_minimo_bytes("11222333000181", "01012024", "31012024")
    r = client.post("/auditar",
                    data={"arquivo": (io.BytesIO(dados), "jan.txt")},
                    content_type="multipart/form-data")
    assert r.status_code == 302
    assert "/laudo/" in r.headers["Location"]
    assert len(appmod.LAUDOS) == 1
    assert len(appmod.LOTES) == 0


def test_upload_de_varios_arquivos_vai_para_lote(client):
    jan = _sped_minimo_bytes("11222333000181", "01012024", "31012024")
    fev = _sped_minimo_bytes("11222333000181", "01022024", "29022024")
    r = client.post("/auditar",
                    data={"arquivo": [(io.BytesIO(jan), "jan.txt"),
                                      (io.BytesIO(fev), "fev.txt")]},
                    content_type="multipart/form-data")
    assert r.status_code == 302
    assert "/lote/" in r.headers["Location"]
    assert len(appmod.LOTES) == 1
    # cada periodo do lote tambem vira um laudo individual navegavel
    assert len(appmod.LAUDOS) == 2


def test_rota_lote_renderiza_com_os_dois_periodos(client):
    jan = _sped_minimo_bytes("11222333000181", "01012024", "31012024")
    fev = _sped_minimo_bytes("11222333000181", "01022024", "29022024")
    r = client.post("/auditar",
                    data={"arquivo": [(io.BytesIO(jan), "jan.txt"),
                                      (io.BytesIO(fev), "fev.txt")]},
                    content_type="multipart/form-data", follow_redirects=True)
    assert r.status_code == 200
    corpo = r.get_data(as_text=True)
    assert "jan.txt" in corpo
    assert "fev.txt" in corpo
    assert "EMPRESA TESTE" in corpo


def test_lote_com_periodos_de_cnpjs_diferentes_avisa_no_html(client):
    a = _sped_minimo_bytes("11222333000181", "01012024", "31012024", nome="EMPRESA A")
    b = _sped_minimo_bytes("11444777000161", "01012024", "31012024", nome="EMPRESA B")
    r = client.post("/auditar",
                    data={"arquivo": [(io.BytesIO(a), "a.txt"), (io.BytesIO(b), "b.txt")]},
                    content_type="multipart/form-data", follow_redirects=True)
    corpo = r.get_data(as_text=True)
    assert "EMPRESA A" in corpo
    assert "EMPRESA B" in corpo
    assert "mais de um CNPJ" in corpo


def test_download_lote_csv_funciona(client):
    jan = _sped_minimo_bytes("11222333000181", "01012024", "31012024", qtd_lin_errada=True)
    fev = _sped_minimo_bytes("11222333000181", "01022024", "29022024")
    r = client.post("/auditar",
                    data={"arquivo": [(io.BytesIO(jan), "jan.txt"),
                                      (io.BytesIO(fev), "fev.txt")]},
                    content_type="multipart/form-data")
    token = r.headers["Location"].rsplit("/", 1)[-1]

    r2 = client.get(f"/download-lote/{token}/csv")
    assert r2.status_code == 200
    assert r2.mimetype == "text/csv"
    corpo = r2.get_data(as_text=True)
    assert "Competencia" in corpo
    assert "jan.txt" in corpo  # linha do achado proposital (E03) de janeiro
    assert "E03" in corpo


def test_rota_lote_com_token_inexistente_redireciona_sem_erro(client):
    r = client.get("/lote/token-inexistente")
    assert r.status_code == 302


def test_download_lote_com_token_inexistente_retorna_404(client):
    r = client.get("/download-lote/token-inexistente/csv")
    assert r.status_code == 404


def test_limpar_lotes_expirados_remove_apenas_os_vencidos():
    agora = time.time()
    appmod.LOTES["velho"] = ({"grupos": []}, agora - appmod.LAUDO_TTL_SEGUNDOS - 1)
    appmod.LOTES["novo"] = ({"grupos": []}, agora)
    appmod._limpar_lotes_expirados()
    assert "velho" not in appmod.LOTES
    assert "novo" in appmod.LOTES
