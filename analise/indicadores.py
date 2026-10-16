#!/usr/bin/env python3
"""
Gera os indicadores do estudo a partir dos dados brutos do SIG/TSE (dados/brutos)
e, se houver, dos resultados do DataJud (dados/brutos/datajud/*.jsonl.gz).

Uso:
    python analise/indicadores.py            # indicadores + lista para o DataJud
    python analise/indicadores.py --sem-historico

Saídas:
    dados/derivados/*.csv      tabelas do estudo e lista de processos para o DataJud
    docs/dados/*.csv           cópia lida pela página pública
    dados/historico/AAAA-MM-DD/  fotografia datada (data da carga do SIG)
"""
import argparse, glob, gzip, json, os, re, shutil, zlib
import numpy as np
import pandas as pd
from scipy.stats import fisher_exact
from statsmodels.stats.contingency_tables import StratifiedTable

RAIZ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
BRUTOS = os.path.join(RAIZ, "dados", "brutos")
DERIV = os.path.join(RAIZ, "dados", "derivados")
HIST = os.path.join(RAIZ, "dados", "historico")
DOCS = os.path.join(RAIZ, "docs", "dados")
ANOS = (2018, 2022, 2026)

# Dia do 1º turno (CF, art. 77) e do 2º turno (Lei 9.504/1997, art. 2º, § 1º)
T1 = {2018: "2018-10-07", 2022: "2022-10-02", 2026: "2026-10-04"}
T2 = {2018: "2018-10-28", 2022: "2022-10-30", 2026: "2026-10-25"}

# Presidência do TSE na data da autuação
PRESIDENCIAS = [("2018-08-14", "Luiz Fux"), ("2020-05-25", "Rosa Weber"), ("2022-08-16", "Edson Fachin"),
                ("2024-06-03", "Alexandre de Moraes"), ("2026-05-12", "Cármen Lúcia"), ("2100-01-01", "Nunes Marques")]

# Entidades centrais de cada campanha presidencial (partes principais)
CAMPANHAS = {
    2018: {"BOL": r"JAIR MESSIAS BOLSONARO|BRASIL ACIMA DE TUDO|PARTIDO SOCIAL LIBERAL \(PSL\) - NACIONAL|HAMILTON MARTINS MOUR|ELEICAO 2018 JAIR",
           "PT": r"PARTIDO DOS TRABALHADORES \(PT\) - NACIONAL|POVO FELIZ DE NOVO|LUIZ INACIO LULA DA SILVA|FERNANDO HADDAD|MANUELA PINTO VIEIRA|ELEICAO 2018 (FERNANDO HADDAD|LUIZ INACIO)"},
    2022: {"BOL": r"JAIR MESSIAS BOLSONARO|PELO BEM DO BRASIL|PARTIDO LIBERAL \(PL\) - NACIONAL|WALTER SOUZA BRAGA NETTO|ELEICAO 2022 JAIR",
           "PT": r"LUIZ INACIO LULA DA SILVA|COLIGA..O BRASIL DA ESPERAN|FEDERA..O BRASIL DA ESPERAN.*NACIONAL|PARTIDO DOS TRABALHADORES \(PT\) - NACIONAL|GERALDO JOSE RODRIGUES ALCKMIN|ELEICAO 2022 LUIZ INACIO"},
    2026: {"BOL": r"FLAVIO NANTES BOLSONARO|PARTIDO LIBERAL \(PL\) - NACIONAL|ELEICAO 2026 FLAVIO",
           "PT": r"LUIZ INACIO LULA DA SILVA|BRASIL PRONTO PRA MAIS|PARTIDO DOS TRABALHADORES \(PT\) - NACIONAL|GERALDO JOSE RODRIGUES ALCKMIN|FEDERA..O BRASIL DA ESPERAN.*NACIONAL|ELEICAO 2026 LUIZ INACIO"},
}

