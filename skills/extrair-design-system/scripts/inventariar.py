#!/usr/bin/env python3
"""Etapa 2 da extração: inventaria a referência e grava manifesto-ds.json.

O manifesto é o contrato entre as skills: diz quais classes, cores, fontes,
keyframes, componentes e estilos tipográficos existem na fonte. O design system
e o site gerado só podem usar o que estiver aqui.

Parte estática (HTML e CSS) + parte renderizada (Playwright): tipografia,
componentes e layout são medidos na página servida em localhost.

Uso:
    python inventariar.py <pasta> [--sem-render] [--permitir-rede]
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sanitizar import registrar_hashes_antes  # noqa: E402
from vd_comum import (  # noqa: E402
    abrir_navegador,
    caminho_do_no,
    classes_de_css,
    classes_de_js,
    cores_em,
    css_inline_do_html,
    detectar_bibliotecas,
    encontrar,
    escrever_json,
    esperar_rede,
    estilos_de_atributo,
    eh_url_local,
    fontes_em_classes,
    fontes_em_css,
    idioma_do_documento,
    iter_nos,
    keyframes_em_css,
    ler_json,
    ler_texto,
    parse_html,
    referencias_do_html,
    resolver_local,
    scripts_inline,
    seletores_css,
    sha256_arquivo,
    transicoes_em_css,
    urls_de_css,
    ATRIBUTOS_COR_SVG,
)

VERSAO = "1.0"
NOMES_TIPOGRAFIA = {
    "h1": "Título 1", "h2": "Título 2", "h3": "Título 3", "h4": "Título 4",
}
TAMANHOS = ["G", "M", "P"]


# ---------------------------------------------------------------------------
# Coleta estática
# ---------------------------------------------------------------------------


def css_locais(pasta: Path, raiz) -> dict[str, str]:
    """Conteúdo de todos os CSS locais referenciados (com @import em cadeia)."""
    resultado: dict[str, str] = {}
    pendentes = []
    for n in iter_nos(raiz):
        if n.tag == "link" and "stylesheet" in (n.attr("rel") or "").lower() and eh_url_local(n.attr("href") or ""):
            alvo = resolver_local(pasta, n.attr("href"))
            if alvo:
                pendentes.append(alvo)
    for bloco in css_inline_do_html(raiz):
        for u in urls_de_css(bloco):
            if u.endswith(".css") and eh_url_local(u):
                alvo = resolver_local(pasta, u)
                if alvo:
                    pendentes.append(alvo)
    while pendentes:
        alvo = pendentes.pop()
        chave = alvo.as_posix()
        if chave in resultado or not alvo.is_file():
            continue
        texto = ler_texto(alvo)
        resultado[chave] = texto
        for u in urls_de_css(texto):
            if ".css" in u and eh_url_local(u):
                prox = resolver_local(alvo.parent, u)
                if prox:
                    pendentes.append(prox)
    return resultado


def js_locais(pasta: Path, raiz) -> dict[str, str]:
    resultado = {}
    for n in iter_nos(raiz):
        if n.tag == "script" and n.attr("src") and eh_url_local(n.attr("src")):
            alvo = resolver_local(pasta, n.attr("src"))
            if alvo and alvo.is_file() and alvo.stat().st_size < 3_000_000:
                resultado[alvo.as_posix()] = ler_texto(alvo)
    return resultado


def classificar_svgs(raiz) -> dict:
    """Categorias: A Lucide, B currentColor/herança, C cores fixas, D Iconify."""
    categorias = {"A": Counter(), "B": 0, "C": 0, "D": Counter()}
    exemplos = {"B": [], "C": []}
    for n in iter_nos(raiz):
        if n.tag == "i" and n.attr("data-lucide"):
            categorias["A"][n.attr("data-lucide")] += 1
        elif n.tag == "iconify-icon" and n.attr("icon"):
            categorias["D"][n.attr("icon")] += 1
        elif n.tag == "svg":
            if n.pai is not None and any(p.tag == "svg" for p in _ancestrais(n)):
                continue
            classes = n.classes
            if "lucide" in classes:
                nome = next((c[len("lucide-"):] for c in classes if c.startswith("lucide-")), "desconhecido")
                categorias["A"][nome] += 1
                continue
            texto_svg = _serializar_attrs(n)
            usa_current = "currentcolor" in texto_svg.lower()
            cores_fixas = cores_em(texto_svg)
            if usa_current or not cores_fixas:
                categorias["B"] += 1
                if len(exemplos["B"]) < 5:
                    exemplos["B"].append(caminho_do_no(n))
            else:
                categorias["C"] += 1
                if len(exemplos["C"]) < 5:
                    exemplos["C"].append(caminho_do_no(n))
    return {
        "A_lucide": [{"nome": k, "ocorrencias": v} for k, v in sorted(categorias["A"].items())],
        "B_heranca": {"quantidade": categorias["B"], "exemplos": exemplos["B"]},
        "C_cores_fixas": {"quantidade": categorias["C"], "exemplos": exemplos["C"]},
        "D_iconify": [{"nome": k, "ocorrencias": v} for k, v in sorted(categorias["D"].items())],
    }


def _ancestrais(no):
    atual = no.pai
    while atual is not None:
        yield atual
        atual = atual.pai


def _serializar_attrs(no) -> str:
    partes = []
    for n in [no] + list(iter_nos(no)):
        for k, v in n.attrs:
            if k in ATRIBUTOS_COR_SVG or k in ("style", "class"):
                partes.append(f"{k}={v or ''}")
    return " ".join(partes)


def total_icones(icones: dict) -> int:
    return (sum(i["ocorrencias"] for i in icones["A_lucide"]) + icones["B_heranca"]["quantidade"]
            + icones["C_cores_fixas"]["quantidade"] + sum(i["ocorrencias"] for i in icones["D_iconify"]))


def localizar_hero(raiz):
    """Primeiro bloco de conteúdo do body: o que contém o h1, ou a primeira seção depois do cabeçalho."""
    body = encontrar(raiz, "body") or raiz
    h1 = encontrar(body, "h1")
    if h1 is not None:
        atual = h1
        while atual.pai is not None and atual.pai is not body and atual.pai.tag not in ("main",):
            if atual.tag in ("section", "header") and atual is not h1:
                return atual
            atual = atual.pai
        return atual
    for n in body.elementos:
        if n.tag in ("section", "main", "div") and n.tag != "script":
            return n
    return None


# ---------------------------------------------------------------------------
# Medição renderizada
# ---------------------------------------------------------------------------

JS_TEXTOS = r"""
() => {
  const caminho = (e) => { const p = []; while (e && e !== document.body && e.parentElement) { const irmaos = Array.from(e.parentElement.children).filter(x => x.tagName === e.tagName); p.unshift(e.tagName.toLowerCase() + ':nth-of-type(' + (irmaos.indexOf(e) + 1) + ')'); e = e.parentElement; } return 'body > ' + p.join(' > '); };
  const saida = [];
  for (const e of document.body.querySelectorAll('*')) {
    const tag = e.tagName.toLowerCase();
    if (['script','style','svg','noscript','template','option'].includes(tag) || e.closest('svg')) continue;
    const direto = Array.from(e.childNodes).filter(n => n.nodeType === 3).map(n => n.textContent.trim()).join(' ').trim();
    if (!direto || direto.length < 2) continue;
    const r = e.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;
    const s = getComputedStyle(e);
    if (s.visibility === 'hidden' || s.display === 'none') continue;
    const tamanho = parseFloat(s.fontSize);
    const entrelinha = s.lineHeight === 'normal' ? tamanho * 1.2 : parseFloat(s.lineHeight);
    saida.push({tag, classes: e.getAttribute('class') || '', seletor: caminho(e), familia: s.fontFamily,
      tamanho, entrelinha, peso: parseInt(s.fontWeight, 10), estilo: s.fontStyle, espacamento: s.letterSpacing,
      transformacao: s.textTransform, texto: direto.slice(0, 80), caracteres: direto.length});
  }
  return saida;
}
"""

JS_COMPONENTES = r"""
() => {
  const caminho = (e) => { const p = []; while (e && e !== document.body && e.parentElement) { const irmaos = Array.from(e.parentElement.children).filter(x => x.tagName === e.tagName); p.unshift(e.tagName.toLowerCase() + ':nth-of-type(' + (irmaos.indexOf(e) + 1) + ')'); e = e.parentElement; } return 'body > ' + p.join(' > '); };
  const visivel = (e) => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const pareceBotao = (e) => {
    const s = getComputedStyle(e);
    const fundo = s.backgroundColor !== 'rgba(0, 0, 0, 0)' || s.backgroundImage !== 'none';
    const borda = parseFloat(s.borderTopWidth) > 0;
    return (fundo || borda) && parseFloat(s.paddingLeft) >= 8;
  };
  const grupos = {botoes: [], campos: [], cartoes: []};
  for (const e of document.body.querySelectorAll('button, a, [role=button], input[type=submit], input[type=button]')) {
    if (!visivel(e)) continue;
    if (e.tagName === 'BUTTON' || e.getAttribute('role') === 'button' || pareceBotao(e))
      grupos.botoes.push({tag: e.tagName.toLowerCase(), classes: e.getAttribute('class') || '', seletor: caminho(e), texto: (e.innerText || e.value || '').trim().slice(0, 50), desabilitado: e.disabled || e.getAttribute('aria-disabled') === 'true'});
  }
  for (const e of document.body.querySelectorAll('input:not([type=hidden]):not([type=submit]):not([type=button]), select, textarea')) {
    if (!visivel(e)) continue;
    grupos.campos.push({tag: e.tagName.toLowerCase(), tipo: e.getAttribute('type') || '', classes: e.getAttribute('class') || '', seletor: caminho(e)});
  }
  for (const e of document.body.querySelectorAll('article, li, div')) {
    if (!visivel(e)) continue;
    const s = getComputedStyle(e), r = e.getBoundingClientRect();
    const arredondado = parseFloat(s.borderTopLeftRadius) >= 6;
    const destacado = parseFloat(s.borderTopWidth) > 0 || s.boxShadow !== 'none' || s.backgroundColor !== 'rgba(0, 0, 0, 0)';
    if (arredondado && destacado && r.width >= 180 && r.width <= 720 && r.height >= 100 && e.children.length >= 2)
      grupos.cartoes.push({tag: e.tagName.toLowerCase(), classes: e.getAttribute('class') || '', seletor: caminho(e)});
  }
  return grupos;
}
"""

JS_LAYOUT = r"""
() => {
  const caminho = (e) => { const p = []; while (e && e !== document.body && e.parentElement) { const irmaos = Array.from(e.parentElement.children).filter(x => x.tagName === e.tagName); p.unshift(e.tagName.toLowerCase() + ':nth-of-type(' + (irmaos.indexOf(e) + 1) + ')'); e = e.parentElement; } return 'body > ' + p.join(' > '); };
  const conteineres = [], grades = [];
  for (const e of document.body.querySelectorAll('*')) {
    const s = getComputedStyle(e), r = e.getBoundingClientRect();
    if (r.width === 0) continue;
    if (s.maxWidth !== 'none' && s.marginLeft === s.marginRight && parseFloat(s.marginLeft) > 0 && r.width > 600)
      conteineres.push({seletor: caminho(e), classes: e.getAttribute('class') || '', largura_maxima: s.maxWidth, largura: Math.round(r.width)});
    if (s.display === 'grid' && s.gridTemplateColumns.split(' ').length >= 2 && r.width > 400)
      grades.push({seletor: caminho(e), classes: e.getAttribute('class') || '', colunas: s.gridTemplateColumns, espaco: s.gap});
  }
  const secoes = Array.from(document.querySelectorAll('section, header, footer, main > *')).slice(0, 20).map(e => {
    const s = getComputedStyle(e);
    return {seletor: caminho(e), classes: e.getAttribute('class') || '', padding: s.paddingTop + ' ' + s.paddingRight + ' ' + s.paddingBottom + ' ' + s.paddingLeft};
  });
  return {conteineres: conteineres.slice(0, 8), grades: grades.slice(0, 10), secoes};
}
"""


def _px(valor: float) -> str:
    texto = f"{round(valor, 1):.1f}".rstrip("0").rstrip(".")
    return f"{texto}px"


def classificar_tipografia(textos: list[dict]) -> list[dict]:
    """Agrupa os textos medidos nas categorias Título 1–4, Negrito G/M/P, Parágrafo e Regular G/M/P."""

    def assinatura(t):
        return (t["familia"].split(",")[0].strip().strip("'\""), round(t["tamanho"], 1), round(t["entrelinha"], 1), t["peso"])

    estilos = []

    def adicionar(nome: str, amostras: list[dict]):
        # usa a assinatura mais frequente; desempata pelo maior número de caracteres
        contagem = Counter(assinatura(t) for t in amostras)
        alvo, _ = contagem.most_common(1)[0]
        exemplo = max((t for t in amostras if assinatura(t) == alvo), key=lambda t: t["caracteres"])
        estilos.append({
            "estilo": nome,
            "tag": exemplo["tag"],
            "seletor_exemplo": exemplo["seletor"],
            "classes": exemplo["classes"],
            "familia": exemplo["familia"],
            "tamanho": _px(exemplo["tamanho"]),
            "entrelinha": _px(exemplo["entrelinha"]),
            "peso": exemplo["peso"],
            "estilo_fonte": exemplo["estilo"],
            "espacamento": exemplo["espacamento"],
            "caixa": exemplo["transformacao"],
            "exemplo_texto": exemplo["texto"],
        })

    for tag, nome in NOMES_TIPOGRAFIA.items():
        amostras = [t for t in textos if t["tag"] == tag]
        if amostras:
            adicionar(nome, amostras)

    corpo = [t for t in textos if t["tag"] not in ("h1", "h2", "h3", "h4", "h5", "h6")]
    negrito = [t for t in corpo if t["peso"] >= 600]
    tamanhos_negrito = [s for s, _ in Counter(round(t["tamanho"], 1) for t in negrito).most_common(3)]
    for i, tamanho in enumerate(sorted(tamanhos_negrito, reverse=True)):
        adicionar(f"Negrito {TAMANHOS[i]}", [t for t in negrito if round(t["tamanho"], 1) == tamanho])

    regulares = [t for t in corpo if t["peso"] < 600]
    paragrafos = [t for t in regulares if t["tag"] == "p"]
    tamanho_paragrafo = None
    if paragrafos:
        adicionar("Parágrafo", paragrafos)
        tamanho_paragrafo = float(estilos[-1]["tamanho"][:-2])
    outros = [t for t in regulares if round(t["tamanho"], 1) != tamanho_paragrafo]
    tamanhos_regular = [s for s, _ in Counter(round(t["tamanho"], 1) for t in outros).most_common(3)]
    for i, tamanho in enumerate(sorted(tamanhos_regular, reverse=True)):
        adicionar(f"Regular {TAMANHOS[i]}", [t for t in outros if round(t["tamanho"], 1) == tamanho])
    return estilos


def _agrupar(itens: list[dict], limite: int = 8) -> list[dict]:
    vistos = {}
    for item in itens:
        chave = (item.get("tag"), item.get("classes"))
        if chave not in vistos:
            vistos[chave] = {**item, "ocorrencias": 1}
        else:
            vistos[chave]["ocorrencias"] += 1
    return sorted(vistos.values(), key=lambda x: -x["ocorrencias"])[:limite]


def medir(pasta: Path, pagina: str, permitir_rede: bool) -> dict:
    from playwright.sync_api import sync_playwright

    from servir import iniciar_servidor

    replay = (pasta / "captura.json").exists()
    servidor, base, entrada = iniciar_servidor(pasta, replay=replay, permitir_rede=permitir_rede, entrada="/" + pagina)
    try:
        with sync_playwright() as p:
            nav = abrir_navegador(p, offline=not permitir_rede)
            page = nav.new_page(viewport={"width": 1440, "height": 900})
            page.goto(entrada, wait_until="load", timeout=60000)
            if replay:
                page.wait_for_url(re.compile(re.escape(pagina)), timeout=20000)
            esperar_rede(page)
            page.wait_for_timeout(1500)
            textos = page.evaluate(JS_TEXTOS)
            componentes = page.evaluate(JS_COMPONENTES)
            layout = page.evaluate(JS_LAYOUT)
            nav.close()
    finally:
        servidor.shutdown()
        servidor.server_close()
    return {"textos": textos, "componentes": componentes, "layout": layout}


# ---------------------------------------------------------------------------
# Manifesto
# ---------------------------------------------------------------------------


def inventariar(pasta: Path, renderizar: bool = True, permitir_rede: bool = False) -> dict:
    pasta = Path(pasta).resolve()
    registrar_hashes_antes(pasta)
    pagina = "vd-analise.html" if (pasta / "vd-analise.html").exists() else "index.html"
    html = ler_texto(pasta / pagina)
    raiz = parse_html(html)

    css = css_locais(pasta, raiz)
    blocos_inline = css_inline_do_html(raiz)
    atributos_style = estilos_de_atributo(raiz)
    css_total = "\n".join(list(css.values()) + blocos_inline)
    js = js_locais(pasta, raiz)
    js_inline = "\n".join(n.texto_bruto() for n in scripts_inline(raiz))

    classes = set()
    for n in iter_nos(raiz):
        classes |= set(n.classes)
    renderizado = pasta / "renderizado.html"
    if renderizado.exists():
        for n in iter_nos(parse_html(ler_texto(renderizado))):
            classes |= set(n.classes)
    classes |= classes_de_css(css_total)
    classes |= classes_de_js(js_inline + "\n" + "\n".join(js.values()))

    texto_cores = css_total + "\n" + "\n".join(atributos_style) + "\n" + js_inline + "\n" + " ".join(classes)
    for n in iter_nos(raiz):
        for k, v in n.attrs:
            if k in ATRIBUTOS_COR_SVG and v:
                texto_cores += f"\n{v}"
    cores = cores_em(texto_cores)

    fontes = fontes_em_css(css_total) | fontes_em_css("\n".join(f"x{{{a}}}" for a in atributos_style)) | fontes_em_classes(classes)
    for m in re.finditer(r"font-family\s*=\s*[\"']([^\"']+)", html):
        fontes |= {f.strip().strip("'\"").lower() for f in m.group(1).split(",") if f.strip()}
    for m in re.finditer(r"--font-[\w-]+\s*:\s*([^;]+);", css_total + js_inline):
        fontes |= {f.strip().strip("'\"").lower() for f in m.group(1).split(",") if f.strip() and not f.strip().startswith("var(")}

    keyframes = keyframes_em_css(css_total)
    transicoes = sorted(transicoes_em_css(css_total))
    estados = sorted({s for s in seletores_css(css_total) if re.search(r":(hover|focus|focus-visible|active|disabled)", s)})[:120]
    estados_classes = sorted(c for c in classes if re.match(r"^(?:[\w-]+:)*(hover|focus|focus-visible|active|disabled|group-hover):", c))

    refs = [v for _, _, v in referencias_do_html(raiz)]
    # capturas renomeiam arquivos: as URLs originais ajudam a reconhecer bibliotecas
    captura = ler_json(pasta / "captura.json", {}) or {}
    origem_de = {r["arquivo"]: r["url"] for r in captura.get("recursos", [])}
    bibliotecas = detectar_bibliotecas(html, refs + [origem_de[r] for r in refs if r in origem_de])
    icones = classificar_svgs(raiz)
    hero = localizar_hero(raiz)

    body = encontrar(raiz, "body") or raiz
    secoes = []
    for n in body.elementos:
        if n.tag in ("script", "style", "noscript", "template"):
            continue
        titulo = next((h.texto().strip() for h in iter_nos(n) if h.tag in ("h1", "h2", "h3")), "")
        secoes.append({"seletor": caminho_do_no(n), "tag": n.tag, "id": n.attr("id") or "",
                       "classes": " ".join(n.classes[:8]), "titulo": " ".join(titulo.split())[:80]})
        if n.tag in ("main", "div") and len(n.elementos) > 1:
            for f in n.elementos:
                if f.tag in ("section", "header", "footer", "article", "div"):
                    t = next((h.texto().strip() for h in iter_nos(f) if h.tag in ("h1", "h2", "h3")), "")
                    secoes.append({"seletor": caminho_do_no(f), "tag": f.tag, "id": f.attr("id") or "",
                                   "classes": " ".join(f.classes[:8]), "titulo": " ".join(t.split())[:80]})

    manifesto = {
        "versao": VERSAO,
        "fonte": "index.html",
        "pagina_analisada": pagina,
        "hash_fonte": sha256_arquivo(pasta / "index.html"),
        "idioma_fonte": idioma_do_documento(raiz),
        "bibliotecas": bibliotecas,
        "classes": sorted(classes),
        "cores": sorted(cores),
        "fontes": sorted(fontes),
        "keyframes": sorted(keyframes),
        "transicoes": transicoes[:200],
        "estados": {"seletores_css": estados, "classes": estados_classes[:200]},
        "icones": icones,
        "total_icones": total_icones(icones),
        "hero": {"seletor": caminho_do_no(hero), "tag": hero.tag, "classes": " ".join(hero.classes)} if hero is not None else None,
        "secoes": secoes[:30],
        "css_locais": sorted(Path(c).relative_to(pasta).as_posix() for c in css if Path(c).is_relative_to(pasta)),
        "blocos_inline": {"style": len(blocos_inline), "script": len(scripts_inline(raiz))},
        "assets": sorted({v for v in refs if eh_url_local(v)})[:400],
        "tipografia": [],
        "componentes": {},
        "layout": {},
    }

    if renderizar:
        medidas = medir(pasta, pagina, permitir_rede)
        manifesto["tipografia"] = classificar_tipografia(medidas["textos"])
        manifesto["componentes"] = {
            "botoes": _agrupar(medidas["componentes"]["botoes"]),
            "campos": _agrupar(medidas["componentes"]["campos"]),
            "cartoes": _agrupar(medidas["componentes"]["cartoes"], 6),
        }
        manifesto["layout"] = medidas["layout"]
        # fontes efetivamente usadas na página também contam como fonte
        for t in medidas["textos"]:
            manifesto["fontes"] = sorted(set(manifesto["fontes"]) | {f.strip().strip("'\"").lower() for f in t["familia"].split(",") if f.strip()})

    escrever_json(pasta / "manifesto-ds.json", manifesto)
    return manifesto


def main():
    parser = argparse.ArgumentParser(description="Inventaria a referência e grava manifesto-ds.json.")
    parser.add_argument("pasta")
    parser.add_argument("--sem-render", action="store_true", help="só análise estática (sem tipografia medida)")
    parser.add_argument("--permitir-rede", action="store_true", help="deixa a página buscar recursos fora da pasta")
    args = parser.parse_args()
    m = inventariar(Path(args.pasta), renderizar=not args.sem_render, permitir_rede=args.permitir_rede)
    print(f"classes: {len(m['classes'])} · cores: {len(m['cores'])} · fontes: {len(m['fontes'])} · "
          f"keyframes: {len(m['keyframes'])} · ícones: {m['total_icones']} · estilos tipográficos: {len(m['tipografia'])}")
    print("bibliotecas: " + ", ".join(b["nome"] for b in m["bibliotecas"]) if m["bibliotecas"] else "bibliotecas: nenhuma")


if __name__ == "__main__":
    main()
