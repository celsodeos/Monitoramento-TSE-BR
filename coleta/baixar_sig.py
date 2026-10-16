#!/usr/bin/env python3
"""
Baixa os pacotes do grupo "Processual" do Portal de Dados Abertos do TSE
(https://dadosabertos.tse.jus.br/group/processual) e extrai os CSV em
dados/brutos/<ano>/<tipo>/.

Uso:
    python coleta/baixar_sig.py --anos 2018 2022 2026
    python coleta/baixar_sig.py --anos 2026 --tipos processo decisoes

Só usa a biblioteca padrão do Python.
"""
import argparse, io, os, sys, time, urllib.request, zipfile

BASE = "https://cdn.tse.jus.br/estatistica/sead/odsele/processual/"
ARQUIVOS = {
    "processo": "processo_eleitoral_{ano}.zip",
    "decisoes": "processos_eleitorais_decisoes_{ano}.zip",
    "partes":   "processos_eleitorais_partes_{ano}.zip",
    "recursos": "recursos_eleitorais_{ano}.zip",
}
RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "dados", "brutos")


def baixar(url, tentativas=4):
    espera = 5
    for t in range(tentativas):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Monitoramento-TSE-BR (pesquisa academica)"})
            with urllib.request.urlopen(req, timeout=300) as r:
                return r.read()
        except Exception as e:
            if t == tentativas - 1:
                raise
            print(f"  falha ({type(e).__name__}); nova tentativa em {espera}s", flush=True)
            time.sleep(espera); espera *= 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--anos", nargs="+", default=["2018", "2022", "2026"])
    ap.add_argument("--tipos", nargs="+", default=["processo", "decisoes", "partes"], choices=list(ARQUIVOS))
    a = ap.parse_args()
    erros = 0
    for ano in a.anos:
        for tipo in a.tipos:
            url = BASE + ARQUIVOS[tipo].format(ano=ano)
            destino = os.path.normpath(os.path.join(RAIZ, ano, tipo))
            os.makedirs(destino, exist_ok=True)
            print(f"{ano} {tipo}: {url}", flush=True)
            try:
                dados = baixar(url)
            except Exception as e:
                print(f"  ERRO: {e}", flush=True); erros += 1; continue
            with zipfile.ZipFile(io.BytesIO(dados)) as z:
                for nome in z.namelist():
                    if nome.lower().endswith(".csv"):
                        alvo = os.path.join(destino, os.path.basename(nome))
                        with z.open(nome) as src, open(alvo, "wb") as dst:
                            dst.write(src.read())
                        with open(alvo, "rb") as fh:
                            cab = fh.readline().decode("latin1").strip()
                        tam = os.path.getsize(alvo) / 1e6
                        print(f"  -> {os.path.relpath(alvo)} ({tam:.1f} MB)", flush=True)
                        # aparece nas anotações da execução no GitHub Actions
                        print(f"::notice title={ano} {tipo}: {os.path.basename(nome)} ({tam:.1f} MB)::{cab[:900]}", flush=True)
    sys.exit(1 if erros else 0)


if __name__ == "__main__":
    main()