CL_CAMPANHA = ["REPRESENTAÇÃO", "REPRESENTAÇÃO ESPECIAL", "DIREITO DE RESPOSTA", "NOTÍCIA DE IRREGULARIDADE EM PROPAGANDA ELEITORAL",
               "TUTELA CAUTELAR ANTECEDENTE", "AÇÃO DE INVESTIGAÇÃO JUDICIAL ELEITORAL", "AÇÃO DE IMPUGNAÇÃO DE MANDATO ELETIVO",
               "RECURSO CONTRA EXPEDIÇÃO DE DIPLOMA"]
CL_RECURSOS = ["RECURSO ESPECIAL ELEITORAL", "RECURSO ORDINÁRIO ELEITORAL", "AGRAVO EM RECURSO ESPECIAL ELEITORAL",
               "RECURSO ELEITORAL", "AGRAVO DE INSTRUMENTO", "AGRAVO REGIMENTAL", "EMBARGOS DE DECLARAÇÃO"]
CL_ORIG_CAMP = ["REPRESENTAÇÃO", "REPRESENTAÇÃO ESPECIAL", "DIREITO DE RESPOSTA", "NOTÍCIA DE IRREGULARIDADE EM PROPAGANDA ELEITORAL",
                "AÇÃO DE INVESTIGAÇÃO JUDICIAL ELEITORAL", "TUTELA CAUTELAR ANTECEDENTE"]
CASS_CL = ["AÇÃO DE INVESTIGAÇÃO JUDICIAL ELEITORAL", "AÇÃO DE IMPUGNAÇÃO DE MANDATO ELETIVO", "RECURSO CONTRA EXPEDIÇÃO DE DIPLOMA",
           "REPRESENTAÇÃO", "REPRESENTAÇÃO ESPECIAL", "RECURSO ELEITORAL", "RECURSO ORDINÁRIO ELEITORAL", "RECURSO ESPECIAL ELEITORAL",
           "AGRAVO EM RECURSO ESPECIAL ELEITORAL", "AGRAVO DE INSTRUMENTO"]
TPU_LIMINAR = {339: "concedida", 892: "concedida em parte", 792: "não concedida"}


def ler(ano, tipo, usecols=None):
    arqs = sorted(glob.glob(os.path.join(BRUTOS, str(ano), tipo, "*.csv")))
    if not arqs:
        raise SystemExit(f"Faltam os dados brutos de {ano}/{tipo}. Rode: python coleta/baixar_sig.py --anos {ano}")
    df = pd.read_csv(arqs[0], sep=";", encoding="latin1", dtype=str, usecols=usecols)
    df["arq"] = ano
    return df


def nome(s):
    if not isinstance(s, str):
        return s
    menores = {"de", "da", "do", "das", "dos", "e"}
    return " ".join(p.lower() if p.lower() in menores else p.capitalize() for p in s.split())


def presidente(d):
    for lim, n in PRESIDENCIAS:
        if d < pd.Timestamp(lim):
            return n


