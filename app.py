"""Interface web da auditoria EFD-Contribuicoes.

Sobe o arquivo do SPED, roda a auditoria completa, mostra o laudo na tela
e permite baixar em PDF e CSV.

    pip install -r requirements.txt
    python app.py
    # abre http://127.0.0.1:5000
"""
import io
import os
import tempfile
import uuid

from flask import (Flask, render_template, request, redirect, url_for,
                   send_file, abort, flash)

from audita.report import gerar_laudo
from audita.exportar import para_csv, para_pdf

app = Flask(__name__)
app.secret_key = os.environ.get("AUDITA_SECRET", "audita-dev-key")
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200 MB

# Laudos em memoria (token -> laudo). Some ao reiniciar o servidor.
LAUDOS = {}
EXTENSOES_OK = {".txt", ".TXT"}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/auditar", methods=["POST"])
def auditar():
    arquivo = request.files.get("arquivo")
    if not arquivo or not arquivo.filename:
        flash("Selecione um arquivo .txt do SPED.")
        return redirect(url_for("index"))

    ext = os.path.splitext(arquivo.filename)[1]
    if ext.lower() != ".txt":
        flash("O arquivo precisa ser o TXT padrao da EFD-Contribuicoes.")
        return redirect(url_for("index"))

    # grava temporario, roda a auditoria, remove
    fd, caminho = tempfile.mkstemp(suffix=".txt")
    try:
        arquivo.save(caminho)
        os.close(fd)
        laudo = gerar_laudo(caminho)
    except Exception as e:
        flash(f"Nao consegui ler o arquivo: {type(e).__name__}: {e}")
        return redirect(url_for("index"))
    finally:
        try:
            os.remove(caminho)
        except OSError:
            pass

    token = uuid.uuid4().hex
    laudo["arquivo"]["nome_original"] = arquivo.filename
    LAUDOS[token] = laudo
    return redirect(url_for("laudo", token=token))


@app.route("/laudo/<token>")
def laudo(token):
    laudo = LAUDOS.get(token)
    if not laudo:
        flash("Laudo expirado. Suba o arquivo de novo.")
        return redirect(url_for("index"))
    return render_template("laudo.html", laudo=laudo, token=token)


@app.route("/download/<token>/<formato>")
def download(token, formato):
    laudo = LAUDOS.get(token)
    if not laudo:
        abort(404)
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


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
