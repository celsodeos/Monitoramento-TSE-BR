#!/usr/bin/env python3
"""
Coleta semanal no DataJud (CNJ) dos processos de campanha nos TREs.

Lê a lista gerada por analise/indicadores.py (dados/brutos/numeros_datajud_tres.csv)
e mantém um estado versionado em dados/derivados/datajud_tres_status.csv, um processo
por linha, com o que foi encontrado no DataJud. A cada execução consulta:
  - processos nunca consultados;
  - todos os processos da eleição mais recente (os andamentos ainda mudam);
  - processos não encontrados, consultados há mais de 7 dias.
Processos de eleições anteriores já encontrados não são consultados de novo.

Uso:
    python coleta/datajud_tres.py --threads 6 --minutos 300
Gera também dados/derivados/liminares_tres.csv (resumo por eleição).
"""
import argparse, csv, os, sys, threading, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from coletar_datajud import consultar, CHAVE_PADRAO  # noqa: E402

RAIZ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
LISTA = os.path.join(RAIZ, "dados", "brutos", "numeros_datajud_tres.csv")
ESTADO = os.path.join(RAIZ, "dados", "derivados", "datajud_tres_status.csv")
RESUMO = os.path.join(RAIZ, "dados", "derivados", "liminares_tres.csv")

LIMINAR = {339: "concedida", 892: "concedida em parte", 792: "não concedida"}
RESULTADO = {219: "procedência", 220: "improcedência", 221: "procedência em parte", 237: "provimento",
             238: "provimento em parte", 239: "não provimento", 236: "negação de seguimento",
             901: "negação de seguimento", 235: "não conhecimento", 12325: "perda do objeto"}
CAMPOS = ["eleicao", "numero_cnj", "endpoint", "classe", "tema", "encontrado", "consultado_em", "ultima_atualizacao_datajud",
          "n_movimentos", "lim_dec", "lim_conc", "lim_1a", "lim_data", "resultado_1o", "resultado_data"]


def resumir(hits):
    h = [x.get("_source", {}) for x in hits if x.get("_source", {}).get("grau") in ("G2", "SUP", None)] or \
        [x.get("_source", {}) for x in hits]
    if not h:
        return {"encontrado": "não"}
    s = h[0]
    ms = sorted(s.get("movimentos") or [], key=lambda m: m.get("dataHora") or "")
    lim = [m for m in ms if m.get("codigo") in LIMINAR]
    res = [m for m in ms if m.get("codigo") in RESULTADO]
    return {"encontrado": "sim", "ultima_atualizacao_datajud": s.get("dataHoraUltimaAtualizacao", ""), "n_movimentos": len(ms),
            "lim_dec": "sim" if lim else "não", "lim_conc": "sim" if any(m["codigo"] in (339, 892) for m in lim) else "não",
            "lim_1a": LIMINAR[lim[0]["codigo"]] if lim else "", "lim_data": lim[0].get("dataHora", "") if lim else "",
            "resultado_1o": RESULTADO[res[0]["codigo"]] if res else "", "resultado_data": res[0].get("dataHora", "") if res else ""}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--threads", type=int, default=6)
    ap.add_argument("--minutos", type=float, default=300, help="tempo máximo; ao atingir, salva e encerra")
    ap.add_argument("--chave", default=os.environ.get("DATAJUD_API_KEY", CHAVE_PADRAO))
    a = ap.parse_args()

    with open(LISTA, encoding="utf-8") as f:
        lista = list(csv.DictReader(f))
    estado = {}
    if os.path.exists(ESTADO):
        with open(ESTADO, encoding="utf-8") as f:
            estado = {(r["eleicao"], r["numero_cnj"]): r for r in csv.DictReader(f)}
    agora = datetime.now(timezone.utc)
    recente = max(r["eleicao"] for r in lista)

    def precisa(r):
        e = estado.get((r["eleicao"], r["numero_cnj"]))
        if not e or not e.get("consultado_em"):
            return True
        if r["eleicao"] == recente:
            return True
        if e.get("encontrado") != "sim":
            return datetime.fromisoformat(e["consultado_em"]) < agora - timedelta(days=7)
        return False

    pend = [r for r in lista if precisa(r)]
    pend.sort(key=lambda r: (r["eleicao"] != recente, (r["eleicao"], r["numero_cnj"]) in estado))  # novos e recentes primeiro
    print(f"{len(lista)} processos na lista | {len(pend)} a consultar nesta execução", flush=True)

    trava, t0, feitos, achados, erros = threading.Lock(), time.time(), 0, 0, 0
    parar = threading.Event()

    def tarefa(r):
        if parar.is_set():
            return r, None, "interrompido"
        res, err = consultar(r["endpoint"], r["numero_20dig"], a.chave)
        return r, res, err

    with ThreadPoolExecutor(max_workers=a.threads) as ex:
        futs = [ex.submit(tarefa, r) for r in pend]
        for fu in as_completed(futs):
            r, res, err = fu.result()
            if err == "interrompido":
                continue
            with trava:
                feitos += 1
                if err:
                    erros += 1
                else:
                    reg = {k: r.get(k, "") for k in ("eleicao", "numero_cnj", "endpoint", "classe", "tema")}
                    reg.update(resumir((res or {}).get("hits", {}).get("hits", [])))
                    reg["consultado_em"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
                    achados += reg["encontrado"] == "sim"
                    estado[(r["eleicao"], r["numero_cnj"])] = reg
                if feitos % 500 == 0:
                    print(f"{feitos}/{len(pend)} consultados | encontrados={achados} | erros={erros} | {(time.time()-t0)/60:.0f} min", flush=True)
                if time.time() - t0 > a.minutos * 60 and not parar.is_set():
                    print("Tempo máximo atingido: salvando e encerrando; a próxima execução continua.", flush=True)
                    parar.set()

    os.makedirs(os.path.dirname(ESTADO), exist_ok=True)
    linhas = sorted(estado.values(), key=lambda r: (r["eleicao"], r["numero_cnj"]))
    with open(ESTADO, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS, extrasaction="ignore"); w.writeheader(); w.writerows(linhas)

    # resumo por eleição
    tot = {}
    for r in lista:
        tot.setdefault(r["eleicao"], 0); tot[r["eleicao"]] += 1
    res = []
    for ano in sorted(tot):
        rs = [r for r in linhas if r["eleicao"] == ano]
        enc = [r for r in rs if r.get("encontrado") == "sim"]
        dec = [r for r in enc if r.get("lim_dec") == "sim"]
        con = [r for r in enc if r.get("lim_conc") == "sim"]
        res.append({"ano": ano, "processos_tres": tot[ano], "consultados": len(rs), "no_datajud": len(enc),
                    "pct_no_datajud": round(len(enc) / tot[ano], 4) if tot[ano] else "",
                    "liminar_decidida": len(dec), "liminar_concedida": len(con),
                    "pct_liminar_decidida": round(len(dec) / len(enc), 4) if enc else ""})
    with open(RESUMO, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(res[0])); w.writeheader(); w.writerows(res)
    print(f"Fim: {feitos} consultados, {achados} encontrados, {erros} erros. Resumo em {os.path.relpath(RESUMO, RAIZ)}")
    print("::notice title=DataJud TREs::" + " | ".join(f"{r['ano']}: {r['no_datajud']}/{r['processos_tres']} no DataJud, "
                                                      f"{r['liminar_decidida']} com liminar apreciada" for r in res))


if __name__ == "__main__":
    main()
