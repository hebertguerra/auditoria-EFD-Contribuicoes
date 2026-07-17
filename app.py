"""Interface web da auditoria EFD-Contribuicoes.

Sobe o arquivo do SPED, roda a auditoria completa, mostra o laudo na tela
e permite baixar em PDF e CSV.

    pip install -r requirements.txt
    python app.py
    # abre http://127.0.0.1:5000
"""
import io
import os
import secrets
import tempfile
import time
import uuid

from flask import (Flask, render_template, request, redirect, url_for,
                   send_file, abort, flash)

from audita.report import gerar_laudo
from audita.exportar import para_csv, para_pdf, para_csv_lote
from audita.lote import gerar_lote

app = Flask(__name__)
# Sem AUDITA_SECRET definido, gera uma chave aleatoria a cada subida do
# processo (nunca um valor fixo no codigo-fonte, que ficaria publico no
# repositorio). Sessoes/flash nao sobrevivem a um restart nesse caso -- ok
# para este app, que nao depende de sessao persistente entre reinicios.
_secret = os.environ.get("AUDITA_SECRET")
if not _secret:
    _secret = secrets.token_hex(32)
    print("[aviso] AUDITA_SECRET nao definido -- usando chave aleatoria "
          "valida so para esta execucao. Defina AUDITA_SECRET em producao.")
app.secret_key = _secret
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200 MB

# Laudos em memoria (token -> (laudo, timestamp)). TTL proprio (ver
# _limpar_laudos_expirados) alem de somir ao reiniciar o servidor --
# laudo fiscal de terceiro (sigilo do Art. 198 CTN) nao deve ficar
# acessivel indefinidamente so porque alguem tem a URL.
LAUDOS = {}
LOTES = {}  # mesma logica do LAUDOS, para o resultado consolidado de varios arquivos
LAUDO_TTL_SEGUNDOS = 15 * 60
LAUDOS_MAX_RETIDOS = 200
EXTENSOES_OK = {".txt", ".TXT"}


def _limpar_expirados(dic):
    agora = time.time()
    expirados = [tok for tok, (_, criado_em) in dic.items()
                 if agora - criado_em > LAUDO_TTL_SEGUNDOS]
    for tok in expirados:
        del dic[tok]
    # se ainda estiver acima do limite (uso intenso), descarta os mais antigos
    if len(dic) > LAUDOS_MAX_RETIDOS:
        por_idade = sorted(dic.items(), key=lambda kv: kv[1][1])
        for tok, _ in por_idade[:len(dic) - LAUDOS_MAX_RETIDOS]:
            del dic[tok]


def _limpar_laudos_expirados():
    _limpar_expirados(LAUDOS)


def _limpar_lotes_expirados():
    _limpar_expirados(LOTES)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/auditar", methods=["POST"])
def auditar():
    arquivos = [a for a in request.files.getlist("arquivo") if a and a.filename]
    if not arquivos:
        flash("Selecione um ou mais arquivos .txt do SPED.")
        return redirect(url_for("index"))

    for a in arquivos:
        if os.path.splitext(a.filename)[1].lower() != ".txt":
            flash(f"'{a.filename}' nao e um TXT -- envie apenas o TXT padrao "
                  "da EFD-Contribuicoes.")
            return redirect(url_for("index"))

    # Um arquivo so: fluxo de sempre (laudo unico). Mais de um: agrupa
    # como lote -- o usuario nao precisa dizer que esta enviando varios
    # periodos, so selecionar os arquivos (ver audita/lote.py).
    if len(arquivos) == 1:
        return _processar_arquivo_unico(arquivos[0])
    return _processar_lote(arquivos)


