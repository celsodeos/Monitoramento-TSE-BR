"""Monitor de menções ao estudo em vídeos do YouTube.

Lista os vídeos recentes dos canais de monitor_midia/canais.yml, baixa as legendas
(manuais ou automáticas, em português) com yt-dlp e procura "Nunes Marques" perto de
termos associados ao estudo. Cada ocorrência sai com o link já no minuto exato.

Saídas (nada em docs/, as páginas públicas não são tocadas):
  monitor_midia/mencoes.csv            acumulado de ocorrências
  monitor_midia/relatorios/AAAA-MM-DD.md  relatório do dia (só quando há ocorrência nova)
  monitor_midia/estado.json            vídeos já processados

Uso:
  python monitor_midia/monitorar.py                 # todos os canais, vídeos dos últimos 3 dias
  python monitor_midia/monitorar.py --dias 7
  python monitor_midia/monitorar.py --video s6s-jia_naA   # analisa um vídeo só (teste)
  python monitor_midia/monitorar.py --cookies cookies.txt  # se o YouTube pedir login
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

import yaml
import yt_dlp

RAIZ = Path(__file__).resolve().parent
ESTADO = RAIZ / "estado.json"
MENCOES = RAIZ / "mencoes.csv"
RELATORIOS = RAIZ / "relatorios"

JANELA_S = 60          # distância máxima (s) entre "Nunes Marques" e o termo associado
AGRUPAR_S = 120        # ocorrências a menos de 2 min uma da outra viram uma só
MAX_TENTATIVAS = 8     # vídeos sem legenda são retentados (lives ganham legenda depois)


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s)


# Expressões sobre texto normalizado (minúsculas, sem acento).
PRIMARIO = re.compile(r"\bnunes marques?\b|\bkassio\b|\bk?c?ass?c?io nunes\b")
# Termos que identificam o estudo: com eles a ocorrência é "confirmada".
TERMOS_ID = {
    "UERJ": r"\buer(?:j|ge|gi|g)\b|\bu e r j\b",
    "Celso": r"\bcelso\b",
}
# Termos associados: ocorrência "provável".
TERMOS_FORTES = {
    "estudo": r"\bestudos?\b",
    "levantamento": r"\blevantamentos?\b",
    "judicialização": r"\bjudicializa\w*",
    "judicializadas": r"\bjudicializad\w*",
    "Lauro Jardim": r"\blauro jardim\b",
}
TERMOS_FRACOS = {
    "TSE": r"\btse\b|\btribunal superior eleitoral\b",
    "lento": r"\blent(?:o|a|os|as|idao)\b",
}
# Termos que contam sozinhos, mesmo sem "Nunes Marques" por perto.
AUTONOMOS = {
    "Celso de Oliveira Santos": r"\bcelso de oliveira santos\b",
    "Monitor Eleitoral": r"\bmonitor eleitoral\b",
}
RE = {k: re.compile(v) for k, v in {**TERMOS_ID, **TERMOS_FORTES, **TERMOS_FRACOS, **AUTONOMOS}.items()}
NIVEL = {"confirmada": 3, "provável": 2, "fraca": 1}

CAMPOS = ["data_coleta", "canal", "data_video", "titulo", "video_id", "minuto",
          "link", "forca", "termos", "trecho"]


# ---------------------------------------------------------------- legendas
def segmentos_json3(dados: dict) -> list[tuple[float, str]]:
    segs = []
    for ev in dados.get("events", []):
        txt = "".join(s.get("utf8", "") for s in ev.get("segs", []) or [])
        txt = txt.replace("\n", " ").strip()
        if txt:
            segs.append((ev.get("tStartMs", 0) / 1000, txt))
    return segs


def escolher_legenda(info: dict):
    """Prefere legenda manual em português; senão a automática original."""
    for fonte, chaves in (("subtitles", ["pt-BR", "pt", "pt-PT"]),
                          ("automatic_captions", ["pt-orig", "pt", "pt-BR"])):
        faixas = info.get(fonte) or {}
        for k in chaves:
            for f in faixas.get(k, []):
                if f.get("ext") == "json3":
                    return f["url"], ("manual" if fonte == "subtitles" else "automática")
    return None, None


# ---------------------------------------------------------------- busca
def buscar(segs: list[tuple[float, str]]) -> list[dict]:
    """Procura no texto corrido (as legendas automáticas quebram nomes entre trechos)."""
    if not segs:
        return []
    partes, inicios, tempos, pos = [], [], [], 0
    for t, txt in segs:
        n = norm(txt) + " "
        partes.append(n); inicios.append(pos); tempos.append(t); pos += len(n)
    texto = "".join(partes)

    def tempo(i: int) -> float:
        lo, hi = 0, len(inicios) - 1
        while lo < hi:
            m = (lo + hi + 1) // 2
            if inicios[m] <= i: lo = m
            else: hi = m - 1
        return tempos[lo]

    def trecho(t0: float, t1: float) -> str:
        return " ".join(txt for t, txt in segs if t0 <= t <= t1)

    def termos_em(t0, t1, nomes):
        janela = norm(trecho(t0, t1))
        return [k for k in nomes if RE[k].search(janela)]

    brutos = []
    for m in PRIMARIO.finditer(texto):
        t = tempo(m.start())
        ids = termos_em(t - JANELA_S, t + JANELA_S, TERMOS_ID)
        fortes = termos_em(t - JANELA_S, t + JANELA_S, TERMOS_FORTES)
        fracos = termos_em(t - JANELA_S, t + JANELA_S, TERMOS_FRACOS)
        if ids or fortes or fracos:
            forca = "confirmada" if ids else "provável" if fortes else "fraca"
            brutos.append({"t": t, "forca": forca, "termos": ["Nunes Marques"] + ids + fortes + fracos})
    for k in AUTONOMOS:
        for m in RE[k].finditer(texto):
            brutos.append({"t": tempo(m.start()), "forca": "confirmada", "termos": [k]})

    brutos.sort(key=lambda h: h["t"])
    grupos: list[dict] = []
    for h in brutos:
        if grupos and h["t"] - grupos[-1]["fim"] <= AGRUPAR_S:
            g = grupos[-1]
            g["fim"] = h["t"]
            g["termos"] = list(dict.fromkeys(g["termos"] + h["termos"]))
            if NIVEL[h["forca"]] > NIVEL[g["forca"]]: g["forca"] = h["forca"]
        else:
            grupos.append({"t": h["t"], "fim": h["t"], "forca": h["forca"], "termos": h["termos"]})
    for g in grupos:
        g["trecho"] = trecho(g["t"] - 15, g["t"] + 40)[:400]
    return grupos


def minuto(t: float) -> str:
    t = int(t); h, r = divmod(t, 3600); m, s = divmod(r, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


# ---------------------------------------------------------------- YouTube
def ydl_opts(cookies: str | None) -> dict:
    o = {"quiet": True, "no_warnings": True, "skip_download": True,
         "extractor_args": {"youtube": {"lang": ["pt"]}}}
    if cookies:
        o["cookiefile"] = cookies
    return o


def listar_canal(ydl, canal: dict, por_aba: int) -> tuple[str, list[str]]:
    if canal.get("video_semente"):
        info = ydl.extract_info(f"https://www.youtube.com/watch?v={canal['video_semente']}", download=False)
        base = info.get("channel_url") or f"https://www.youtube.com/channel/{info['channel_id']}"
    else:
        base = f"https://www.youtube.com/{canal['handle']}"
    ids = []
    lista = yt_dlp.YoutubeDL({**ydl.params, "extract_flat": "in_playlist", "playlistend": por_aba})
    for aba in ("videos", "streams"):
        try:
            pl = lista.extract_info(f"{base}/{aba}", download=False)
            for e in (pl.get("entries") or [])[:por_aba]:
                if e and e.get("id"): ids.append(e["id"])
        except yt_dlp.utils.DownloadError:
            pass          # canal sem aba de lives, por exemplo
    return base, list(dict.fromkeys(ids))


def data_video(info: dict) -> dt.date | None:
    d = info.get("upload_date") or info.get("release_date")
    if d: return dt.datetime.strptime(d, "%Y%m%d").date()
    if info.get("timestamp"): return dt.datetime.utcfromtimestamp(info["timestamp"]).date()
    return None


def analisar_video(ydl, vid: str, canal_nome: str, dias: int | None):
    """Retorna (status, info_resumida, ocorrências)."""
    info = ydl.extract_info(f"https://www.youtube.com/watch?v={vid}", download=False)
    d = data_video(info)
    resumo = {"titulo": info.get("title", ""), "data": d.isoformat() if d else "",
              "canal": canal_nome or info.get("channel", "")}
    if dias is not None and d and d < dt.date.today() - dt.timedelta(days=dias):
        return "antigo", resumo, []
    if info.get("is_live") or info.get("live_status") in ("is_live", "is_upcoming"):
        return "sem_legenda", resumo, []
    url, tipo = escolher_legenda(info)
    if not url:
        return "sem_legenda", resumo, []
    dados = json.loads(ydl.urlopen(url).read().decode("utf-8"))
    resumo["legenda"] = tipo
    return "ok", resumo, buscar(segmentos_json3(dados))


# ---------------------------------------------------------------- registro
def carregar_estado() -> dict:
    return json.loads(ESTADO.read_text()) if ESTADO.exists() else {}


def gravar(ocorrencias: list[dict]):
    novo = not MENCOES.exists()
    with MENCOES.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        if novo: w.writeheader()
        w.writerows(ocorrencias)


def relatorio_md(ocorrencias: list[dict]) -> str:
    linhas = [f"# Menções em vídeo — {dt.date.today().isoformat()}", "",
              "Ocorrências encontradas nas legendas, a até 60 s de \"Nunes Marques\". "
              "**Confirmada**: com UERJ, Celso, \"Celso de Oliveira Santos\" ou \"Monitor Eleitoral\". "
              "**Provável**: com estudo, levantamento, judicialização ou Lauro Jardim. "
              "**Fraca**: só com TSE ou lento. Conferir sempre no vídeo antes de usar.", ""]
    for o in sorted(ocorrencias, key=lambda o: (-NIVEL[o["forca"]], o["canal"], o["data_video"])):
        linhas += [f"## [{o['forca'].upper()}] {o['canal']} — {o['titulo']}",
                   f"- Data do vídeo: {o['data_video']} · minuto **{o['minuto']}** · [abrir no ponto]({o['link']})",
                   f"- Termos: {o['termos']}",
                   f"- Trecho (legenda): “{o['trecho']}”", ""]
    return "\n".join(linhas)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--canais", default=str(RAIZ / "canais.yml"))
    ap.add_argument("--dias", type=int, default=3, help="idade máxima dos vídeos")
    ap.add_argument("--por-aba", type=int, default=20, help="vídeos recentes lidos por aba (vídeos e lives)")
    ap.add_argument("--video", help="analisa só este vídeo e imprime o resultado")
    ap.add_argument("--cookies", default=os.environ.get("YT_COOKIES_FILE"))
    a = ap.parse_args()

    hoje = dt.date.today().isoformat()
    with yt_dlp.YoutubeDL(ydl_opts(a.cookies)) as ydl:
        if a.video:
            status, r, occ = analisar_video(ydl, a.video, "", None)
            print(f"{status} · {r}")
            for o in occ:
                print(f"[{o['forca']}] {minuto(o['t'])} https://www.youtube.com/watch?v={a.video}&t={max(0,int(o['t'])-5)}s "
                      f"{o['termos']}\n    {o['trecho']}")
            return

        estado = carregar_estado()
        canais = yaml.safe_load(Path(a.canais).read_text())["canais"]
        novas, problemas = [], []
        for c in canais:
            try:
                base, ids = listar_canal(ydl, c, a.por_aba)
            except Exception as e:
                problemas.append(f"{c['nome']}: canal não encontrado ({type(e).__name__}: {str(e)[:160]})")
                continue
            print(f"{c['nome']}: {len(ids)} vídeos listados ({base})")
            for vid in ids:
                st = estado.get(vid, {})
                if st.get("status") in ("ok", "antigo") or st.get("tentativas", 0) >= MAX_TENTATIVAS:
                    continue
                try:
                    status, r, occ = analisar_video(ydl, vid, c["nome"], a.dias)
                except Exception as e:
                    status, r, occ = "erro", {}, []
                    erro = f"{type(e).__name__}: {str(e)[:200]}"
                    problemas.append(f"{c['nome']} {vid}: {erro}")
                estado[vid] = {"status": status, "canal": c["nome"], "visto": hoje,
                               "tentativas": st.get("tentativas", 0) + 1}
                if status == "erro": estado[vid]["erro"] = erro
                for o in occ:
                    novas.append({"data_coleta": hoje, "canal": r["canal"], "data_video": r["data"],
                                  "titulo": r["titulo"], "video_id": vid, "minuto": minuto(o["t"]),
                                  "link": f"https://www.youtube.com/watch?v={vid}&t={max(0, int(o['t']) - 5)}s",
                                  "forca": o["forca"], "termos": ", ".join(o["termos"]),
                                  "trecho": o["trecho"]})

    ESTADO.write_text(json.dumps(estado, ensure_ascii=False, indent=1, sort_keys=True))
    resumo = [f"Ocorrências novas: {len(novas)} ({sum(o['forca']=='confirmada' for o in novas)} confirmadas, "
              f"{sum(o['forca']=='provável' for o in novas)} prováveis)"]
    if novas:
        gravar(novas)
        RELATORIOS.mkdir(exist_ok=True)
        md = relatorio_md(novas)
        arq = RELATORIOS / f"{hoje}.md"
        arq.write_text((arq.read_text() + "\n\n" if arq.exists() else "") + md, encoding="utf-8")
        resumo.append(md)
    if problemas:
        resumo += ["", "### Problemas", *[f"- {p}" for p in problemas]]
    texto = "\n".join(resumo)
    print(texto)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(texto + "\n")
    # Se o YouTube bloqueou tudo, falha o job para aparecer em vermelho na aba Actions.
    if problemas and not any(v.get("visto") == hoje and v["status"] in ("ok", "antigo") for v in estado.values()):
        sys.exit("Nenhum vídeo pôde ser lido — provável bloqueio do YouTube (ver Problemas).")


if __name__ == "__main__":
    main()
