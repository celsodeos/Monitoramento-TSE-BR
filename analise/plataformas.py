#!/usr/bin/env python3
"""
Ações contra plataformas digitais (big techs) e meios de comunicação.

Identifica, nos arquivos de partes do TSE, as empresas no polo passivo dos processos
autuados de 20/07 ao dia do 1º turno, em todas as instâncias, e cruza com o DataJud
(processos do TSE) para medir liminares concedidas e desfechos.

Uso:
    python analise/plataformas.py
Saídas (dados/derivados e docs/dados):
    plataformas.csv            processos por empresa, eleição e instância
    plataformas_servico.csv    Meta e Google por serviço (quando identificável) e eleição
    plataformas_tse.csv        TSE: liminar e desfecho por empresa e eleição (DataJud)
    midia.csv                  processos contra veículos de comunicação, por eleição e instância
    midia_empresas.csv         veículos mais acionados por eleição
    numeros_datajud_plataformas.csv  lista do TSE para a consulta ao DataJud
"""
import glob, os, sys
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import indicadores as ind  # noqa: E402

PLATAFORMAS = [
    ("Meta (Facebook, Instagram, WhatsApp)", r"FACEBOOK SERVICOS ONLINE|META PLATFORMS|^FACEBOOK|INSTAGRAM|WHATSAPP"),
    ("Google (Google, YouTube)", r"GOOGLE BRASIL|GOOGLE LLC|^GOOGLE|YOUTUBE"),
    ("X (Twitter)", r"TWITTER|X BRASIL INTERNET|X CORP"),
    ("TikTok (ByteDance)", r"BYTEDANCE|TIKTOK|TIK TOK"),
    ("Kwai", r"JOYO TECNOLOGIA|KUAISHOU|\bKWAI\b"),
    ("Telegram", r"TELEGRAM"),
    ("Microsoft (LinkedIn)", r"MICROSOFT|LINKEDIN"),
    ("Spotify", r"SPOTIFY"),
    ("Discord", r"DISCORD"),
    ("Amazon", r"AMAZON SERVICOS|AMAZON\.COM|AMAZON WEB"),
    ("Gettr / Rumble", r"GETTR|RUMBLE"),
]
MIDIA = (r"\bRADIO\b|TELEVISAO|\bTV\b|RADIODIFUS|EMISSORA|\bJORNAL\b|EDITORA|GLOBO COMUNICACAO|RECORD|"
         r"SISTEMA BRASILEIRO DE TELEVISAO|BANDEIRANTES|REDETV|JOVEM PAN|CNN BRASIL|FOLHA DA MANHA|"
         r"S\.?A\.? O ESTADO DE S|PORTAL|NOTICIAS|\bNEWS\b|COMUNICACAO LTDA|COMUNICACOES")
NAO_MIDIA = r"PARTIDO|COLIGACAO|FEDERACAO|ELEICAO 20|PROMOTOR|MINISTERIO|PROCURADORIA"
DESFECHO = {219: "procedência", 221: "procedência em parte", 220: "improcedência", 237: "provimento",
            238: "provimento em parte", 239: "não provimento", 236: "negação de seguimento", 901: "negação de seguimento",
            235: "não conhecimento", 12325: "perda do objeto"}
INST = {1: "Zonas eleitorais", 2: "TREs", 3: "TSE"}


def datajud_tse():
    regs = {}
    for f in sorted(glob.glob(os.path.join(ind.BRUTOS, "datajud", "*.jsonl.gz"))):
        for j in ind.ler_jsonl_gz(f):
            h = [x for x in j.get("hits", []) if x.get("grau") == "SUP"]
            if not h:
                regs.setdefault((int(j["eleicao"]), j["numero_cnj"]), None); continue
            cods = [m.get("codigo") for m in sorted(h[0].get("movimentos") or [], key=lambda m: m.get("dataHora") or "")]
            fin = [DESFECHO[c] for c in cods if c in DESFECHO]
            regs[(int(j["eleicao"]), j["numero_cnj"])] = {
                "liminar": "concedida" if (339 in cods or 892 in cods) else ("negada" if 792 in cods else "sem decisão"),
                "desfecho": fin[-1] if fin else "sem desfecho registrado"}
    return regs


