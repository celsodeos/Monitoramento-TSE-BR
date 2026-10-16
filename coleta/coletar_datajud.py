#!/usr/bin/env python3
"""
Coleta na API pública do DataJud (CNJ) os metadados e andamentos dos processos
listados em numeros_datajud.csv.

Uso (Python 3.8+, sem bibliotecas extras). No repositório, a lista vem de
analise/indicadores.py (dados/derivados/numeros_datajud_tse.csv):
    python coletar_datajud.py                       # coleta tudo, na ordem de prioridade
    python coletar_datajud.py --prioridade-max 1    # só o TSE (≈2 mil processos)
    python coletar_datajud.py --prioridade-max 2    # TSE + TREs (≈29 mil)
    python coletar_datajud.py --teste 5             # testa com 5 processos
    python coletar_datajud.py --amostra 60          # testa 60 processos sorteados (todas as eleições e instâncias)

Pode ser interrompido (Ctrl+C) e retomado: os processos já coletados são pulados.
Saídas, na mesma pasta:
    datajud_resultados.jsonl.gz  -> um registro por processo (é este que você me envia)
    datajud_falhas.csv           -> processos não encontrados ou com erro
"""
import argparse, csv, gzip, json, os, sys, time, threading, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = "https://api-publica.datajud.cnj.jus.br/{endpoint}/_search"
CHAVE_PADRAO = "cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw=="  # chave pública divulgada pelo CNJ
CAMPOS = ["numeroProcesso", "tribunal", "grau", "classe", "assuntos", "orgaoJulgador",
          "dataAjuizamento", "dataHoraUltimaAtualizacao", "sistema", "formato", "nivelSigilo", "movimentos"]

def consultar(endpoint, numero, chave, tentativas=4):
    corpo = json.dumps({"query": {"match": {"numeroProcesso": numero}}, "size": 10}).encode()
    req = urllib.request.Request(BASE.format(endpoint=endpoint), data=corpo, method="POST",
                                 headers={"Authorization": f"APIKey {chave}", "Content-Type": "application/json"})
    espera = 2
    for t in range(tentativas):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r), None
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and t < tentativas - 1:
                time.sleep(espera); espera *= 2; continue
            return None, f"HTTP {e.code}"
        except Exception as e:  # rede, timeout
            if t < tentativas - 1:
                print(f"  aviso: {type(e).__name__} em {numero} — tentando de novo em {espera}s", flush=True)
                time.sleep(espera); espera *= 2; continue
            return None, type(e).__name__
    return None, "esgotou tentativas"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--entrada", default="numeros_datajud.csv")
    ap.add_argument("--saida", default="datajud_resultados.jsonl.gz")
    ap.add_argument("--falhas", default="datajud_falhas.csv")
    ap.add_argument("--chave", default=os.environ.get("DATAJUD_API_KEY", CHAVE_PADRAO))
    ap.add_argument("--prioridade-max", type=int, default=3, help="1=TSE, 2=+TREs, 3=+zonas")
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--teste", type=int, default=0, help="coleta só N processos")
    ap.add_argument("--eleicao", default="", help="ex.: 2022 ou 2018,2022")
    ap.add_argument("--amostra", type=int, default=0, help="coleta N processos sorteados, equilibrando eleição e instância")
    a = ap.parse_args()

    with open(a.entrada, encoding="utf-8") as f:
        linhas = [r for r in csv.DictReader(f) if int(r["prioridade"]) <= a.prioridade_max
                  and (not a.eleicao or r["eleicao"] in a.eleicao.split(","))]

    feitos = set()
    if os.path.exists(a.saida):
        try:
            with gzip.open(a.saida, "rt", encoding="utf-8") as f:
                for l in f:
                    try:
                        d = json.loads(l); feitos.add((d["endpoint"], d["numero_20dig"]))
                    except Exception:
                        pass  # linha truncada por interrupção: será recoletada
        except EOFError:
            pass
    pend = [r for r in linhas if (r["endpoint"], r["numero_20dig"]) not in feitos]
    if a.teste: pend = pend[:a.teste]
    if a.amostra:
        import random; random.seed(1)
        grupos = {}
        for r in pend: grupos.setdefault((r["eleicao"], r["prioridade"]), []).append(r)
        por = max(1, a.amostra // max(len(grupos), 1))
        pend = [x for g in grupos.values() for x in random.sample(g, min(por, len(g)))]
    print(f"{len(linhas)} no recorte | {len(feitos)} já coletados | {len(pend)} a coletar", flush=True)
    if not pend: return

    print("Consultando a API… o progresso aparece a cada 10 processos.", flush=True)
    trava = threading.Lock()
    nova_falha = not os.path.exists(a.falhas)
    out = gzip.open(a.saida, "at", encoding="utf-8")
    ff = open(a.falhas, "a", newline="", encoding="utf-8"); fw = csv.writer(ff)
    if nova_falha: fw.writerow(["endpoint", "numero_cnj", "erro"])
    ok = falhas = 0; t0 = time.time()

    UF = dict(zip(["01","02","03","04","05","06","07","08","09","10","11","12","13","14","15","16","17","18","19","20","21","22","23","24","25","26","27"],
                  ["ac","al","ap","am","ba","ce","df","es","go","ma","mt","ms","mg","pa","pb","pr","pe","pi","rj","rn","rs","ro","rr","sc","se","sp","to"]))
    def tarefa(r):
        res, err = consultar(r["endpoint"], r["numero_20dig"], a.chave)
        if not err and not (res or {}).get("hits", {}).get("hits"):
            uf = UF.get(r["numero_20dig"][14:16])
            alt = ("api_publica_tre-" + uf if uf else None) if r["endpoint"] == "api_publica_tse" else "api_publica_tse"
            if alt:
                res2, err2 = consultar(alt, r["numero_20dig"], a.chave)
                if not err2 and (res2 or {}).get("hits", {}).get("hits"):
                    r = dict(r, endpoint_encontrado=alt); return r, res2, None
        return r, res, err

    try:
        with ThreadPoolExecutor(max_workers=a.threads) as ex:
            futs = [ex.submit(tarefa, r) for r in pend]
            for i, fu in enumerate(as_completed(futs), 1):
                r, res, err = fu.result()
                hits = (res or {}).get("hits", {}).get("hits", [])
                with trava:
                    if err or not hits:
                        falhas += 1; fw.writerow([r["endpoint"], r["numero_cnj"], err or "não encontrado"])
                    else:
                        ok += 1
                    if not err:  # grava também 'não encontrado' para não repetir a consulta
                        reg = {k: r[k] for k in ("endpoint", "numero_cnj", "numero_20dig", "eleicao", "instancia", "classe", "tema")}
                        reg["endpoint_encontrado"] = r.get("endpoint_encontrado", r["endpoint"])
                        reg["hits"] = [{k: h.get("_source", {}).get(k) for k in CAMPOS} for h in hits]
                        out.write(json.dumps(reg, ensure_ascii=False) + "\n")
                    if i % 10 == 0 or i == len(pend) or i <= 3:
                        out.flush(); ff.flush()
                        v = i / max(time.time() - t0, 1)
                        print(f"{i}/{len(pend)}  encontrados={ok}  falhas={falhas}  ~{(len(pend)-i)/v/60:.0f} min restantes", flush=True)
    except KeyboardInterrupt:
        print("\nInterrompido. Rode de novo para continuar de onde parou.")
    finally:
        out.close(); ff.close()
    print(f"Fim. Envie o arquivo {a.saida}.")

if __name__ == "__main__":
    main()
