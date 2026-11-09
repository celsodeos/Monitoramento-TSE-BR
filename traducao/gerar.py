"""Gera as versões EN e ES das páginas públicas a partir das páginas em português.

Uso: python traducao/gerar.py           (escreve docs/en, docs/es, docs/segundo-turno/en, docs/segundo-turno/es)
     python traducao/gerar.py --checar  (só lista trechos sem tradução)
Também insere o seletor de idioma (PT · EN · ES) nas páginas em português.
Depois de mudar o texto em português, rode de novo e traduza em traducao/textos.py o que for listado.
"""
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from segmentos import segmentos_html, segmentos_js
from textos import T

RAIZ = Path(__file__).resolve().parent.parent / "docs"
LANG = {"pt": "pt-BR", "en": "en", "es": "es"}
ROTULO = {"pt": "Português", "en": "English", "es": "Español"}

# Trechos que ficam iguais em todas as línguas (nomes próprios, títulos de matérias, modelos sem texto).
def neutro(s):
    if re.fullmatch(r"[\s\S]*\$\{[\s\S]*", s) and not re.search(r"\b(de|ações|sem|do|da|em|até|carga)\b", re.sub(r"\$\{[^}]*\}", "", s)):
        return True
    return False

PAGINAS = {   # página PT -> (pasta das traduções, ajustes de caminho)
    "index.html": ("", [("'dados/", "'../dados/")]),
    "segundo-turno/index.html": ("segundo-turno/", [('src="../assets/', 'src="../../assets/'), ("'v2/dados/", "'../v2/dados/")]),
}

CODIGO = {   # formatação de números e datas
    "en": [(".replace(/,/g, '.')", ""), ("pct(v).replace('.', ',')", "pct(v)"),
           ("'< 0,001' : String(+v).replace('.', ',')", "'< 0.001' : String(+v)"),
           ("'p < 0,001' : 'p = ' + String(+v).replace('.', ',')", "'p < 0.001' : 'p = ' + String(+v)"),
           (".toFixed(1).replace('.', ',')", ".toFixed(1)"), ("toLocaleDateString('pt-BR')", "toLocaleDateString('en-GB')")],
    "es": [("toLocaleDateString('pt-BR')", "toLocaleDateString('es-ES')")],
}

def seletor(atual, base_pt):
    """base_pt: caminho relativo da página atual até a pasta da versão PT."""
    href = {"pt": base_pt or "./", "en": base_pt + "en/", "es": base_pt + "es/"}
    itens = []
    for l in ("pt", "en", "es"):
        if l == atual:
            itens.append(f'<span aria-current="page">{l.upper()}</span>')
        else:
            itens.append(f'<a href="{href[l]}" hreflang="{LANG[l]}" lang="{LANG[l]}" title="{ROTULO[l]}">{l.upper()}</a>')
    return '<nav class="idiomas" aria-label="Idioma / Language / Idioma">' + "".join(itens) + "</nav>"

CSS = """.idiomas { position: absolute; top: max(12px, env(safe-area-inset-top, 0px)); right: max(16px, env(safe-area-inset-right, 0px)); display: flex; gap: 2px; font-size: var(--cds-font-size-caption, 12px); letter-spacing: .06em; z-index: 5; }
.idiomas a, .idiomas span { padding: 3px 7px; border-radius: 4px; text-decoration: none; color: var(--color-fg-muted); border: 1px solid transparent; }
.idiomas a:hover, .idiomas a:focus-visible { color: var(--color-fg); border-color: var(--color-border-line); outline: none; }
.idiomas span { color: var(--color-fg); font-weight: 600; border-color: var(--color-border-line); }
"""

def com_seletor(s, atual, base_pt, alternativos):
    s = re.sub(r'\n?<nav class="idiomas".*?</nav>', "", s, flags=re.S)
    s = re.sub(r'<link rel="alternate" hreflang="[^"]*" href="[^"]*">\n?', "", s)
    s = re.sub(r"/\* idiomas \*/.*?/\* fim idiomas \*/\n?", "", s, flags=re.S)
    s = s.replace("</style>", "/* idiomas */\n" + CSS + "/* fim idiomas */\n</style>", 1)
    s = re.sub(r"(<body[^>]*>)", lambda m: m.group(1) + "\n" + seletor(atual, base_pt), s, count=1)
    links = "".join(f'<link rel="alternate" hreflang="{LANG[l]}" href="{h}">\n' for l, h in alternativos.items())
    s = s.replace("</head>", links + "</head>", 1)
    if "body { position" not in s and "body{position" not in s:
        s = s.replace("/* fim idiomas */", "body { position: relative; }\n/* fim idiomas */", 1)
    return s

def traduzir(s, lang, faltam):
    trechos = sorted(set(segmentos_html(s) + segmentos_js(s)), reverse=True)
    for a, b in trechos:
        pt = s[a:b]
        if pt in T:
            s = s[:a] + T[pt][lang] + s[b:]
            continue
        # trecho com marcação interna (ex.: item da lista de imprensa): traduz os pedaços conhecidos
        novo = re.sub(r">([^<>]+)<", lambda m: ">" + (T[m.group(1)][lang] if m.group(1) in T else m.group(1)) + "<", pt)
        if novo != pt:
            s = s[:a] + novo + s[b:]
        elif not neutro(pt):
            faltam.add(pt)
    return s

def main():
    checar = "--checar" in sys.argv
    faltam = set()
    base_site = "https://celsodeos.github.io/Monitoramento-TSE-BR/"
    for rel, (pasta, caminhos) in PAGINAS.items():
        orig = (RAIZ / rel).read_text(encoding="utf-8")
        orig = re.sub(r'\n?<nav class="idiomas".*?</nav>', "", orig, flags=re.S)
        alt = {"pt": base_site + pasta, "en": base_site + pasta + "en/", "es": base_site + pasta + "es/"}
        for lang in ("en", "es"):
            s = traduzir(orig, lang, faltam)
            for a, b in caminhos:
                assert a in s, f"{rel}: não achei {a!r}"
                s = s.replace(a, b)
            for k in (" (presidente)", "Outros gabinetes", "Contra Lula", "Contra Flávio"):   # rótulos curtos no script
                s = s.replace(f"'{k}'", f"'{T[k][lang]}'")
            for a, b in CODIGO[lang]:
                s = s.replace(a, b)
            if lang == "en":   # números em células de tabela: 0,7% -> 0.7%
                s = re.sub(r"(<td[^>]*>)([^<]*)", lambda m: m.group(1) + re.sub(r"(\d),(\d)", r"\1.\2", m.group(2)), s)
            s = s.replace('<html lang="pt-BR">', f'<html lang="{LANG[lang]}">', 1)
            s = com_seletor(s, lang, "../", alt)
            if not checar:
                destino = RAIZ / pasta / lang / "index.html"
                destino.parent.mkdir(parents=True, exist_ok=True)
                destino.write_text(s, encoding="utf-8")
        if not checar:
            (RAIZ / rel).write_text(com_seletor((RAIZ / rel).read_text(encoding="utf-8"), "pt", "", alt), encoding="utf-8")
    if faltam:
        print(f"{len(faltam)} trechos sem tradução (ficaram em português):")
        for f in sorted(faltam):
            if not re.match(r"(id|ano),|display:|width:", f): print("  ", repr(f[:150]))
    else:
        print("Todos os trechos traduzidos.")

if __name__ == "__main__":
    main()