def main():
    P, D, carga = ind.preparar()
    J = P[P.janela][["arq", "num", "inst", "classe", "tema"]]
    X = pd.concat([ind.ler(y, "partes", ["NR_INSTANCIA", "NR_PROCESSO", "DS_POLO", "TP_PARTE", "NM_PARTE"]) for y in ind.ANOS],
                  ignore_index=True)
    x = X[(X.DS_POLO == "Pólo passivo") & ~X.TP_PARTE.str.startswith("ADVOGADO", na=False)].copy()
    x["inst"] = x.NR_INSTANCIA.astype(int)
    x["nm"] = x.NM_PARTE.str.upper().str.normalize("NFKD").str.encode("ascii", "ignore").str.decode("ascii")
    x["empresa"] = None
    for lab, pat in PLATAFORMAS:
        x.loc[x.empresa.isna() & x.nm.str.contains(pat, regex=True, na=False), "empresa"] = lab
    # perfis, canais e páginas de usuários ("responsável pelo perfil @x no TikTok") não são a empresa
    usuario = x.nm.str.contains(r"PERFIL|CANAL|RESPONSAV|@|HTTP|PAGINA|ADMINISTRADOR|URL", regex=True, na=False)
    x.loc[usuario, "empresa"] = None
    x["midia"] = x.empresa.isna() & x.nm.str.contains(MIDIA, regex=True, na=False) & ~x.nm.str.contains(NAO_MIDIA, regex=True, na=False)
    k = x.merge(J, left_on=["arq", "NR_PROCESSO", "inst"], right_on=["arq", "num", "inst"])

    bt = k[k.empresa.notna()].drop_duplicates(["arq", "num", "inst", "empresa"])
    tab = (bt.groupby(["arq", "empresa", "inst"]).size().rename("processos").reset_index()
           .assign(instancia=lambda d: d.inst.map(INST)).rename(columns={"arq": "ano"}))
    tot = bt.drop_duplicates(["arq", "num", "inst"]).groupby("arq").size()
    saidas = {"plataformas": tab[["ano", "empresa", "instancia", "processos"]]}

    # serviço: a parte costuma ser a pessoa jurídica brasileira (Facebook Serviços Online do Brasil
    # responde por Facebook e Instagram; Google Brasil Internet por Google e YouTube). O serviço só é
    # identificável pelo nome da própria parte ou pela menção ao serviço em outra parte do mesmo processo.
    srv = bt[bt.empresa.isin([PLATAFORMAS[0][0], PLATAFORMAS[1][0]])][["arq", "num", "inst", "empresa", "nm"]].copy()
    outros = (k.groupby(["arq", "num", "inst"]).nm.apply(lambda v: " | ".join(v)).rename("todas").reset_index())
    srv = srv.merge(outros, on=["arq", "num", "inst"], how="left")
    linhas = []
    for r in srv.itertuples():
        cands = ([("WhatsApp", "WHATSAPP"), ("Instagram", "INSTAGRAM"), ("Facebook", "FACEBOOK")]
                 if r.empresa == PLATAFORMAS[0][0] else [("YouTube", "YOUTUBE")])
        proprio = [lab for lab, pat in cands if pat in r.nm and not (lab == "Facebook" and "FACEBOOK SERVICOS" in r.nm)]
        outra = [lab for lab, pat in cands
                 if any(pat in p_ and not p_.startswith("FACEBOOK SERVICOS") for p_ in r.todas.split(" | ") if p_ != r.nm)]
        achou = proprio or outra
        for lab in (achou or ["não identificado"]):
            linhas.append({"ano": r.arq, "grupo": r.empresa, "instancia": INST[r.inst], "num": r.num, "servico": lab,
                           "identificado_por": "nome da parte" if proprio else ("outra parte do processo" if outra else "")})
    S = pd.DataFrame(linhas).drop_duplicates(["ano", "num", "instancia", "servico"])
    saidas["plataformas_servico"] = (S.groupby(["ano", "grupo", "instancia", "servico", "identificado_por"]).size()
                                     .rename("processos").reset_index())

    md = k[k.midia].drop_duplicates(["arq", "num", "inst"])
    saidas["midia"] = (md.groupby(["arq", "inst"]).size().rename("processos").reset_index()
                       .assign(instancia=lambda d: d.inst.map(INST)).rename(columns={"arq": "ano"})[["ano", "instancia", "processos"]])
    me = k[k.midia].drop_duplicates(["arq", "num", "inst", "NM_PARTE"])
    saidas["midia_empresas"] = (me.groupby(["arq", "NM_PARTE"]).size().rename("processos").reset_index()
                                .sort_values(["arq", "processos"], ascending=[True, False]).groupby("arq").head(20)
                                .rename(columns={"arq": "ano", "NM_PARTE": "empresa"}))

    # TSE: liminar e desfecho (DataJud)
    dj = datajud_tse()
    t = bt[bt.inst == 3].copy()
    t["dj"] = [dj.get((r.arq, r.num), "não consultado") for r in t.itertuples()]
    t["no_datajud"] = t.dj.map(lambda v: isinstance(v, dict))
    t["liminar"] = t.dj.map(lambda v: v["liminar"] if isinstance(v, dict) else None)
    t["desfecho"] = t.dj.map(lambda v: v["desfecho"] if isinstance(v, dict) else None)
    rows = []
    for (ano, emp), g in t.groupby(["arq", "empresa"]):
        e = g[g.no_datajud]
        rows.append({"ano": ano, "empresa": emp, "processos_tse": len(g), "no_datajud": len(e),
                     "liminar_concedida": int((e.liminar == "concedida").sum()), "liminar_negada": int((e.liminar == "negada").sum()),
                     "procedencia_total_ou_parcial": int(e.desfecho.isin(["procedência", "procedência em parte"]).sum()),
                     "improcedencia": int((e.desfecho == "improcedência").sum()),
                     "perda_do_objeto": int((e.desfecho == "perda do objeto").sum()),
                     "sem_desfecho": int((e.desfecho == "sem desfecho registrado").sum())})
    saidas["plataformas_tse"] = pd.DataFrame(rows)

    # lista do TSE (plataformas e mídia) para a consulta ao DataJud
    lt = pd.concat([bt[bt.inst == 3], md[md.inst == 3]]).drop_duplicates(["arq", "num"])
    saidas["numeros_datajud_plataformas"] = pd.DataFrame({
        "prioridade": 1, "eleicao": lt.arq, "instancia": 3, "endpoint": "api_publica_tse", "numero_cnj": lt.num,
        "numero_20dig": lt.num.str.replace(r"[.-]", "", regex=True), "classe": lt.classe, "tema": "plataformas e mídia"})

    for nome_, df in saidas.items():
        df.to_csv(os.path.join(ind.DERIV, f"{nome_}.csv"), index=False)
        if nome_ != "numeros_datajud_plataformas":
            df.to_csv(os.path.join(ind.DOCS, f"{nome_}.csv"), index=False)
    print("Processos com plataforma no polo passivo (1º turno):", tot.to_dict())
    print(saidas["plataformas_tse"].to_string(index=False))
    print("::notice title=plataformas::" + " | ".join(f"{a}: {n} processos" for a, n in tot.items()))


if __name__ == "__main__":
    main()
