#!/usr/bin/env python3
"""
Indicadores do 2º turno: ações entre as duas campanhas presidenciais no TSE,
autuadas do dia seguinte ao 1º turno até o dia do 2º turno (2018, 2022 e 2026).

Lê dados/derivados/processos_campanhas.csv (gerado por indicadores.py) e grava
em dados/derivados e docs/dados os arquivos 2t_*.csv e 2t_meta.json.

Em 2026 o 2º turno está em curso: só entram no cálculo de "decidido em até N dias"
os processos que já tinham N dias de tramitação na data da carga do TSE.
"""
import json, os
import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency, fisher_exact
from statsmodels.stats.contingency_tables import StratifiedTable

RAIZ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DERIV = os.path.join(RAIZ, "dados", "derivados")
DOCS = os.path.join(RAIZ, "docs", "dados")
LADOS = [("bol", "Bolsonaro / Flávio", "Bolsonaro/Flávio contra PT/Lula"), ("pt", "PT / Lula", "PT/Lula contra Bolsonaro/Flávio")]
T2 = {2018: "2018-10-28", 2022: "2022-10-30", 2026: "2026-10-25"}


def nome(s):
    if not isinstance(s, str):
        return s
    menores = {"de", "da", "do", "das", "dos", "e"}
    return " ".join(p.lower() if p.lower() in menores else p.capitalize() for p in s.split())


def bool_(s):
    return s.map({True: True, False: False, "True": True, "False": False})


def testes(q, col):
    q = q[q[col].notna()].copy(); q[col] = q[col].astype(bool)
    a, b = q[q.lado == "bol"][col], q[q.lado == "pt"][col]
    if len(a) == 0 or len(b) == 0:
        return None, None
    pf = fisher_exact([[a.sum(), len(a) - a.sum()], [b.sum(), len(b) - b.sum()]])[1]
    tabs = []
    for _, g in q.groupby(["relator_efetivo", "classe"]):
        x, y = g[g.lado == "bol"][col], g[g.lado == "pt"][col]
        if len(x) and len(y):
            tabs.append(np.array([[x.sum(), len(x) - x.sum()], [y.sum(), len(y) - y.sum()]], float))
    pm = None
    if tabs:
        try:
            v = StratifiedTable(tabs).test_null_odds().pvalue
            pm = None if np.isnan(v) else v
        except Exception:
            pass
    r = lambda v: None if v is None else (float(f"{v:.2g}") if v < 0.001 else round(v, 3))
    return r(pf), r(pm)


def main():
    meta0 = json.load(open(os.path.join(DERIV, "meta.json")))
    carga = pd.Timestamp(meta0["carga_sig"]).normalize()
    d = pd.read_csv(os.path.join(DERIV, "processos_campanhas.csv"))
    d = d[d.turno == "2º turno"].copy()
    d["aut"] = pd.to_datetime(d.autuacao).dt.normalize()
    d["obs"] = (carga - d.aut).dt.days
    d["lado"] = d.direcao.map({v: k for k, _, v in LADOS})
    for c in ("ok3", "ok10", "no_datajud", "lim_dec", "lim_conc"):
        d[c] = bool_(d[c])
    d["sem_decisao"] = d.dias_ate_1a_decisao.isna()
    anos = sorted(d.eleicao.unique())

    vel, lim, vol = [], [], []
    for y in anos:
        q = d[d.eleicao == y]
        q3, q10 = q[q.obs >= 3], q[q.obs >= 10]
        p3, m3 = testes(q3, "ok3"); p10, m10 = testes(q10, "ok10")
        dj = q[q.no_datajud == True]
        pl, ml = testes(dj, "lim_dec")
        pres = q.presidente_tse.mode()[0]
        for k, lab, _ in LADOS:
            g, g3, g10, gj = q[q.lado == k], q3[q3.lado == k], q10[q10.lado == k], dj[dj.lado == k]
            vol.append({"id": f"{y}-{k}", "ano": y, "presidente_tse": pres, "autor": lab, "processos": len(g),
                        "sem_decisao": int(g.sem_decisao.sum())})
            vel.append({"id": f"{y}-{k}", "ano": y, "presidente_tse": pres, "autor": lab, "processos": len(g),
                        "observaveis_3d": len(g3), "ate_3_dias": int(g3.ok3.sum()),
                        "pct_ate_3_dias": round(g3.ok3.mean(), 4) if len(g3) else None,
                        "observaveis_10d": len(g10), "ate_10_dias": int(g10.ok10.sum()),
                        "pct_ate_10_dias": round(g10.ok10.mean(), 4) if len(g10) else None,
                        "p_fisher_3d": p3, "p_mh_3d": m3, "p_fisher_10d": p10, "p_mh_10d": m10})
            lim.append({"id": f"{y}-{k}", "ano": y, "presidente_tse": pres, "autor": lab, "processos": len(g), "no_datajud": len(gj),
                        "liminar_decidida": int(gj.lim_dec.fillna(False).astype(bool).sum()),
                        "liminar_concedida": int(gj.lim_conc.fillna(False).astype(bool).sum()),
                        "pct_decidida": round(gj.lim_dec.fillna(False).astype(bool).mean(), 4) if len(gj) else None,
                        "p_fisher": pl, "p_mh": ml})

    # gabinetes na eleição mais recente
    y = max(anos); q = d[d.eleicao == y]; rel = []
    for r, g0 in q.groupby("relator_efetivo"):
        if len(g0) < 5:
            continue
        for k, re_ in (("bol", "Lula"), ("pt", "Flávio Bolsonaro")):
            g = g0[g0.lado == k]; g3 = g[g.obs >= 3]
            rel.append({"id": f"{nome(r)}|{re_}", "relator": nome(r), "campanha_re": re_, "processos": len(g),
                        "observaveis_3d": len(g3), "ate_3_dias": int(g3.ok3.sum()),
                        "pct_ate_3_dias": round(g3.ok3.mean(), 4) if len(g3) else None,
                        "sem_decisao": int(g.sem_decisao.sum())})
    R = pd.DataFrame(rel)
    tab = R.pivot(index="relator", columns="campanha_re", values="processos").fillna(0)
    p_dist = float(chi2_contingency(tab.values)[1]) if tab.shape[0] > 1 else None

    meta = {"carga_sig": meta0["carga_sig"], "gerado_em": meta0["gerado_em"], "ano_atual": int(y),
            "segundo_turno_atual": T2[int(y)], "em_curso": bool(carga < pd.Timestamp(T2[int(y)]) + pd.Timedelta(days=1)),
            "autuacao_ate": str(d[d.eleicao == y].aut.max().date()),
            "p_distribuicao_relatores": None if p_dist is None else (round(p_dist, 8) if p_dist < 0.001 else round(p_dist, 3)),
            "processos_atual": int((d.eleicao == y).sum())}
    saidas = {"2t_volume": pd.DataFrame(vol), "2t_velocidade": pd.DataFrame(vel), "2t_liminares": pd.DataFrame(lim),
              f"2t_relatores": R}
    for k, df in saidas.items():
        for alvo in (DERIV, DOCS):
            df.to_csv(os.path.join(alvo, f"{k}.csv"), index=False)
    for alvo in (DERIV, DOCS):
        json.dump(meta, open(os.path.join(alvo, "2t_meta.json"), "w"), ensure_ascii=False, indent=1)
    print(pd.DataFrame(vel).to_string(index=False)); print(R.to_string(index=False)); print(meta)
    print("::notice title=2º turno::" + f"{meta['processos_atual']} ações em {y}; distribuição entre relatores p={meta['p_distribuicao_relatores']}")


if __name__ == "__main__":
    main()
