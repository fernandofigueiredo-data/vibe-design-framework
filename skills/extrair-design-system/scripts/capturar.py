#!/usr/bin/env python3
"""Captura fiel de uma página (modo fidelidade).

Princípios:
- Serve-se o HTML de ORIGEM (o que o servidor entregou), não o DOM já animado:
  o JavaScript roda de novo, offline, e reproduz as animações como no original.
- Nada visual é alterado. Nenhum CSS ou script é injetado. Toda alteração
  necessária (rastreador neutralizado, <base> ajustado, integrity removido de
  arquivo reescrito) fica marcada com um atributo data-vd-*.
- Todos os recursos vão para assets/: fontes, CDNs, imagens, vídeos, dados.
- Sem evasão de detecção: se aparecer login, CAPTCHA ou desafio anti-bot, a
  captura é abortada.

Uso:
    python capturar.py <url> <pasta-destino> [--largura 1440] [--altura 900]
                       [--limite-mb 25] [--timeout 60]

Saída (na pasta-destino): index.html, origem.html, renderizado.html,
assets/, captura.json.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html as html_lib
import re
import sys
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vd_comum import (  # noqa: E402
    ATRIBUTOS_SRCSET,
    ATRIBUTOS_URL,
    abrir_navegador,
    eh_rastreador,
    escrever_json,
    esperar_rede,
    extensao_para,
    rolar_pagina,
    sha256_bytes,
    tipo_base,
    urls_de_srcset,
)

VERSAO = "1.0"
MAX_COMPLEMENTOS = 500


class CapturaAbortada(Exception):
    """Login, CAPTCHA ou desafio anti-bot: a captura não contorna proteções."""


# ---------------------------------------------------------------------------
# URLs
# ---------------------------------------------------------------------------


def sem_fragmento(url: str) -> str:
    partes = urlsplit(url)
    return urlunsplit((partes.scheme, partes.netloc, partes.path, partes.query, ""))


def absoluta(url: str, base: str) -> str | None:
    url = html_lib.unescape((url or "").strip())
    if not url or url.startswith(("data:", "blob:", "#", "javascript:", "mailto:", "tel:", "about:")):
        return None
    try:
        resultado = urljoin(base, url)
    except ValueError:
        return None
    if not resultado.startswith(("http://", "https://")):
        return None
    return sem_fragmento(resultado)


def nome_de_arquivo(url: str, content_type: str | None) -> str:
    caminho = urlsplit(url).path
    base = caminho.rstrip("/").rsplit("/", 1)[-1] or "recurso"
    base = base.rsplit(".", 1)[0] if "." in base else base
    base = re.sub(r"[^A-Za-z0-9_-]", "_", base)[:40] or "recurso"
    digest = hashlib.sha1(url.encode()).hexdigest()[:12]
    return f"{base}_{digest}{extensao_para(url, content_type)}"


# ---------------------------------------------------------------------------
# Reescrita de CSS e JS
# ---------------------------------------------------------------------------

_RE_URL_CSS = re.compile(r"url\(\s*(['\"]?)(.*?)\1\s*\)", re.S)
_RE_IMPORT_CSS = re.compile(r"(@import\s+)(['\"])(.*?)\2")


def reescrever_css(css: str, base_css: str, localizar, prefixo: str) -> tuple[str, int]:
    """Troca url(...) e @import "..." por caminhos locais. prefixo='' para CSS em assets/."""
    trocas = 0

    def por_url(m):
        nonlocal trocas
        aspas, valor = m.group(1), m.group(2).strip()
        alvo = absoluta(valor, base_css)
        local = localizar(alvo) if alvo else None
        if not local:
            return m.group(0)
        trocas += 1
        return f"url({aspas}{prefixo}{local}{aspas})"

    def por_import(m):
        nonlocal trocas
        alvo = absoluta(m.group(3), base_css)
        local = localizar(alvo) if alvo else None
        if not local:
            return m.group(0)
        trocas += 1
        return f"{m.group(1)}{m.group(2)}{prefixo}{local}{m.group(2)}"

    css = _RE_URL_CSS.sub(por_url, css)
    css = _RE_IMPORT_CSS.sub(por_import, css)
    return css, trocas


def reescrever_literais(texto: str, mapa_abs: dict[str, str], prefixo: str) -> tuple[str, int]:
    """Troca literais de URL absoluta (inclusive protocolo relativo e barras escapadas) por caminhos locais."""
    trocas = 0
    for url in sorted(mapa_abs, key=len, reverse=True):
        local = prefixo + mapa_abs[url]
        partes = urlsplit(url)
        resto = url.split(partes.netloc, 1)[1]
        variantes = [(url, local), ("//" + partes.netloc + resto, local)]
        variantes += [(v.replace("/", "\\/"), l.replace("/", "\\/")) for v, l in variantes]
        for v, l in variantes:
            if v not in texto:
                continue
            # o próximo caractere não pode continuar a URL (evita trocar prefixo de URL maior)
            padrao = re.compile(re.escape(v) + r"(?![\w\-./%~+])")
            texto, n = padrao.subn(lambda _m, l=l: l, texto)
            trocas += n
    return texto, trocas


# ---------------------------------------------------------------------------
# Reescrita do HTML preservando o texto original
# ---------------------------------------------------------------------------

_RE_ATRIBUTO = re.compile(r"""([^\s=/>"']+)(?:(\s*=\s*)("[^"]*"|'[^']*'|[^\s>]+))?""")
_RE_TAG = re.compile(r"""<([A-Za-z][\w:-]*)((?:"[^"]*"|'[^']*'|[^'">])*)>""")


class ReescritorHTML:
    def __init__(self, base: str, localizar, mapa_abs: dict[str, str], relatorio: dict):
        self.base = base
        self.localizar = localizar
        self.mapa_abs = mapa_abs
        self.relatorio = relatorio

    # -- atributos -----------------------------------------------------------
    def _valor_url(self, valor: str) -> str | None:
        alvo = absoluta(valor, self.base)
        local = self.localizar(alvo) if alvo else None
        return f"assets/{local}" if local else None

    def _reescrever_tag(self, nome: str, corpo: str, rastreador: bool = False) -> str:
        nome_l = nome.lower()
        attrs = []
        for m in _RE_ATRIBUTO.finditer(corpo):
            chave, sep, bruto = m.group(1), m.group(2), m.group(3)
            if bruto is not None and bruto[:1] in "\"'":
                aspas, valor = bruto[0], bruto[1:-1]
            else:
                aspas, valor = '"', bruto
            attrs.append([chave, sep, aspas, valor])
        nomes = {a[0].lower() for a in attrs}
        rel = next((html_lib.unescape(a[3] or "") for a in attrs if a[0].lower() == "rel"), "").lower()
        src = next((html_lib.unescape(a[3] or "") for a in attrs if a[0].lower() == "src"), None)
        extras = []
        alterou_recurso = False

        for a in attrs:
            chave = a[0].lower()
            valor = a[3]
            if valor is None:
                continue
            bruto = html_lib.unescape(valor)
            if chave in ATRIBUTOS_URL:
                if nome_l == "a" and chave == "href":
                    continue
                if nome_l == "form" and chave == "action":
                    continue
                if nome_l == "link" and chave == "href" and any(r in rel for r in ("canonical", "alternate", "dns-prefetch", "preconnect", "next", "prev")):
                    continue
                if nome_l == "base" and chave == "href":
                    continue
                if nome_l == "iframe" and chave == "src":
                    alvo = absoluta(bruto, self.base)
                    if alvo and not self.localizar(alvo):
                        self.relatorio["omitidos"].append({"url": alvo, "motivo": "iframe externo (documento incorporado não é capturado)"})
                    continue
                novo = self._valor_url(bruto)
                if novo:
                    a[3] = novo
                    alterou_recurso = True
            elif chave in ATRIBUTOS_SRCSET:
                partes = []
                mudou = False
                for candidato in bruto.split(","):
                    tokens = candidato.strip().split()
                    if not tokens:
                        continue
                    novo = self._valor_url(tokens[0])
                    if novo:
                        tokens[0] = novo
                        mudou = True
                    partes.append(" ".join(tokens))
                if mudou:
                    a[3] = ", ".join(partes)
            elif chave == "style" and "url(" in bruto:
                css, n = reescrever_css(bruto, self.base, self.localizar, "assets/")
                if n:
                    a[3] = css

        # <base href> absoluto faria os caminhos locais apontarem de volta para o site
        if nome_l == "base":
            for a in attrs:
                if a[0].lower() == "href" and a[3] is not None:
                    extras.append(("data-vd-base-original", a[3]))
                    a[3] = "./"
                    self.relatorio["alteracoes"].append("<base href> trocado por ./ (marcado com data-vd-base-original)")

        # Rastreadores: neutralizados e marcados (não têm efeito visual)
        if nome_l == "script" and rastreador:
            self._neutralizar(attrs, extras, src or "script inline")

        # integrity deixa de valer quando o arquivo foi reescrito
        if alterou_recurso and "integrity" in nomes:
            for a in attrs:
                if a[0].lower() == "integrity":
                    a[0] = "data-vd-integrity-original"
                    self.relatorio["alteracoes"].append("integrity renomeado para data-vd-integrity-original")

        saida = [f"<{nome}"]
        for chave, sep, aspas, valor in attrs:
            if valor is None:
                saida.append(f" {chave}")
            else:
                saida.append(f" {chave}{sep or '='}{aspas}{self._escapar(valor, aspas)}{aspas}")
        for chave, valor in extras:
            saida.append(f' {chave}="{self._escapar(valor, chr(34))}"')
        fechamento = "/>" if corpo.rstrip().endswith("/") else ">"
        if fechamento == "/>" and saida[-1].endswith("/"):
            saida[-1] = saida[-1][:-1]
        return "".join(saida) + fechamento

    def _neutralizar(self, attrs, extras, src_ou_codigo):
        tipo = next((a for a in attrs if a[0].lower() == "type"), None)
        if tipo is not None:
            extras.append(("data-vd-type-original", tipo[3] or ""))
            tipo[3] = "text/plain"
        else:
            attrs.append(["type", "=", '"', "text/plain"])
        extras.append(("data-vd-neutralizado", "rastreador"))
        self.relatorio["neutralizados"].append(src_ou_codigo[:120])

    @staticmethod
    def _escapar(valor: str, aspas: str) -> str:
        if valor is None:
            return ""
        return valor.replace(aspas, "&quot;" if aspas == '"' else "&#39;")

    # -- documento -----------------------------------------------------------
    def reescrever(self, texto: str) -> str:
        saida = []
        i = 0
        n = len(texto)
        while i < n:
            j = texto.find("<", i)
            if j < 0:
                saida.append(texto[i:])
                break
            saida.append(texto[i:j])
            if texto.startswith("<!--", j):
                k = texto.find("-->", j + 4)
                k = n if k < 0 else k + 3
                saida.append(texto[j:k])
                i = k
                continue
            m = _RE_TAG.match(texto, j)
            if not m:
                saida.append("<")
                i = j + 1
                continue
            nome, corpo = m.group(1), m.group(2)
            nome_l = nome.lower()
            i = m.end()
            if nome_l in ("script", "style") and not corpo.rstrip().endswith("/"):
                fim = re.compile(rf"</{nome_l}\s*>", re.I).search(texto, i)
                k = fim.start() if fim else n
                conteudo = texto[i:k]
                rastreador = False
                if nome_l == "style":
                    conteudo, _ = reescrever_css(conteudo, self.base, self.localizar, "assets/")
                else:
                    tipo_m = re.search(r"""\btype\s*=\s*["']?([^"'\s>]+)""", corpo, re.I)
                    tipo = tipo_m.group(1).lower() if tipo_m else ""
                    src_m = re.search(r"""\bsrc\s*=\s*["']?([^"'\s>]+)""", corpo, re.I)
                    rastreador = eh_rastreador(html_lib.unescape(src_m.group(1)) if src_m else None, conteudo)
                    if not tipo or "javascript" in tipo or tipo == "module" or "json" in tipo:
                        conteudo, _ = reescrever_literais(conteudo, self.mapa_abs, "/assets/")
                saida.append(self._reescrever_tag(nome, corpo, rastreador))
                saida.append(conteudo)
                i = k
                continue
            nova_tag = self._reescrever_tag(nome, corpo)
            saida.append(nova_tag)
        return "".join(saida)


# ---------------------------------------------------------------------------
# Detecção de bloqueios
# ---------------------------------------------------------------------------

MARCADORES_TITULO = ["just a moment", "verify you are human", "checking your browser", "attention required", "access denied", "verificando", "verifique que você é humano"]
MARCADORES_CONTEUDO = ["/cdn-cgi/challenge", "cf-challenge", "challenge-platform", "cf-browser-verification", "datadome", "perimeterx", "px-captcha"]


def verificar_bloqueio(page) -> None:
    titulo = (page.title() or "").lower()
    if any(m in titulo for m in MARCADORES_TITULO):
        raise CapturaAbortada(f"desafio anti-bot detectado (título: {titulo!r}). A captura não contorna proteções.")
    conteudo = page.content().lower()
    if any(m in conteudo for m in MARCADORES_CONTEUDO):
        raise CapturaAbortada("desafio anti-bot detectado no conteúdo. A captura não contorna proteções.")
    texto = page.evaluate("document.body ? document.body.innerText.length : 0")
    senha_visivel = page.evaluate(
        "Array.from(document.querySelectorAll('input[type=password]')).some(e => e.offsetParent !== null)"
    )
    if senha_visivel and texto < 3000:
        raise CapturaAbortada("a página pede login. Páginas autenticadas não são capturadas.")
    captcha = page.evaluate(
        "!!document.querySelector('iframe[src*=\"recaptcha\"], iframe[src*=\"hcaptcha\"], iframe[src*=\"turnstile\"]')"
    )
    if captcha and texto < 3000:
        raise CapturaAbortada("a página exige CAPTCHA. A captura não contorna proteções.")


JS_IFRAME_DOMINANTE = r"""
() => {
  const vw = innerWidth, vh = innerHeight;
  let melhor = -1, area = 0;
  document.querySelectorAll('iframe').forEach((f, i) => {
    const r = f.getBoundingClientRect();
    const a = Math.max(0, Math.min(r.right, vw) - Math.max(r.left, 0)) * Math.max(0, Math.min(r.bottom, vh) - Math.max(r.top, 0));
    if (a > area) { area = a; melhor = i; }
  });
  const texto = document.body ? document.body.innerText.trim().length : 0;
  return {indice: melhor, cobertura: area / (vw * vh), texto};
}
"""


def escolher_frame(page):
    """Construtores publicam o site dentro de um iframe que ocupa a tela: usa o documento interno nesse caso.

    Devolve (frame, srcdoc). srcdoc vem preenchido quando o documento interno está no atributo srcdoc.
    """
    info = page.evaluate(JS_IFRAME_DOMINANTE)
    if info["indice"] < 0 or info["cobertura"] < 0.6 or info["texto"] > 600:
        return page.main_frame, None
    elemento = page.query_selector_all("iframe")[info["indice"]]
    frame = elemento.content_frame()
    if frame is None:
        return page.main_frame, None
    srcdoc = elemento.get_attribute("srcdoc")
    if srcdoc is None and frame.url in ("about:srcdoc", "about:blank"):
        srcdoc = None
    return frame, srcdoc


# ---------------------------------------------------------------------------
# Captura
# ---------------------------------------------------------------------------


def charset_de(content_type: str | None, corpo: bytes) -> str:
    m = re.search(r"charset=([\w\-]+)", content_type or "", re.I)
    if m:
        return m.group(1).lower()
    m = re.search(rb"<meta[^>]+charset=[\"']?([\w\-]+)", corpo[:4096], re.I)
    return m.group(1).decode().lower() if m else "utf-8"


def capturar(url: str, destino: Path, largura: int = 1440, altura: int = 900, limite_mb: float = 25,
             timeout_s: int = 60, log=print) -> dict:
    from playwright.sync_api import sync_playwright

    if not re.match(r"^https?://", url, re.I):
        raise ValueError("a URL precisa começar com http:// ou https://")
    destino = Path(destino)
    if destino.exists() and any(destino.iterdir()):
        raise FileExistsError(f"{destino} já existe e não está vazia; escolha outra pasta")
    limite = int(limite_mb * 1024 * 1024)

    respostas: dict[str, dict] = {}
    aliases: dict[str, set[str]] = {}
    parciais: set[str] = set()
    relatorio = {"omitidos": [], "neutralizados": [], "alteracoes": []}

    def ao_responder(resposta):
        try:
            u = sem_fragmento(resposta.url)
            if not u.startswith(("http://", "https://")):
                return
            status = resposta.status
            if status == 206:
                parciais.add(u)
                return
            if status != 200:
                if status >= 400:
                    relatorio["omitidos"].append({"url": u, "motivo": f"HTTP {status} no site original"})
                return
            tipo = resposta.headers.get("content-type", "")
            try:
                tamanho = int(resposta.headers.get("content-length") or 0)
            except ValueError:
                tamanho = 0
            if tamanho > limite:
                relatorio["omitidos"].append({"url": u, "motivo": f"maior que o limite ({tamanho} bytes)"})
                return
            try:
                corpo = resposta.body()
            except Exception:
                return
            if len(corpo) > limite:
                relatorio["omitidos"].append({"url": u, "motivo": f"maior que o limite ({len(corpo)} bytes)"})
                return
            try:
                frame = resposta.frame
            except Exception:
                frame = None
            respostas[u] = {"tipo": tipo, "corpo": corpo, "origem": "rede", "frame": frame}
            anterior = resposta.request.redirected_from
            while anterior is not None:
                aliases.setdefault(u, set()).add(sem_fragmento(anterior.url))
                anterior = anterior.redirected_from
        except Exception:
            pass

    with sync_playwright() as p:
        navegador = abrir_navegador(p)
        contexto = navegador.new_context(viewport={"width": largura, "height": altura}, device_scale_factor=1,
                                         service_workers="block")
        page = contexto.new_page()
        page.on("response", ao_responder)
        log(f"→ carregando {url}")
        page.goto(url, wait_until="load", timeout=timeout_s * 1000)
        esperar_rede(page)
        verificar_bloqueio(page)
        frame, srcdoc = escolher_frame(page)
        log("→ rolando a página para carregar conteúdo sob demanda")
        rolar_pagina(frame)
        esperar_rede(page)
        page.wait_for_timeout(1000)
        frame, srcdoc = escolher_frame(page)
        if srcdoc is not None:
            doc_url = sem_fragmento(page.url)
            origem_bytes = srcdoc.encode("utf-8")
            charset = "utf-8"
            log("→ conteúdo real está num iframe srcdoc; usando o documento interno")
        else:
            doc_url = sem_fragmento(frame.url)
            if frame != page.main_frame:
                log(f"→ conteúdo real está num iframe: {doc_url}")
            doc = respostas.get(doc_url)
            if doc is None:
                r = contexto.request.get(doc_url, timeout=timeout_s * 1000)
                doc = {"tipo": r.headers.get("content-type", ""), "corpo": r.body(), "origem": "complemento"}
            origem_bytes = doc["corpo"]
            charset = charset_de(doc["tipo"], origem_bytes)
        renderizado = frame.content()

        # Com invólucro, só interessa o que o documento interno pediu (o resto é o app do construtor)
        if frame != page.main_frame:
            internos = {frame}
            internos |= set(frame.child_frames)
            antes = len(respostas)
            for u in [u for u, r in respostas.items() if r.get("frame") is not None and r["frame"] not in internos]:
                del respostas[u]
            log(f"→ {antes - len(respostas)} recursos do invólucro descartados")

        try:
            origem_texto = origem_bytes.decode(charset)
        except (LookupError, UnicodeDecodeError):
            charset = "utf-8"
            origem_texto = origem_bytes.decode("utf-8", errors="replace")

        m_base = re.search(r"""<base\b[^>]*href\s*=\s*["']([^"']+)""", origem_texto, re.I)
        base = urljoin(doc_url, html_lib.unescape(m_base.group(1))) if m_base else doc_url

        # Complementos: recursos citados no HTML/CSS que o navegador não chegou a pedir
        def complementar(alvo: str, motivo: str):
            if alvo in respostas or alvo == doc_url or len(complementos) >= MAX_COMPLEMENTOS:
                return
            complementos.add(alvo)
            try:
                r = contexto.request.get(alvo, timeout=20000, max_redirects=5)
            except Exception as e:
                relatorio["omitidos"].append({"url": alvo, "motivo": f"falha ao baixar ({motivo}): {str(e)[:80]}"})
                return
            if r.status != 200:
                relatorio["omitidos"].append({"url": alvo, "motivo": f"HTTP {r.status} ({motivo})"})
                return
            corpo = r.body()
            if len(corpo) > limite:
                relatorio["omitidos"].append({"url": alvo, "motivo": "maior que o limite"})
                return
            respostas[alvo] = {"tipo": r.headers.get("content-type", ""), "corpo": corpo, "origem": "complemento"}

        complementos: set[str] = set()
        from vd_comum import parse_html, referencias_do_html  # import tardio: evita ciclo

        for _, attr, valor in referencias_do_html(parse_html(origem_texto)):
            alvo = absoluta(valor, base)
            if alvo:
                complementar(alvo, f"citado no HTML ({attr})")
        for u in sorted(parciais):
            complementar(u, "mídia carregada em partes")

        # CSS pode citar fontes e imagens não usadas na primeira dobra; @import em cadeia
        vistos_css: set[str] = set()
        while True:
            pendentes = [u for u, r in respostas.items() if tipo_base(r["tipo"]) == "text/css" and u not in vistos_css]
            if not pendentes:
                break
            for u in pendentes:
                vistos_css.add(u)
                css = respostas[u]["corpo"].decode("utf-8", errors="replace")
                for m in _RE_URL_CSS.finditer(css):
                    alvo = absoluta(m.group(2), u)
                    if alvo:
                        complementar(alvo, "citado em CSS")
                for m in _RE_IMPORT_CSS.finditer(css):
                    alvo = absoluta(m.group(3), u)
                    if alvo:
                        complementar(alvo, "@import")
        contexto.close()
        navegador.close()

    # ---- nomes de arquivo -----------------------------------------------------
    respostas.pop(doc_url, None)
    nomes: dict[str, str] = {}
    usados: set[str] = set()
    for u, r in sorted(respostas.items()):
        if not r["corpo"]:
            relatorio["omitidos"].append({"url": u, "motivo": "corpo vazio"})
            continue
        nome = nome_de_arquivo(u, r["tipo"])
        while nome in usados:
            nome = "x" + nome
        usados.add(nome)
        nomes[u] = nome
    alias_para: dict[str, str] = {}
    for u, origens in aliases.items():
        for a in origens:
            if u in nomes:
                alias_para[a] = nomes[u]

    def localizar(alvo: str | None) -> str | None:
        if not alvo:
            return None
        return nomes.get(alvo) or alias_para.get(alvo)

    mapa_abs = {**{a: n for a, n in alias_para.items()}, **nomes}

    # ---- reescrita dos recursos -------------------------------------------
    pasta_assets = destino / "assets"
    pasta_assets.mkdir(parents=True, exist_ok=True)
    recursos = []
    for u, nome in nomes.items():
        r = respostas[u]
        corpo = r["corpo"]
        base_tipo = tipo_base(r["tipo"])
        reescrito = False
        if base_tipo == "text/css" or nome.endswith(".css"):
            texto = corpo.decode("utf-8", errors="replace")
            texto, n = reescrever_css(texto, u, localizar, "")
            if n:
                corpo, reescrito = texto.encode("utf-8"), True
        elif nome.endswith((".js", ".json", ".mjs")):
            try:
                texto = corpo.decode("utf-8")
            except UnicodeDecodeError:
                texto = None
            if texto is not None:
                texto, n = reescrever_literais(texto, mapa_abs, "/assets/")
                if n:
                    corpo, reescrito = texto.encode("utf-8"), True
        (pasta_assets / nome).write_bytes(corpo)
        recursos.append({
            "url": u,
            "aliases": sorted(aliases.get(u, [])),
            "arquivo": f"assets/{nome}",
            "tipo": r["tipo"],
            "bytes": len(corpo),
            "sha256": sha256_bytes(corpo),
            "origem": r["origem"],
            "reescrito": reescrito,
        })

    # ---- HTML ---------------------------------------------------------------
    reescritor = ReescritorHTML(base, localizar, mapa_abs, relatorio)
    index_texto = reescritor.reescrever(origem_texto)
    if srcdoc is not None and not re.match(r"\s*<!doctype", index_texto, re.I):
        # Documentos srcdoc são sempre renderizados em modo padrão (no-quirks). Servido como página
        # comum, o mesmo HTML sem doctype cairia em quirks mode e mudaria alturas e layout.
        index_texto = "<!DOCTYPE html>\n" + index_texto
        relatorio["alteracoes"].append("<!DOCTYPE html> declarado: documentos srcdoc renderizam sempre em modo padrão")
    (destino / "index.html").write_bytes(index_texto.encode(charset, errors="xmlcharrefreplace"))
    (destino / "origem.html").write_bytes(origem_bytes)
    (destino / "renderizado.html").write_text(
        "<!-- vd: DOM renderizado após o JavaScript, salvo apenas para análise. Não servir. -->\n" + renderizado,
        encoding="utf-8",
    )

    vistos = set()
    omitidos = []
    for o in relatorio["omitidos"]:
        if o["url"] in nomes or o["url"] in vistos:
            continue
        vistos.add(o["url"])
        omitidos.append(o)

    captura = {
        "versao": VERSAO,
        "url": url,
        "url_documento": doc_url,
        "base": base,
        "data": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "viewport": {"largura": largura, "altura": altura},
        "modo": "fidelidade",
        "charset": charset,
        "srcdoc": srcdoc is not None,
        "recursos": sorted(recursos, key=lambda r: r["arquivo"]),
        "omitidos": omitidos,
        "neutralizados": relatorio["neutralizados"],
        "alteracoes": sorted(set(relatorio["alteracoes"])),
    }
    escrever_json(destino / "captura.json", captura)
    log(f"✓ {len(recursos)} recursos salvos, {len(omitidos)} omitidos, {len(relatorio['neutralizados'])} rastreadores neutralizados")
    return captura


def main():
    parser = argparse.ArgumentParser(description="Captura fiel de uma página para uso offline.")
    parser.add_argument("url")
    parser.add_argument("destino")
    parser.add_argument("--largura", type=int, default=1440)
    parser.add_argument("--altura", type=int, default=900)
    parser.add_argument("--limite-mb", type=float, default=25)
    parser.add_argument("--timeout", type=int, default=60, help="segundos para carregar a página")
    args = parser.parse_args()
    try:
        capturar(args.url, Path(args.destino), args.largura, args.altura, args.limite_mb, args.timeout)
    except CapturaAbortada as e:
        print(f"✗ captura abortada: {e}", file=sys.stderr)
        sys.exit(2)
    except (ValueError, FileExistsError) as e:
        print(f"✗ {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
