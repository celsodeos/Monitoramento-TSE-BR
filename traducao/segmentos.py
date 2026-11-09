"""Localiza os trechos traduzíveis de uma página (HTML fora de <script>/<style> e literais de texto nos scripts do painel)."""
import re
from html.parser import HTMLParser

BLOCOS = {"span","p","li","h1","h2","h3","h4","figcaption","caption","th","td","button","label","summary","dt","dd","title","option","legend"}
CONTEINERES = (BLOCOS - {"span"}) | {"div","section","ul","ol","table","figure","details","header","footer","nav","main","article","aside","form","fieldset","dl","tr","thead","tbody"}
VAZIOS = {"br","img","meta","link","input","hr","source","wbr","col","area","base","embed","param","track"}

class _P(HTMLParser):
    def __init__(self, s):
        super().__init__(convert_charrefs=False); self.s = s; self.pilha = []; self.seg = []; self.attrs = []
        lines = s.split("\n"); self.off = [0]
        for l in lines: self.off.append(self.off[-1] + len(l) + 1)
    def pos(self): l, c = self.getpos(); return self.off[l-1] + c
    def handle_starttag(self, tag, attrs):
        p = self.pos(); fim = self.s.index(">", p) + 1
        for k, v in attrs:
            if k in ("alt","aria-label","title","placeholder") and v and re.search(r"[A-Za-zÀ-ú]{2}", v):
                i = self.s.index(f'{k}="', p, fim) + len(k) + 2; self.attrs.append((i, i + len(v)))
            if k == "content" and dict(attrs).get("name") in ("description","og:description","twitter:description") or (k=="content" and dict(attrs).get("property") in ("og:title","og:description")):
                i = self.s.index('content="', p, fim) + 9; self.attrs.append((i, i + len(v)))
        if tag in VAZIOS: return
        for e in self.pilha: 
            if tag in CONTEINERES: e[2] = True
        self.pilha.append([tag, fim, False])
    def handle_endtag(self, tag):
        p = self.pos()
        while self.pilha:
            t, ini, tem_bloco = self.pilha.pop()
            if t == tag:
                if t in BLOCOS and not tem_bloco: self.seg.append((ini, p))
                break

def segmentos_html(s):
    """Retorna intervalos (ini, fim) de conteúdo traduzível, fora de script/style."""
    # mascara scripts e estilos preservando offsets
    m = re.sub(r"(<(script|style)[^>]*>)(.*?)(</\2>)", lambda x: x.group(1) + " " * len(x.group(3)) + x.group(4), s, flags=re.S)
    p = _P(m); p.feed(m)
    seg = sorted(set((a, b) for a, b in p.seg if re.search(r"[A-Za-zÀ-ú]{2}", m[a:b])), key=lambda x: (x[0], -x[1]))
    fora = []
    for a, b in seg:   # descarta trechos contidos em outro trecho (ex.: <span> dentro de <p>)
        if not any(a2 <= a and b <= b2 and (a2, b2) != (a, b) for a2, b2 in seg): fora.append((a, b))
    at = [(a, b) for a, b in p.attrs if not any(a2 <= a and b <= b2 for a2, b2 in fora)]
    return sorted(set(fora + at))

LIT = re.compile(r"""'((?:[^'\\\n]|\\.)*)'|"((?:[^"\\\n]|\\.)*)"|`((?:[^`\\]|\\.)*)`""")
def segmentos_js(s):
    """Literais de texto em português nos scripts do painel (não no d3)."""
    out = []
    for m in re.finditer(r"<script(?![^>]*src)[^>]*>(.*?)</script>", s, re.S):
        corpo = m.group(1)
        if "d3js.org" in corpo[:200] or len(corpo) > 100000: continue
        base = m.start(1)
        for l in LIT.finditer(corpo):
            g = next(i for i in (1,2,3) if l.group(i) is not None); v = l.group(g)
            if l.start(g) > 0 and len(v) > 200 and v.count("\n") > 3: continue   # dados embutidos (CSV)
            if not re.search(r"[A-Za-zÀ-ú]{3}", v): continue
            if re.fullmatch(r"[\w.#\-\[\]=\"' :>*(),%/]+", v) and not re.search(r"[À-ú]|\s\w+\s", v):
                # seletor, id, classe, chave: só entra se tiver palavra portuguesa clara
                if not re.search(r"[À-ú]|\b(de|da|do|em|ações|dias|turno|gabinete|total|sem|com|até)\b", v, re.I): continue
            out.append((base + l.start(g), base + l.end(g)))
    return out