# ---------------------------------------------------------------- processos e decisões
def preparar():
    P = pd.concat([ler(y, "processo") for y in ANOS], ignore_index=True)
    D = pd.concat([ler(y, "decisoes", ["Número do processo", "Instância", "Tipo da decisão", "Data da decisão", "Autor da decisão"])
                   for y in ANOS], ignore_index=True)
    carga = pd.to_datetime(P["Data de carga"], errors="coerce").max()
    P = P.rename(columns={"Assunto principal": "assunto", "Classe": "classe", "Instância": "inst", "Número do processo": "num",
                          "Tipo de origem": "origem", "Relator": "relator"})
    P["inst"] = P.inst.astype(int)
    P["aut"] = pd.to_datetime(P["Data de autuação"])
    P["dist"] = pd.to_datetime(P["Data de distribuição"], errors="coerce")
    P["inicio"] = pd.to_datetime(np.where(P.origem == "Recursal", P.dist.fillna(P.aut), P.aut))
    P["eleicao"] = P.arq.map(lambda y: pd.Timestamp(T1[y]))
    P["janela"] = (P.aut >= P.arq.map(lambda y: pd.Timestamp(f"{y}-07-20"))) & (P.aut < P.eleicao + pd.Timedelta(days=1))
    a, c = P.assunto.fillna(""), P.classe.fillna("")
    has = lambda s, pat: s.str.contains(pat, case=False, regex=True)
    crim = c.str.contains("CRIMINAL|INQUÉRITO|HABEAS|PENAL|CRIME|PIC-MP|TERMO CIRCUNSTANCIADO|AÇÃO PENAL", regex=True)
    dr = (c == "DIREITO DE RESPOSTA") | has(a, "^Direito de Resposta")
    cass = c.isin(CASS_CL[:3]) | (~crim & has(a, "^Captação Ilícita de Sufrágio$|^Captação ou Gasto Ilícito|^Conduta Vedada ao Agente Público|^Abuso - De Poder|^Abuso - Uso Indevido|^Ação de Impugnação de Mandato") & c.isin(CASS_CL))
    reg = (c == "REGISTRO DE CANDIDATURA") | has(a, "^Registro de Candidatura|^Impugnação ao Registro|^Inelegibilidade|^Condição de Elegibilidade|^Cancelamento de Registro de Candidatura")
    prop = (c == "NOTÍCIA DE IRREGULARIDADE EM PROPAGANDA ELEITORAL") | has(a, "^Propaganda")
    contas = has(a, "Contas|Prestação de Contas") | c.str.contains("CONTAS")
    pesq = has(a, "^Pesquisa Eleitoral")
    P["tema"] = "Outros"
    for lab, m in [("Crimes eleitorais", crim), ("Contas", contas), ("Pesquisas", pesq), ("Registro de candidatura", reg),
                   ("Propaganda irregular", prop), ("Ações cassatórias", cass), ("Direito de resposta", dr)]:
        P.loc[m, "tema"] = lab

    D = D.rename(columns={"Número do processo": "num", "Instância": "inst", "Tipo da decisão": "tipo", "Autor da decisão": "autor"})
    D["inst"] = D.inst.astype(int)
    D["data"] = pd.to_datetime(D["Data da decisão"], format="%d/%m/%Y", errors="coerce")
    k = ["arq", "num", "inst"]
    dd = D[D.tipo.isin(["Decisão", "Sentença", "Acórdão"])]
    P = P.merge(dd.groupby(k).data.min().rename("d1"), on=k, how="left")
    P["t1"] = (P.d1 - P.inicio.dt.normalize()).dt.days
    P.loc[P.t1 < 0, "t1"] = 0
    return P, D, carga


