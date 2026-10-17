#!/usr/bin/env python3
"""
Consulta ao DataJud (CNJ) em lotes: até 100 números por requisição, em vez de um por vez.

Uso como script (mesmo formato de saída de coletar_datajud.py, lido pela análise):
    python coleta/datajud_lote.py --entrada dados/derivados/numeros_datajud_tse.csv \
        --saida dados/brutos/datajud/tse.jsonl.gz
Uso como módulo:
    from datajud_lote import consultar_lote
    achados, erro = consultar_lote("api_publica_tre-sp", ["0600..."], chave)
"""
import argparse, csv, gzip, json, os, sys, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from coletar_datajud import BASE, CAMPOS, CHAVE_PADRAO  # noqa: E402

UF = dict(zip([f"{i:02d}" for i in range(1, 28)],
              ["ac", "al", "ap", "am", "ba", "ce", "df", "es", "go", "ma", "mt", "ms", "mg", "pa", "pb", "pr", "pe", "pi", "rj", "rn",
               "rs", "ro", "rr", "sc", "se", "sp", "to"]))
LOTE = 100


def consultar_lote(endpoint, numeros, chave, tentativas=5):
    """Devolve ({numero_20dig: [hits]}, erro)."""
    corpo = json.dumps({"query": {"bool": {"should": [{"match": {"numeroProcesso": n}} for n in numeros],
                                           "minimum_should_match": 1}},
                        "size": max(10, len(numeros) * 4)}).encode()
    req = urllib.request.Request(BASE.format(endpoint=endpoint), data=corpo, method="POST",
                                 headers={"Authorization": f"APIKey {chave}", "Content-Type": "application/json"})
    espera = 3
    for t in range(tentativas):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                res = json.load(r)
            out = {}
            for h in res.get("hits", {}).get("hits", []):
                n = (h.get("_source") or {}).get("numeroProcesso")
                if n:
                    out.setdefault(n, []).append(h)
            return out, None
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and t < tentativas - 1:
                time.sleep(espera); espera *= 2; continue
            return {}, f"HTTP {e.code}"
        except Exception as e:
            if t < tentativas - 1:
                time.sleep(espera); espera *= 2; continue
            return {}, type(e).__name__
    return {}, "esgotou tentativas"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--entrada", required=True)
    ap.add_argument("--saida", required=True)
    ap.add_argument("--chave", default=os.environ.get("DATAJUD_API_KEY", CHAVE_PADRAO))
    ap.add_argument("--threads", type=int, default=4)
    a = ap.parse_args()
    with open(a.entrada, encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))
    por_ep = {}
    for r in linhas:
        por_ep.setdefault(r["endpoint"], []).append(r)
    lotes = [(ep, rs[i:i + LOTE]) for ep, rs in por_ep.items() for i in range(0, len(rs), LOTE)]
    print(f"{len(linhas)} processos em {len(lotes)} lotes", flush=True)
    resultado, erros = {}, 0
    t0 = time.time()

    def tarefa(ep, rs):
        achados, err = consultar_lote(ep, [r["numero_20dig"] for r in rs], a.chave)
        faltam = [r for r in rs if r["numero_20dig"] not in achados]
        # não encontrado no TSE: tenta o TRE de origem (código do tribunal no número CNJ)
        alt = {}
        if not err and ep == "api_publica_tse" and faltam:
            grupos = {}
            for r in faltam:
                uf = UF.get(r["numero_20dig"][14:16])
                if uf:
                    grupos.setdefault("api_publica_tre-" + uf, []).append(r)
            for ep2, rs2 in grupos.items():
                ach2, _ = consultar_lote(ep2, [r["numero_20dig"] for r in rs2], a.chave)
                for n, h in ach2.items():
                    alt[n] = (ep2, h)
        return rs, achados, alt, err

    with ThreadPoolExecutor(max_workers=a.threads) as ex:
        futs = [ex.submit(tarefa, ep, rs) for ep, rs in lotes]
        for i, fu in enumerate(as_completed(futs), 1):
            rs, achados, alt, err = fu.result()
            if err:
                erros += 1
                print(f"  lote com erro: {err}", flush=True)
                continue
            for r in rs:
                n = r["numero_20dig"]
                ep_enc, hits = (r["endpoint"], achados[n]) if n in achados else alt.get(n, (r["endpoint"], []))
                reg = {k: r.get(k) for k in ("endpoint", "numero_cnj", "numero_20dig", "eleicao", "instancia", "classe", "tema")}
                reg["endpoint_encontrado"] = ep_enc
                reg["hits"] = [{k: h.get("_source", {}).get(k) for k in CAMPOS} for h in hits]
                resultado[(r["eleicao"], n)] = reg
            if i % 10 == 0 or i == len(lotes):
                print(f"{i}/{len(lotes)} lotes | {(time.time()-t0)/60:.1f} min", flush=True)
    os.makedirs(os.path.dirname(a.saida) or ".", exist_ok=True)
    with gzip.open(a.saida, "wt", encoding="utf-8") as f:
        for reg in resultado.values():
            f.write(json.dumps(reg, ensure_ascii=False) + "\n")
    enc = sum(1 for r in resultado.values() if r["hits"])
    print(f"::notice title=DataJud {os.path.basename(a.entrada)}::{enc}/{len(linhas)} encontrados; {erros} lotes com erro; "
          f"{(time.time()-t0)/60:.1f} min")


if __name__ == "__main__":
    main()
