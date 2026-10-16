#!/usr/bin/env python3
"""
Envia as tabelas de dados/derivados para o banco do projeto no Supabase,
registrando a carga (data da extração do TSE) para manter o histórico.

Variáveis de ambiente (no GitHub: Settings → Secrets and variables → Actions):
    SUPABASE_URL                 ex.: https://wmtjybayqqpjiayjvswd.supabase.co
    SUPABASE_SERVICE_ROLE_KEY    chave de serviço (nunca publicar)

Uso:
    python analise/enviar_supabase.py
Só usa a biblioteca padrão do Python.
"""
import csv, json, math, os, sys, urllib.request

RAIZ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DERIV = os.path.join(RAIZ, "dados", "derivados")
URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
CHAVE = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

TABELAS = {  # arquivo -> (tabela, colunas extras fixas)
    "volume.csv": ("volume", {}),
    "tse_tres.csv": ("tse_tres", {}),
    "campanhas.csv": ("campanhas", {}),
    "liminares.csv": ("liminares", {}),
    "relatores_2026.csv": ("relatores", {"ano": 2026}),
    "processos_campanhas.csv": ("processos_campanhas", {}),
}


def req(metodo, caminho, corpo=None, prefer="return=minimal"):
    r = urllib.request.Request(f"{URL}/rest/v1/{caminho}", method=metodo,
                               data=None if corpo is None else json.dumps(corpo).encode(),
                               headers={"apikey": CHAVE, "Authorization": f"Bearer {CHAVE}",
                                        "Content-Type": "application/json", "Prefer": prefer})
    with urllib.request.urlopen(r, timeout=120) as resp:
        txt = resp.read().decode()
        return json.loads(txt) if txt else None


def valor(v):
    if v is None or v == "" or v == "nan":
        return None
    if v in ("True", "False"):
        return v == "True"
    return v


def main():
    if not URL or not CHAVE:
        print("SUPABASE_URL ou SUPABASE_SERVICE_ROLE_KEY ausentes: envio ao Supabase ignorado.")
        return
    meta = json.load(open(os.path.join(DERIV, "meta.json")))
    carga = req("POST", "cargas?on_conflict=carga_sig",
                [{"carga_sig": meta["carga_sig"] + "-03:00",  # horário de Brasília "processos_datajud": meta.get("processos_datajud"),
                  "observacao": f"gerado em {meta['gerado_em']}"}],
                prefer="resolution=merge-duplicates,return=representation")[0]
    cid = carga["id"]
    for arq, (tab, extras) in TABELAS.items():
        caminho = os.path.join(DERIV, arq)
        if not os.path.exists(caminho):
            continue
        with open(caminho, encoding="utf-8") as f:
            linhas = [{**{k: valor(v) for k, v in r.items()}, **extras, "carga_id": cid} for r in csv.DictReader(f)]
        for i in range(0, len(linhas), 500):
            req("POST", tab, linhas[i:i + 500], prefer="resolution=merge-duplicates,return=minimal")
        print(f"{tab}: {len(linhas)} linhas (carga {cid})")


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as e:
        print("Erro do Supabase:", e.code, e.read().decode()[:500]); sys.exit(1)