# ---------------------------------------------------------------- campanhas presidenciais
def campanhas(P, D):
    X = pd.concat([ler(y, "partes", ["NR_INSTANCIA", "NR_PROCESSO", "DS_POLO", "TP_PARTE", "ST_PARTE_PRINCIPAL", "NM_PARTE"]) for y in ANOS],
                  ignore_index=True)
    x = X[(X.NR_INSTANCIA == "3") & (X.ST_PARTE_PRINCIPAL == "S") & ~X.TP_PARTE.str.startswith("ADVOGADO", na=False)].copy()
    x["side"] = None
    for y, d in CAMPANHAS.items():
        for lado, pat in d.items():
            m = (x.arq == y) & x.NM_PARTE.str.upper().str.contains(pat, regex=True, na=False)
            x.loc[m & x.side.isna(), "side"] = lado
    x["polo"] = x.DS_POLO.map({"Pólo ativo": "A", "Pólo passivo": "P"})
    g = (x[x.side.notna() & x.polo.notna()].groupby(["arq", "NR_PROCESSO", "polo"]).side
         .agg(lambda s: "+".join(sorted(set(s)))).unstack().reset_index()
         .rename(columns={"NR_PROCESSO": "num", "A": "autor", "P": "reu"}))
    S = P[(P.inst == 3) & (P.origem == "Originário") & P.classe.isin(CL_ORIG_CAMP)
          & (P.aut >= P.arq.map(lambda y: pd.Timestamp(f"{y}-07-20")))
          & (P.aut < P.arq.map(lambda y: pd.Timestamp(T2[y])) + pd.Timedelta(days=1))].copy()
    S["turno"] = np.where(S.aut < S.eleicao + pd.Timedelta(days=1), "1º turno", "2º turno")
    S = S.merge(g, on=["arq", "num"], how="left")

    def direcao(r):
        a = r.autor if isinstance(r.autor, str) else ""
        b = r.reu if isinstance(r.reu, str) else ""
        if a == "PT" and "BOL" in b and "PT" not in b: return "PT→BOL"
        if a == "BOL" and "PT" in b and "BOL" not in b: return "BOL→PT"
        return None
    S["dir"] = S.apply(direcao, axis=1)
    S = S[S.dir.notna()].copy()
    S["tipo"] = S.classe.map({"DIREITO DE RESPOSTA": "DR", "REPRESENTAÇÃO": "Rep", "REPRESENTAÇÃO ESPECIAL": "Rep",
                              "NOTÍCIA DE IRREGULARIDADE EM PROPAGANDA ELEITORAL": "NIP", "AÇÃO DE INVESTIGAÇÃO JUDICIAL ELEITORAL": "AIJE",
                              "TUTELA CAUTELAR ANTECEDENTE": "Tutela"})
    S.loc[(S.arq == 2018) & S.assunto.str.startswith("Direito de Resposta", na=False), "tipo"] = "DR"
    S["presidente_tse"] = S.aut.map(presidente)
    S["ok3"], S["ok10"] = S.t1 <= 3, S.t1 <= 10

    d = D[D.inst == 3].merge(S[["arq", "num"]], on=["arq", "num"]).sort_values("data")
    fm = d[d.tipo == "Decisão"].groupby(["arq", "num"]).first().reset_index()[["arq", "num", "autor"]].rename(columns={"autor": "autor_mono"})
    fa = d[d.tipo.isin(["Decisão", "Sentença", "Acórdão"])].groupby(["arq", "num"]).first().reset_index()[["arq", "num", "autor"]].rename(columns={"autor": "autor_1ato"})
    S = S.merge(fm, on=["arq", "num"], how="left").merge(fa, on=["arq", "num"], how="left")
    S["relator_efetivo"] = S.autor_mono.fillna(S.autor_1ato).fillna(S.relator)
    return S


# ---------------------------------------------------------------- DataJud
def ler_jsonl_gz(caminho):
    dados = open(caminho, "rb").read(); txt = b""
    while dados:
        dz = zlib.decompressobj(16 + zlib.MAX_WBITS)
        txt += dz.decompress(dados); dados = dz.unused_data
    for l in txt.decode("utf-8", "replace").splitlines():
        if l.strip():
            try:
                yield json.loads(l)
            except Exception:
                pass


def liminares_datajud():
    regs = {}
    for f in sorted(glob.glob(os.path.join(BRUTOS, "datajud", "*.jsonl.gz"))):
        for j in ler_jsonl_gz(f):
            regs[(int(j["eleicao"]), j["numero_cnj"])] = j
    out = {}
    for k, j in regs.items():
        hits = [h for h in j.get("hits", []) if h.get("grau") == "SUP"]
        if not hits:
            out[k] = {"no_datajud": False}; continue
        ms = sorted(hits[0].get("movimentos") or [], key=lambda m: m.get("dataHora") or "")
        lims = [m for m in ms if m.get("codigo") in TPU_LIMINAR]
        out[k] = {"no_datajud": True, "lim_dec": bool(lims), "lim_conc": any(m["codigo"] in (339, 892) for m in lims),
                  "lim_1a": TPU_LIMINAR[lims[0]["codigo"]] if lims else None,
                  "lim_data": lims[0]["dataHora"] if lims else None}
    return out


# ---------------------------------------------------------------- testes
def testes(q, col):
    def tab(g):
        a, b = g[g.dir == "BOL→PT"][col], g[g.dir == "PT→BOL"][col]
        return np.array([[a.sum(), len(a) - a.sum()], [b.sum(), len(b) - b.sum()]], dtype=float)
    t = tab(q)
    if (t.sum(axis=1) == 0).any():
        return None, None
    p_f = fisher_exact(t)[1]
    estratos = [tab(g) for _, g in q.groupby(["relator_efetivo", "tipo"]) if g.dir.nunique() == 2]
    p_mh = None
    if estratos:
        try:
            p = StratifiedTable(estratos).test_null_odds().pvalue
            p_mh = None if np.isnan(p) else p
        except Exception:
            p_mh = None
    r = lambda v: None if v is None else (round(v, 5) if v < 0.001 else round(v, 3))
    return r(p_f), r(p_mh)


