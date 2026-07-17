import csv
import sys
from .parser import Documento
from .checks import executar

ORDEM = {"ALTA": 0, "MEDIA": 1, "BAIXA": 2}


def main(caminho, csv_saida=None, limite_amostra=3):
    doc = Documento(caminho)
    nome, cnpj = doc.empresa
    ini, fim = doc.competencia

    print("=" * 78)
    print(f" AUDITORIA EFD-CONTRIBUICOES")
    print(f" {nome}  |  CNPJ {cnpj}  |  competencia {ini} a {fim}")
    print(f" {doc.total_linhas_arquivo:,} linhas  |  {len(doc.contagem)} tipos de registro")
    print("=" * 78)

    resultado = executar(doc)
    resultado.sort(key=lambda x: (ORDEM.get(x[0].severidade, 9), x[0].id))

    linhas_csv = []
    total_ok = total_falha = 0

    for c, achados in resultado:
        if not achados:
            total_ok += 1
            print(f"  [ok]  {c.id}  {c.titulo}")
            continue
        total_falha += 1
        valor = sum(a.valor for a in achados)
        tag = "  [ESTENDIDO - leiaute pendente de conferencia]" if c.confianca == "ESTENDIDO" else ""
        print()
        print(f"  [!!]  {c.id}  {c.titulo}{tag}")
        print(f"        {c.severidade} | {c.caixa} | {len(achados)} ocorrencia(s)"
              + (f" | R$ {valor:,.2f}" if valor else ""))
        print(f"        base: {c.base}")
        for a in achados[:limite_amostra]:
            loc = f"L{a.linha}" if a.linha else "-"
            print(f"          {loc:>7} {a.registro:<5} {a.referencia[:32]:<32} {a.detalhe}")
        if len(achados) > limite_amostra:
            print(f"          ... mais {len(achados) - limite_amostra}")
        for a in achados:
            linhas_csv.append({
                "check": c.id, "titulo": c.titulo, "severidade": c.severidade,
                "caixa": c.caixa, "confianca": c.confianca,
                "linha": a.linha, "registro": a.registro,
                "referencia": a.referencia, "detalhe": a.detalhe,
                "valor": f"{a.valor:.2f}", "base": c.base,
            })

    print()
    print("=" * 78)
    print(f" {total_ok} check(s) sem achado | {total_falha} com achado | "
          f"{len(linhas_csv)} ocorrencia(s)")
    print("=" * 78)

    if csv_saida and linhas_csv:
        with open(csv_saida, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(linhas_csv[0]))
            w.writeheader()
            w.writerows(linhas_csv)
        print(f" laudo: {csv_saida}")
    return linhas_csv


def main_lote(caminhos, csv_saida=None):
    """Varios arquivos de uma vez: agrupa por CNPJ e ordena por competencia
    sozinho (cada arquivo ja carrega isso no proprio 0000 -- nao precisa
    passar em ordem nem dizer quais formam um lote)."""
    from .lote import gerar_lote

    lote = gerar_lote([(c, c) for c in caminhos])

    print("=" * 78)
    print(" AUDITORIA EFD-CONTRIBUICOES -- LOTE")
    print(f" {lote['total_arquivos']} arquivo(s)  |  {len(lote['grupos'])} CNPJ(s) distinto(s)")
    print("=" * 78)

    for g in lote["grupos"]:
        r = g["resumo"]
        print()
        print(f" {g['nome']}  |  CNPJ {g['cnpj_fmt']}  |  {r['periodos']} periodo(s)")
        for aviso in g["avisos"]:
            print(f"   [aviso] {aviso}")
        print(f"   {r['ocorrencias']} ocorrencia(s)  |  R$ {r['valor_total']:,.2f}  |  "
              f"ALTA {r['por_severidade']['ALTA']} / MEDIA {r['por_severidade']['MEDIA']} "
              f"/ BAIXA {r['por_severidade']['BAIXA']}")
        if g["por_check"]:
            print("   checks mais recorrentes entre periodos:")
            for a in g["por_check"][:5]:
                print(f"     {a['id']:<5} {a['periodos_com_achado']}/{a['total_periodos']} "
                      f"periodos  {a['titulo']}")

    print()
    print("=" * 78)

    if csv_saida:
        from .exportar import para_csv_lote
        with open(csv_saida, "wb") as f:
            f.write(para_csv_lote(lote))
        print(f" laudo consolidado: {csv_saida}")
    return lote


if __name__ == "__main__":
    args = sys.argv[1:]
    txts = [a for a in args if a.lower().endswith(".txt")]
    csvs = [a for a in args if a.lower().endswith(".csv")]
    saida = csvs[0] if csvs else None

    if len(txts) > 1:
        main_lote(txts, saida)
    elif len(txts) == 1:
        main(txts[0], saida)
    else:
        print("uso: python -m audita.cli arquivo.txt [saida.csv]")
        print("     python -m audita.cli arquivo1.txt arquivo2.txt [...] [saida.csv]  (lote)")
        sys.exit(1)