def _processar_arquivo_unico(arquivo):
    fd, caminho = tempfile.mkstemp(suffix=".txt")
    os.close(fd)  # so precisa do caminho; fechado ja aqui para nao vazar o
                   # descritor se arquivo.save() ou gerar_laudo() falharem
    try:
        arquivo.save(caminho)
        laudo = gerar_laudo(caminho)
    except Exception as e:
        flash(f"Nao consegui ler o arquivo: {type(e).__name__}: {e}")
        return redirect(url_for("index"))
    finally:
        try:
            os.remove(caminho)
        except OSError:
            pass

    _limpar_laudos_expirados()
    token = uuid.uuid4().hex
    laudo["arquivo"]["nome_original"] = arquivo.filename
    LAUDOS[token] = (laudo, time.time())
    return redirect(url_for("laudo", token=token))


def _processar_lote(arquivos):
    caminhos_temp = []
    try:
        caminhos_com_nome = []
        for arquivo in arquivos:
            fd, caminho = tempfile.mkstemp(suffix=".txt")
            os.close(fd)
            caminhos_temp.append(caminho)
            arquivo.save(caminho)
            caminhos_com_nome.append((caminho, arquivo.filename))
        lote = gerar_lote(caminhos_com_nome)
    except Exception as e:
        flash(f"Nao consegui ler o lote: {type(e).__name__}: {e}")
        return redirect(url_for("index"))
    finally:
        for caminho in caminhos_temp:
            try:
                os.remove(caminho)
            except OSError:
                pass

    _limpar_laudos_expirados()
    _limpar_lotes_expirados()
    # cada periodo tambem vira um laudo individual navegavel em /laudo/<token>
    # (reaproveita a tela e os downloads que ja existem, sem duplicar nada)
    for grupo in lote["grupos"]:
        for p in grupo["periodos"]:
            tok_periodo = uuid.uuid4().hex
            LAUDOS[tok_periodo] = (p["laudo"], time.time())
            p["token"] = tok_periodo

    token = uuid.uuid4().hex
    LOTES[token] = (lote, time.time())
    return redirect(url_for("lote", token=token))


@app.route("/laudo/<token>")
def laudo(token):
    _limpar_laudos_expirados()
    entrada = LAUDOS.get(token)
    if not entrada:
        flash("Laudo expirado ou nao encontrado. Suba o arquivo de novo.")
        return redirect(url_for("index"))
    return render_template("laudo.html", laudo=entrada[0], token=token)


@app.route("/lote/<token>")
def lote(token):
    _limpar_lotes_expirados()
    entrada = LOTES.get(token)
    if not entrada:
        flash("Lote expirado ou nao encontrado. Suba os arquivos de novo.")
        return redirect(url_for("index"))
    return render_template("lote.html", lote=entrada[0], token=token)


@app.route("/download/<token>/<formato>")
def download(token, formato):
    _limpar_laudos_expirados()
    entrada = LAUDOS.get(token)
    if not entrada:
        abort(404)
    laudo = entrada[0]
    base = "laudo_auditoria"
    if formato == "csv":
        dados = para_csv(laudo)
        return send_file(io.BytesIO(dados), mimetype="text/csv",
                         as_attachment=True, download_name=f"{base}.csv")
    if formato == "pdf":
        dados = para_pdf(laudo)
        return send_file(io.BytesIO(dados), mimetype="application/pdf",
                         as_attachment=True, download_name=f"{base}.pdf")
    abort(404)


@app.route("/download-lote/<token>/csv")
def download_lote(token):
    _limpar_lotes_expirados()
    entrada = LOTES.get(token)
    if not entrada:
        abort(404)
    dados = para_csv_lote(entrada[0])
    return send_file(io.BytesIO(dados), mimetype="text/csv",
                     as_attachment=True, download_name="laudo_lote.csv")


def _debug_habilitado():
    """Debug (console interativo do Werkzeug) so liga com opt-in explicito
    -- nunca por padrao. Ver achado F1 da auditoria: com debug=True fixo,
    qualquer excecao nao tratada expunha um terminal Python navegavel no
    proprio navegador."""
    return os.environ.get("AUDITA_DEBUG") == "1"


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=_debug_habilitado())