# ---------------------------------------------------------------- principal
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sem-historico", action="store_true")
    a = ap.parse_args()
    os.makedirs(DERIV, exist_ok=True); os.makedirs(DOCS, exist_ok=True)

    P, D, carga = preparar()
    J = P[P.janela]
    saidas = {}

    # 1. volume
    vol = pd.DataFrame({"ano": ANOS,
                        "total_justica_eleitoral": [int((J.arq == y).sum()) for y in ANOS]})
    camp = J[J.classe.isin(CL_CAMPANHA) | (J.classe.isin(CL_RECURSOS) & (J.tema != "Registro de candidatura"))]
    vol["tse_campanha"] = [int(((camp.arq == y) & (camp.inst == 3)).sum()) for y in ANOS]
    saidas["volume"] = vol

    # 2. velocidade TSE x TREs
    rows = []
    for y in ANOS:
        for inst, lab in [(2, "TREs"), (3, "TSE")]:
            q = camp[(camp.arq == y) & (camp.inst == inst)]
            n, a3, a10 = len(q), int((q.t1 <= 3).sum()), int((q.t1 <= 10).sum())
            rows.append({"ano": y, "tribunal": lab, "processos": n, "ate_3_dias": a3, "pct_ate_3_dias": round(a3 / n, 4),
                         "ate_10_dias": a10, "pct_ate_10_dias": round(a10 / n, 4)})
    saidas["tse_tres"] = pd.DataFrame(rows)

    # 3. campanhas
    S = campanhas(P, D)
    lim = liminares_datajud()
    for c in ("no_datajud", "lim_dec", "lim_conc", "lim_1a", "lim_data"):
        S[c] = [lim.get((r.arq, r.num), {}).get(c) for r in S.itertuples()]
    S1 = S[S.turno == "1º turno"]
    S1 = S1[(S1.arq != 2022) | (S1.presidente_tse == "Alexandre de Moraes")]
    rows = []
    for y in ANOS:
        q = S1[S1.arq == y]
        if q.empty: continue
        p3, p3mh = testes(q, "ok3"); p10, p10mh = testes(q, "ok10")
        for d, lado, suf in [("BOL→PT", "Bolsonaro / Flávio", "bol"), ("PT→BOL", "PT / Lula", "pt")]:
            g = q[q.dir == d]; n = len(g)
            rows.append({"id": f"{y}-{suf}", "ano": y, "presidente_tse": q.presidente_tse.mode()[0], "autor": lado, "processos": n,
                         "ate_3_dias": int(g.ok3.sum()), "pct_ate_3_dias": round(g.ok3.mean(), 4),
                         "ate_10_dias": int(g.ok10.sum()), "pct_ate_10_dias": round(g.ok10.mean(), 4),
                         "p_fisher_3d": p3, "p_mh_3d": p3mh, "p_fisher_10d": p10, "p_mh_10d": p10mh})
    saidas["campanhas"] = pd.DataFrame(rows)

    # 4. liminares (anos com cobertura mínima no DataJud)
    rows = []
    for y in ANOS:
        q = S1[(S1.arq == y) & (S1.no_datajud == True)].copy()
        if q.groupby("dir").size().reindex(["BOL→PT", "PT→BOL"]).fillna(0).min() < 10: continue
        q["lim_dec"] = q.lim_dec.astype(bool)
        pf, pmh = testes(q, "lim_dec")
        for d, lado, suf in [("BOL→PT", "Bolsonaro / Flávio", "bol"), ("PT→BOL", "PT / Lula", "pt")]:
            g = q[q.dir == d]; tot = int((S1[(S1.arq == y)].dir == d).sum())
            rows.append({"id": f"{y}-{suf}", "ano": y, "presidente_tse": q.presidente_tse.mode()[0], "autor": lado, "processos": tot,
                         "no_datajud": len(g), "liminar_decidida": int(g.lim_dec.sum()),
                         "liminar_concedida": int(g.lim_conc.fillna(False).astype(bool).sum()),
                         "pct_decidida": round(g.lim_dec.mean(), 4), "p_fisher": pf, "p_mh": pmh})
    saidas["liminares"] = pd.DataFrame(rows)

    # 5. gabinetes no último ano
    y = max(ANOS); q = S1[S1.arq == y]; rows = []
    for rel, g0 in q.groupby("relator_efetivo"):
        if len(g0) < 15 or g0.t1.notna().sum() == 0: continue
        for d, re_ in [("BOL→PT", "Lula"), ("PT→BOL", "Flávio Bolsonaro")]:
            g = g0[g0.dir == d]; n = len(g)
            if n == 0: continue
            dj = g[g.no_datajud == True]
            rows.append({"id": f"{nome(rel)}|{re_}", "relator": nome(rel), "campanha_re": re_, "processos": n,
                         "ate_3_dias": int(g.ok3.sum()), "pct_ate_3_dias": round(g.ok3.mean(), 4),
                         "ate_10_dias": int(g.ok10.sum()), "pct_ate_10_dias": round(g.ok10.mean(), 4),
                         "no_datajud": len(dj), "liminar_decidida": int(dj.lim_dec.fillna(False).astype(bool).sum()),
                         "liminar_concedida": int(dj.lim_conc.fillna(False).astype(bool).sum())})
    saidas[f"relatores_{y}"] = pd.DataFrame(rows)

    # processo a processo (1º e 2º turnos)
    pp = S.rename(columns={"arq": "eleicao", "num": "numero_cnj", "t1": "dias_ate_1a_decisao"})
    pp["autuacao"] = pp.aut.dt.strftime("%Y-%m-%d %H:%M")
    pp["direcao"] = pp.dir.map({"BOL→PT": "Bolsonaro/Flávio contra PT/Lula", "PT→BOL": "PT/Lula contra Bolsonaro/Flávio"})
    saidas["processos_campanhas"] = pp[["eleicao", "turno", "presidente_tse", "direcao", "numero_cnj", "classe", "relator", "relator_efetivo",
                                        "autuacao", "dias_ate_1a_decisao", "ok3", "ok10", "no_datajud", "lim_dec", "lim_conc", "lim_1a", "lim_data"]]

    # lista para o DataJud (ações entre as campanhas, todas as eleições e turnos)
    saidas["numeros_datajud_tse"] = pd.DataFrame({
        "prioridade": 1, "eleicao": S.arq, "instancia": 3, "endpoint": "api_publica_tse", "numero_cnj": S.num,
        "numero_20dig": S.num.str.replace(r"[.-]", "", regex=True), "classe": S.classe, "tema": S.turno})

    meta = {"carga_sig": str(carga), "gerado_em": pd.Timestamp.now(tz="America/Sao_Paulo").strftime("%Y-%m-%d %H:%M"),
            "processos_datajud": int(S.no_datajud.notna().sum())}
    for k, df in saidas.items():
        df.to_csv(os.path.join(DERIV, f"{k}.csv"), index=False)
        if k != "numeros_datajud_tse":
            df.to_csv(os.path.join(DOCS, f"{k}.csv"), index=False)
    for alvo in (DERIV, DOCS):
        json.dump(meta, open(os.path.join(alvo, "meta.json"), "w"), ensure_ascii=False, indent=1)
    if not a.sem_historico:
        h = os.path.join(HIST, carga.strftime("%Y-%m-%d"))
        os.makedirs(h, exist_ok=True)
        for k in saidas:
            if k != "numeros_datajud_tse":
                shutil.copy(os.path.join(DERIV, f"{k}.csv"), h)
        shutil.copy(os.path.join(DERIV, "meta.json"), h)
    for k in ("volume", "tse_tres", "campanhas", "liminares"):
        print(f"\n{k}\n", saidas[k].to_string(index=False))
    print("\n", meta)


if __name__ == "__main__":
    main()
