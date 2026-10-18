"""Utilitários compartilhados pelos scripts do framework Vibe Design.

Só usa a biblioteca padrão. As funções que abrem navegador importam o
Playwright sob demanda, para que a análise estática funcione sem ele.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

# ---------------------------------------------------------------------------
# Tipos de conteúdo e extensões
# ---------------------------------------------------------------------------

EXTENSAO_POR_TIPO = {
    "text/html": ".html",
    "text/css": ".css",
    "text/javascript": ".js",
    "application/javascript": ".js",
    "application/x-javascript": ".js",
    "application/ecmascript": ".js",
    "text/ecmascript": ".js",
    "application/json": ".json",
    "application/manifest+json": ".json",
    "application/ld+json": ".json",
    "text/plain": ".txt",
    "text/xml": ".xml",
    "application/xml": ".xml",
    "image/svg+xml": ".svg",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/avif": ".avif",
    "image/x-icon": ".ico",
    "image/vnd.microsoft.icon": ".ico",
    "font/woff2": ".woff2",
    "font/woff": ".woff",
    "font/ttf": ".ttf",
    "font/otf": ".otf",
    "application/font-woff": ".woff",
    "application/font-woff2": ".woff2",
    "application/x-font-ttf": ".ttf",
    "application/x-font-woff": ".woff",
    "application/vnd.ms-fontobject": ".eot",
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "audio/mpeg": ".mp3",
    "audio/ogg": ".ogg",
    "application/wasm": ".wasm",
    "model/gltf-binary": ".glb",
    "model/gltf+json": ".gltf",
    "application/octet-stream": ".bin",
}

TIPO_POR_EXTENSAO = {
    ".html": "text/html; charset=utf-8",
    ".htm": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".es": "text/javascript; charset=utf-8",  # capturas antigas
    ".json": "application/json; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
    ".xml": "application/xml",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".avif": "image/avif",
    ".ico": "image/x-icon",
    ".woff2": "font/woff2",
    ".woff": "font/woff",
    ".ttf": "font/ttf",
    ".otf": "font/otf",
    ".eot": "application/vnd.ms-fontobject",
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".mp3": "audio/mpeg",
    ".ogg": "audio/ogg",
    ".wasm": "application/wasm",
    ".glb": "model/gltf-binary",
    ".gltf": "model/gltf+json",
    ".bin": "application/octet-stream",
}

EXTENSOES_TEXTO = {".html", ".htm", ".css", ".js", ".mjs", ".json", ".svg", ".txt", ".xml"}


def tipo_base(content_type: str | None) -> str:
    return (content_type or "").split(";")[0].strip().lower()


def extensao_para(url: str, content_type: str | None) -> str:
    """Extensão coerente com o content-type; recorre à URL só se o tipo for desconhecido."""
    base = tipo_base(content_type)
    if base in EXTENSAO_POR_TIPO:
        return EXTENSAO_POR_TIPO[base]
    if base.startswith("font/"):
        return "." + base.split("/", 1)[1][:5]
    ext = os.path.splitext(urlsplit(url).path)[1].lower()
    if re.fullmatch(r"\.[a-z0-9]{1,5}", ext or "") and ext not in {".php", ".asp", ".aspx", ".jsp"}:
        return ext
    return ".bin"


# ---------------------------------------------------------------------------
# Arquivos
# ---------------------------------------------------------------------------


def sha256_bytes(dados: bytes) -> str:
    return hashlib.sha256(dados).hexdigest()


def sha256_arquivo(caminho: Path) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 16), b""):
            h.update(bloco)
    return h.hexdigest()


def ler_texto(caminho: Path) -> str:
    dados = Path(caminho).read_bytes()
    for codificacao in ("utf-8", "cp1252", "latin-1"):
        try:
            return dados.decode(codificacao)
        except UnicodeDecodeError:
            continue
    return dados.decode("utf-8", errors="replace")


def escrever_json(caminho: Path, dados) -> None:
    Path(caminho).parent.mkdir(parents=True, exist_ok=True)
    Path(caminho).write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ler_json(caminho: Path, padrao=None):
    try:
        return json.loads(Path(caminho).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return padrao


def hashes_da_pasta(pasta: Path, ignorar: tuple[str, ...] = (".vd",)) -> dict[str, str]:
    resultado = {}
    for raiz, dirs, arquivos in os.walk(pasta):
        dirs[:] = [d for d in dirs if d not in ignorar]
        for nome in arquivos:
            if nome == ".DS_Store":
                continue
            caminho = Path(raiz) / nome
            resultado[caminho.relative_to(pasta).as_posix()] = sha256_arquivo(caminho)
    return dict(sorted(resultado.items()))


# ---------------------------------------------------------------------------
# Árvore HTML mínima
# ---------------------------------------------------------------------------

ELEMENTOS_VAZIOS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
    "param", "source", "track", "wbr",
}
ELEMENTOS_TEXTO_BRUTO = {"script", "style"}
FECHAMENTO_IMPLICITO = {
    "p": {"p", "div", "section", "ul", "ol", "table", "header", "footer", "nav", "h1", "h2", "h3", "h4", "h5", "h6", "form", "article", "aside", "main", "figure", "blockquote", "pre"},
    "li": {"li"},
    "option": {"option"},
    "tr": {"tr"},
    "td": {"td", "th", "tr"},
    "th": {"td", "th", "tr"},
    "dt": {"dt", "dd"},
    "dd": {"dt", "dd"},
}


@dataclass
class No:
    tag: str
    attrs: list[tuple[str, str | None]] = field(default_factory=list)
    filhos: list["No | str"] = field(default_factory=list)
    pai: "No | None" = field(default=None, repr=False)
    linha: int = 0

    def attr(self, nome: str, padrao: str | None = None) -> str | None:
        for chave, valor in self.attrs:
            if chave == nome:
                return valor if valor is not None else ""
        return padrao

    def tem_attr(self, nome: str) -> bool:
        return any(chave == nome for chave, _ in self.attrs)

    @property
    def classes(self) -> list[str]:
        return (self.attr("class") or "").split()

    @property
    def elementos(self) -> list["No"]:
        return [f for f in self.filhos if isinstance(f, No)]

    def texto(self) -> str:
        partes = []
        for f in self.filhos:
            if isinstance(f, str):
                partes.append(f)
            elif f.tag not in ELEMENTOS_TEXTO_BRUTO:
                partes.append(f.texto())
        return "".join(partes)

    def texto_bruto(self) -> str:
        return "".join(f for f in self.filhos if isinstance(f, str))


class _Construtor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.raiz = No("#documento")
        self.pilha = [self.raiz]

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        topo = self.pilha[-1]
        fechar = FECHAMENTO_IMPLICITO.get(topo.tag)
        if fechar and tag in fechar:
            self.pilha.pop()
            topo = self.pilha[-1]
        no = No(tag, attrs, pai=topo, linha=self.getpos()[0])
        topo.filhos.append(no)
        if tag not in ELEMENTOS_VAZIOS:
            self.pilha.append(no)

    def handle_startendtag(self, tag, attrs):
        tag = tag.lower()
        topo = self.pilha[-1]
        topo.filhos.append(No(tag, attrs, pai=topo, linha=self.getpos()[0]))

    def handle_endtag(self, tag):
        tag = tag.lower()
        for i in range(len(self.pilha) - 1, 0, -1):
            if self.pilha[i].tag == tag:
                del self.pilha[i:]
                return

    def handle_data(self, data):
        if data:
            self.pilha[-1].filhos.append(data)


def parse_html(texto: str) -> No:
    construtor = _Construtor()
    construtor.feed(texto)
    construtor.close()
    return construtor.raiz


def iter_nos(no: No):
    for f in no.filhos:
        if isinstance(f, No):
            yield f
            yield from iter_nos(f)


def encontrar(no: No, tag: str) -> No | None:
    for n in iter_nos(no):
        if n.tag == tag:
            return n
    return None


def encontrar_todos(no: No, tag: str) -> list[No]:
    return [n for n in iter_nos(no) if n.tag == tag]


def caminho_do_no(no: No) -> str:
    """Seletor estrutural a partir do body (mesmo formato usado nos scripts de navegador)."""
    if no is None:
        return ""
    partes = []
    atual = no
    while atual is not None and atual.tag not in ("#documento", "html", "body"):
        pai = atual.pai
        if pai is None:
            break
        irmaos = [e for e in pai.elementos if e.tag == atual.tag]
        partes.append(f"{atual.tag}:nth-of-type({irmaos.index(atual) + 1})")
        atual = pai
    return "body > " + " > ".join(reversed(partes)) if partes else "body"


def no_por_caminho(raiz: No, caminho: str) -> No | None:
    """Inverso de caminho_do_no."""
    atual = encontrar(raiz, "body")
    if atual is None:
        return None
    for parte in [p.strip() for p in caminho.split(">")][1:]:
        m = re.fullmatch(r"([\w-]+):nth-of-type\((\d+)\)", parte)
        if not m:
            return None
        irmaos = [e for e in atual.elementos if e.tag == m.group(1)]
        indice = int(m.group(2)) - 1
        if indice >= len(irmaos):
            return None
        atual = irmaos[indice]
    return atual


# ---------------------------------------------------------------------------
# CSS: classes, cores, fontes, keyframes
# ---------------------------------------------------------------------------

_RE_COMENTARIO_CSS = re.compile(r"/\*.*?\*/", re.S)
_RE_SELETOR_CLASSE = re.compile(r"\.((?:[A-Za-z_\-]|\\.)(?:[\w\-]|\\.)*)")
_RE_ESCAPE_CSS = re.compile(r"\\([0-9a-fA-F]{1,6}\s?|.)")
_RE_COR = re.compile(
    r"#[0-9a-fA-F]{8}\b|#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{4}\b|#[0-9a-fA-F]{3}\b"
    r"|\b(?:rgba?|hsla?|oklch|oklab|lab|lch|hwb)\([^()]*\)"
)
_RE_FONTE = re.compile(r"font-family\s*:\s*([^;}{]+)", re.I)
_RE_KEYFRAMES = re.compile(r"@(?:-webkit-)?keyframes\s+([\w\-]+)")
_RE_TRANSICAO = re.compile(r"(?<![\w-])(transition(?:-[a-z-]+)?|animation(?:-[a-z-]+)?)\s*:\s*([^;}{]+)", re.I)


def remover_comentarios_css(css: str) -> str:
    return _RE_COMENTARIO_CSS.sub("", css)


def desescapar_css(ident: str) -> str:
    def troca(m):
        s = m.group(1)
        if re.fullmatch(r"[0-9a-fA-F]{1,6}\s?", s):
            return chr(int(s.strip(), 16))
        return s

    return _RE_ESCAPE_CSS.sub(troca, ident)


def seletores_css(css: str) -> list[str]:
    """Textos de seletor (antes de cada bloco de declarações), ignorando @regras de bloco."""
    css = remover_comentarios_css(css)
    seletores = []
    for m in re.finditer(r"([^{}]+)\{", css):
        sel = m.group(1).strip()
        if not sel or sel.startswith("@"):
            continue
        if re.fullmatch(r"(?:from|to|\d+(?:\.\d+)?%)(?:\s*,\s*(?:from|to|\d+(?:\.\d+)?%))*", sel):
            continue
        seletores.append(sel)
    return seletores


def classes_de_css(css: str) -> set[str]:
    classes = set()
    for sel in seletores_css(css):
        sem_strings = re.sub(r"\[[^\]]*\]", lambda m: m.group(0) if "\\" in m.group(0) else "", sel)
        for m in _RE_SELETOR_CLASSE.finditer(sem_strings):
            bruto = m.group(1)
            if re.fullmatch(r"\d.*", bruto):
                continue
            classes.add(desescapar_css(bruto))
    return classes


def normalizar_cor(cor: str) -> str:
    cor = cor.strip().lower()
    if cor.startswith("#"):
        if len(cor) in (4, 5):  # #rgb / #rgba
            cor = "#" + "".join(c * 2 for c in cor[1:])
        if len(cor) == 9 and cor.endswith("ff"):
            cor = cor[:7]
        return cor
    cor = re.sub(r"\s+", "", cor)
    cor = cor.replace("rgba(", "rgb(").replace("hsla(", "hsl(")
    return cor


def cores_em(texto: str) -> set[str]:
    return {normalizar_cor(m.group(0)) for m in _RE_COR.finditer(texto or "")}


GENERICAS_FONTE = {
    "serif", "sans-serif", "monospace", "cursive", "fantasy", "system-ui", "ui-serif",
    "ui-sans-serif", "ui-monospace", "ui-rounded", "emoji", "math", "fangsong",
    "inherit", "initial", "unset", "revert", "-apple-system", "blinkmacsystemfont",
}


def familias_de_declaracao(valor: str) -> set[str]:
    familias = set()
    valor = re.sub(r"!important", "", valor, flags=re.I)
    for parte in valor.split(","):
        nome = parte.strip().strip("'\"").strip()
        if not nome or nome.startswith("var(") or nome.startswith("--"):
            continue
        familias.add(nome.lower())
    return familias


def fontes_em_css(css: str) -> set[str]:
    familias = set()
    for m in _RE_FONTE.finditer(remover_comentarios_css(css)):
        familias |= familias_de_declaracao(m.group(1))
    return familias


def keyframes_em_css(css: str) -> set[str]:
    return set(_RE_KEYFRAMES.findall(remover_comentarios_css(css)))


def transicoes_em_css(css: str) -> set[str]:
    return {f"{m.group(1).lower()}: {m.group(2).strip()}" for m in _RE_TRANSICAO.finditer(remover_comentarios_css(css))}


# Classes arbitrárias do Tailwind: font-['Inter'], bg-[#0a0a0a] etc.
_RE_FONTE_ARBITRARIA = re.compile(r"font-\[(['\"]?)([^\]'\"]+)\1\]")


def fontes_em_classes(classes) -> set[str]:
    familias = set()
    for c in classes:
        for m in _RE_FONTE_ARBITRARIA.finditer(c):
            familias |= familias_de_declaracao(m.group(2).replace("_", " "))
    return familias


# Literais de classe adicionados por JS: classList.add('a', "b"), className = 'x y'
_RE_CLASSLIST = re.compile(r"classList\.(?:add|toggle|remove|replace)\(([^)]*)\)")
_RE_CLASSNAME = re.compile(r"className\s*[+]?=\s*([`'\"])(.*?)\1")
_RE_STRING = re.compile(r"([`'\"])((?:\\.|(?!\1).)*)\1")


def classes_de_js(js: str) -> set[str]:
    classes = set()
    for m in _RE_CLASSLIST.finditer(js):
        for s in _RE_STRING.finditer(m.group(1)):
            classes |= set(s.group(2).split())
    for m in _RE_CLASSNAME.finditer(js):
        classes |= set(m.group(2).split())
    return {c for c in classes if re.fullmatch(r"[\w\-:/\[\]().#%!,'&]+", c) and "${" not in c}


# ---------------------------------------------------------------------------
# HTML: coleta de estilos, referências e texto
# ---------------------------------------------------------------------------

ATRIBUTOS_URL = {"src", "href", "poster", "data", "action", "data-src", "data-original", "data-lazy-src", "data-bg", "data-background", "data-image", "data-url"}
ATRIBUTOS_SRCSET = {"srcset", "data-srcset", "imagesrcset"}
ATRIBUTOS_COR_SVG = {"fill", "stroke", "stop-color", "flood-color", "lighting-color", "color"}


def css_inline_do_html(raiz: No) -> list[str]:
    blocos = []
    for n in iter_nos(raiz):
        if n.tag == "style":
            blocos.append(n.texto_bruto())
    return blocos


def estilos_de_atributo(raiz: No) -> list[str]:
    return [n.attr("style") for n in iter_nos(raiz) if n.attr("style")]


def scripts_inline(raiz: No) -> list[No]:
    return [n for n in iter_nos(raiz) if n.tag == "script" and not n.attr("src") and n.texto_bruto().strip()]


def eh_url_local(valor: str) -> bool:
    valor = (valor or "").strip()
    if not valor or valor.startswith(("#", "data:", "blob:", "mailto:", "tel:", "javascript:", "about:")):
        return False
    return not re.match(r"^(?:[a-z][a-z0-9+.\-]*:)?//", valor, re.I)


def urls_de_srcset(valor: str) -> list[str]:
    urls = []
    for parte in (valor or "").split(","):
        tokens = parte.strip().split()
        if tokens:
            urls.append(tokens[0])
    return urls


def urls_de_css(css: str) -> list[str]:
    css = remover_comentarios_css(css)
    urls = []
    for m in re.finditer(r"url\(\s*(['\"]?)(.*?)\1\s*\)", css):
        urls.append(m.group(2).strip())
    for m in re.finditer(r"@import\s+(['\"])(.*?)\1", css):
        urls.append(m.group(2).strip())
    return urls


def referencias_do_html(raiz: No) -> list[tuple[No, str, str]]:
    """(nó, atributo, url) para referências de recursos (exclui <a href> de navegação)."""
    refs = []
    for n in iter_nos(raiz):
        for chave, valor in n.attrs:
            if valor is None:
                continue
            if chave in ATRIBUTOS_URL:
                if n.tag == "a" and chave == "href":
                    continue
                if n.tag in ("form",) and chave == "action":
                    continue
                if n.tag == "link" and chave == "href":
                    rel = (n.attr("rel") or "").lower()
                    if any(r in rel for r in ("canonical", "alternate", "next", "prev", "dns-prefetch", "preconnect")):
                        continue
                refs.append((n, chave, valor))
            elif chave in ATRIBUTOS_SRCSET:
                for u in urls_de_srcset(valor):
                    refs.append((n, chave, u))
            elif chave == "style":
                for u in urls_de_css(valor):
                    refs.append((n, chave, u))
        if n.tag == "style":
            for u in urls_de_css(n.texto_bruto()):
                refs.append((n, "#css", u))
    return refs


def resolver_local(base_dir: Path, url: str) -> Path | None:
    url = unquote(url.split("#", 1)[0].split("?", 1)[0])
    if not url:
        return None
    if url.startswith("/"):
        return None  # caminhos absolutos de servidor não resolvem numa pasta
    return (base_dir / url).resolve()


def textos_visiveis(raiz: No, minimo_palavras: int = 1) -> list[str]:
    """Nós de texto visíveis (ignora script, style, svg, code, pre, template, noscript e translate=no)."""
    ignorar = {"script", "style", "svg", "code", "pre", "template", "noscript", "head", "title"}
    textos = []

    def visitar(no: No, bloqueado: bool):
        bloqueado = bloqueado or no.tag in ignorar or no.attr("translate") == "no" or no.tem_attr("hidden")
        for f in no.filhos:
            if isinstance(f, str):
                if not bloqueado:
                    t = " ".join(f.split())
                    if t and len(t.split()) >= minimo_palavras and re.search(r"[A-Za-zÀ-ÿ]", t):
                        textos.append(t)
            else:
                visitar(f, bloqueado)

    visitar(raiz, False)
    return textos


def idioma_do_documento(raiz: No) -> str:
    html = encontrar(raiz, "html")
    return ((html.attr("lang") if html else "") or "").lower()


# ---------------------------------------------------------------------------
# Bibliotecas conhecidas
# ---------------------------------------------------------------------------

BIBLIOTECAS = [
    # (nome exibido, padrões em src/href/nome de arquivo, padrões no HTML)
    ("Tailwind CSS", [r"tailwind", r"resource_3fa48481346f"], [r"tailwind\.config", r"type=[\"']text/tailwindcss"]),
    ("Lucide", [r"lucide"], [r"data-lucide=", r"class=[\"'][^\"']*\blucide\b"]),
    ("Iconify", [r"iconify"], [r"<iconify-icon\b"]),
    ("GSAP", [r"gsap", r"ScrollTrigger"], [r"\bgsap\."]),
    ("Three.js", [r"three(?:\.module)?(?:\.min)?\.js", r"/three@", r"three_"], [r"\bTHREE\."]),
    ("Lenis", [r"lenis"], [r"new Lenis\("]),
    ("Unicorn Studio", [r"unicorn"], [r"data-us-project"]),
    ("Framer Motion", [r"framer-motion", r"motion\.dev", r"/motion@"], []),
    ("Alpine.js", [r"alpine"], [r"\bx-data="]),
    ("Swiper", [r"swiper"], [r"class=[\"'][^\"']*\bswiper\b"]),
    ("jQuery", [r"jquery"], []),
    ("Spline", [r"spline"], [r"<spline-viewer\b", r"my\.spline\.design"]),
    ("Google Fonts", [r"fonts\.googleapis", r"fonts\.gstatic", r"css2_[0-9a-f]{12}\.css"], []),
]


def detectar_bibliotecas(html_texto: str, refs: list[str]) -> list[dict]:
    encontradas = []
    for nome, padroes_ref, padroes_html in BIBLIOTECAS:
        evidencias = []
        for r in refs:
            if any(re.search(p, r, re.I) for p in padroes_ref):
                evidencias.append(r)
        for p in padroes_html:
            if re.search(p, html_texto, re.I):
                evidencias.append(f"html:{p}")
        if evidencias:
            encontradas.append({"nome": nome, "evidencias": sorted(set(evidencias))[:5]})
    return encontradas


# ---------------------------------------------------------------------------
# Rastreadores
# ---------------------------------------------------------------------------

HOSTS_RASTREADORES = [
    "googletagmanager.com", "google-analytics.com", "analytics.google.com", "doubleclick.net",
    "connect.facebook.net", "clarity.ms", "hotjar.com", "static.hotjar.com", "segment.com",
    "cdn.segment.com", "mixpanel.com", "amplitude.com", "plausible.io", "umami.is",
    "snap.licdn.com", "bat.bing.com", "analytics.tiktok.com", "posthog.com",
]
_RE_RASTREADOR_INLINE = re.compile(r"\b(gtag\(|fbq\(|dataLayer\.push|clarity\(|hj\(|_hsq|mixpanel\.|analytics\.track)")


def eh_rastreador(src: str | None, codigo: str | None) -> bool:
    if src:
        host = urlsplit(urljoin("https://x/", src)).hostname or ""
        if any(host == h or host.endswith("." + h) for h in HOSTS_RASTREADORES):
            return True
    if codigo and _RE_RASTREADOR_INLINE.search(codigo):
        return True
    return False


# ---------------------------------------------------------------------------
# Navegador
# ---------------------------------------------------------------------------


def abrir_navegador(playwright, offline: bool = False):
    """Chromium headless. Em modo offline, todo host diferente de localhost/127.0.0.1 deixa de resolver."""
    args = []
    if offline:
        args.append("--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE localhost, EXCLUDE 127.0.0.1")
    return playwright.chromium.launch(headless=True, args=args)


def rolar_pagina(page, passo: float = 0.8, espera_ms: int = 350, max_passos: int = 80) -> None:
    """Rola até o fim em passos (dispara lazy-load e animações de scroll) e volta ao topo."""
    altura_vista = page.evaluate("window.innerHeight") or 900
    posicao = 0
    for _ in range(max_passos):
        altura_total = page.evaluate("Math.max(document.body ? document.body.scrollHeight : 0, document.documentElement.scrollHeight)")
        if posicao >= altura_total:
            break
        posicao += int(altura_vista * passo)
        page.evaluate("y => window.scrollTo(0, y)", posicao)
        page.wait_for_timeout(espera_ms)
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(600)


def esperar_rede(page, timeout_ms: int = 12000) -> None:
    try:
        page.wait_for_load_state("networkidle", timeout=timeout_ms)
    except Exception:
        pass
