#!/usr/bin/env python3
"""Verifica um site gerado pela skill criar-site contra os critérios B1–B13.

B1  Seções do PLANO.md existem com o id declarado; nenhuma seção fora do plano.
B2  Referências locais resolvem.
B3  Classes ⊆ classes dos manifestos declarados (ou [classe] no DESVIOS.md).
B4  Cores e fontes literais ⊆ as dos manifestos (ou [cor]/[fonte] no DESVIOS.md).
B5  Há movimento (animação ou transição) e todo @keyframes vem dos manifestos.
B6  Nenhum erro de console ao carregar.
B7  Nenhuma requisição a terceiros (exceto [externo] no DESVIOS.md).
B8  Sem rolagem horizontal em 360, 768 e 1440 px.
B9  lang pt-BR, title, meta description, viewport, og:title, og:description,
    um único h1, sem salto de nível de heading, ids únicos.
B10 alt em toda img; nome acessível em links, botões e campos; contraste AA
    (exceto [contraste] aprovado no DESVIOS.md); prefers-reduced-motion quando há
    movimento; foco visível em todo elemento focável.
B11 img com width/height ou aspect-ratio; lazy abaixo da primeira dobra; nenhum
    arquivo sem uso em assets/; peso total reportado.
B12 target=_blank com rel="noopener noreferrer"; nenhum rastreador.
B13 PLANO.md e DESVIOS.md existem; relatorio-verificacao.md é gerado.

Uso:
    python verificar_site.py <pasta-do-site> [--ds <pasta-da-referencia> ...]
Sem --ds, usa as pastas declaradas no PLANO.md ("Design system primário/secundário: <caminho>").
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent.parent / "extrair-design-system" / "scripts"))
from vd_comum import (  # noqa: E402
    ATRIBUTOS_COR_SVG,
    abrir_navegador,
    cores_em,
    eh_rastreador,
    eh_url_local,
    encontrar,
    encontrar_todos,
    esperar_rede,
    familias_de_declaracao,
    fontes_em_classes,
    fontes_em_css,
    iter_nos,
    keyframes_em_css,
    ler_json,
    ler_texto,
    parse_html,
    referencias_do_html,
    resolver_local,
    urls_de_css,
    EXTENSOES_TEXTO,
)

LARGURAS = [360, 768, 1440]


# ---------------------------------------------------------------------------
# Leitura de PLANO.md e DESVIOS.md
# ---------------------------------------------------------------------------


def ler_plano(pasta: Path) -> dict:
    caminho = pasta / "PLANO.md"
    if not caminho.exists():
        return {"existe": False, "secoes": [], "ds": []}
    texto = ler_texto(caminho)
    secoes = re.findall(r"^\s*[-*]\s+`?#([a-z0-9][\w-]*)`?", texto, re.M | re.I)
    ds = re.findall(r"design system (?:primário|secundário)\s*:\s*`?([^`\n]+?)`?\s*$", texto, re.M | re.I)
    return {"existe": True, "secoes": secoes, "ds": [d.strip() for d in ds]}


def ler_desvios(pasta: Path) -> dict[str, list[str]]:
    caminho = pasta / "DESVIOS.md"
    desvios: dict[str, list[str]] = {}
    if not caminho.exists():
        return desvios
    for linha in ler_texto(caminho).splitlines():
        m = re.match(r"\s*[-*]\s+\[(\w+)\]\s+`?([^`—–]+?)`?\s*(?:[—–-]\s+(.*))?$", linha)
        if m:
            desvios.setdefault(m.group(1).lower(), []).append((m.group(2).strip(), (m.group(3) or "").strip()))
    return desvios


def nomes(desvios, tipo) -> set[str]:
    return {n for n, _ in desvios.get(tipo, [])}


# ---------------------------------------------------------------------------
# Coleta estática do site
# ---------------------------------------------------------------------------


def css_do_site(pasta: Path, raiz) -> dict[str, str]:
    resultado = {}
    for n in iter_nos(raiz):
        if n.tag == "link" and "stylesheet" in (n.attr("rel") or "").lower() and eh_url_local(n.attr("href") or ""):
            alvo = resolver_local(pasta, n.attr("href"))
            if alvo and alvo.is_file():
                resultado[alvo.relative_to(pasta).as_posix()] = ler_texto(alvo)
    return resultado


def verificar_estatico(pasta: Path, manifestos: list[dict], plano: dict, desvios: dict) -> tuple[dict, dict]:
    html = ler_texto(pasta / "index.html")
    raiz = parse_html(html)
    css = css_do_site(pasta, raiz)
    css_inline = "\n".join(n.texto_bruto() for n in iter_nos(raiz) if n.tag == "style")
    css_total = "\n".join(css.values()) + "\n" + css_inline
    criterios = {}

    # B1
    ids = [n.attr("id") for n in iter_nos(raiz) if n.attr("id")]
    faltando = [s for s in plano["secoes"] if s not in ids]
    secoes_topo = []
    for n in iter_nos(raiz):
        if n.tag == "section" and not any(a.tag == "section" for a in _ancestrais(n)):
            secoes_topo.append(n.attr("id") or "(sem id)")
    fora = [s for s in secoes_topo if s not in plano["secoes"]]
    criterios["B1"] = {"aprovado": plano["existe"] and bool(plano["secoes"]) and not faltando and not fora,
                       "faltando": faltando, "fora_do_plano": fora}

    # B2
    quebradas = []
    for _, _, url in referencias_do_html(raiz):
        if eh_url_local(url):
            alvo = resolver_local(pasta, url)
            if alvo is None or not alvo.exists():
                quebradas.append(url)
    for nome, texto in css.items():
        for url in urls_de_css(texto):
            if eh_url_local(url):
                alvo = resolver_local((pasta / nome).parent, url)
                if alvo is None or not alvo.exists():
                    quebradas.append(f"{nome}: {url}")
    criterios["B2"] = {"aprovado": not quebradas, "quebradas": quebradas[:20]}

    # B3
    classes_fonte = set().union(*[set(m["classes"]) for m in manifestos]) if manifestos else set()
    classes_site = set()
    for n in iter_nos(raiz):
        classes_site |= set(n.classes)
    novas = sorted(c for c in classes_site - classes_fonte if c not in nomes(desvios, "classe"))
    criterios["B3"] = {"aprovado": bool(manifestos) and not novas, "classes_fora_dos_manifestos": novas[:40]}

    # B4
    texto_cores = css_total + "\n" + " ".join(classes_site)
    fontes_site = fontes_em_css(css_total) | fontes_em_classes(classes_site)
    for n in iter_nos(raiz):
        for k, v in n.attrs:
            if v and (k == "style" or k in ATRIBUTOS_COR_SVG):
                texto_cores += "\n" + v
            if k == "style" and v:
                for m in re.finditer(r"font-family\s*:\s*([^;]+)", v):
                    fontes_site |= familias_de_declaracao(m.group(1))
            if k == "font-family" and v:
                fontes_site |= familias_de_declaracao(v)
    cores_fonte = set().union(*[set(m["cores"]) for m in manifestos]) if manifestos else set()
    fontes_fonte = set().union(*[set(m["fontes"]) for m in manifestos]) if manifestos else set()
    cores_novas = sorted(c for c in cores_em(texto_cores) if c not in cores_fonte and c not in nomes(desvios, "cor"))
    fontes_novas = sorted(f for f in fontes_site if f not in fontes_fonte and f not in {x.lower() for x in nomes(desvios, "fonte")})
    criterios["B4"] = {"aprovado": not cores_novas and not fontes_novas, "cores_fora": cores_novas[:20], "fontes_fora": fontes_novas}

    # B5
    kf_fonte = set().union(*[set(m["keyframes"]) for m in manifestos]) if manifestos else set()
    kf_site = keyframes_em_css(css_total)
    tem_movimento = bool(re.search(r"(?<![\w-])(animation|transition)\s*:", css_total)) or any(
        re.match(r"^(?:[\w-]+:)*(animate-|transition)", c) for c in classes_site)
    kf_novos = sorted(k for k in kf_site if k not in kf_fonte)
    criterios["B5"] = {"aprovado": tem_movimento and not kf_novos, "tem_movimento": tem_movimento, "keyframes_fora": kf_novos}

    # B9
    head = encontrar(raiz, "head") or raiz
    html_no = encontrar(raiz, "html")
    lang = ((html_no.attr("lang") if html_no else "") or "").lower()
    metas = {(m.attr("name") or m.attr("property") or "").lower(): (m.attr("content") or "") for m in encontrar_todos(head, "meta")}
    titulo = encontrar(head, "title")
    headings = [int(n.tag[1]) for n in iter_nos(raiz) if re.fullmatch(r"h[1-6]", n.tag)]
    saltos = [f"h{a}→h{b}" for a, b in zip(headings, headings[1:]) if b > a + 1]
    duplicados = sorted({i for i in ids if ids.count(i) > 1})
    problemas = []
    if not lang.startswith("pt"):
        problemas.append(f"lang={lang!r}")
    if not (titulo and titulo.texto().strip()):
        problemas.append("title vazio")
    for chave in ("description", "viewport", "og:title", "og:description"):
        if not metas.get(chave):
            problemas.append(f"meta {chave} ausente")
    if headings.count(1) != 1:
        problemas.append(f"{headings.count(1)} h1")
    criterios["B9"] = {"aprovado": not problemas and not saltos and not duplicados, "problemas": problemas,
                       "saltos_de_heading": saltos, "ids_duplicados": duplicados}

    # B11 (parte estática): arquivos sem uso
    textos = html + "\n" + css_total
    for raiz_dir, _, arquivos in os.walk(pasta / "assets"):
        for nome in arquivos:
            if Path(nome).suffix.lower() in EXTENSOES_TEXTO:
                textos += "\n" + ler_texto(Path(raiz_dir) / nome)
    sem_uso, peso = [], 0
    for raiz_dir, _, arquivos in os.walk(pasta / "assets"):
        for nome in arquivos:
            caminho = Path(raiz_dir) / nome
            if nome.startswith(".") or nome.endswith((".txt", ".md")):
                continue  # licenças acompanham os arquivos
            peso += caminho.stat().st_size
            if nome not in textos:
                sem_uso.append(caminho.relative_to(pasta).as_posix())

    # B12
    alvos = []
    for a in encontrar_todos(raiz, "a"):
        if (a.attr("target") or "") == "_blank":
            rel = (a.attr("rel") or "").lower().split()
            if "noopener" not in rel or "noreferrer" not in rel:
                alvos.append(a.attr("href"))
    rastreadores = [n.attr("src") or "inline" for n in iter_nos(raiz) if n.tag == "script" and eh_rastreador(n.attr("src"), n.texto_bruto())]
    criterios["B12"] = {"aprovado": not alvos and not rastreadores, "links_sem_rel": alvos, "rastreadores": rastreadores}

    extras = {"tem_movimento": tem_movimento, "css_total": css_total, "sem_uso": sem_uso, "peso": peso}
    return criterios, extras


def _ancestrais(no):
    atual = no.pai
    while atual is not None:
        yield atual
        atual = atual.pai


# ---------------------------------------------------------------------------
# Verificação no navegador
# ---------------------------------------------------------------------------

JS_A11Y = r"""
() => {
  const parse = c => { const m = c && c.match(/rgba?\(([^)]+)\)/); if (!m) return null; const p = m[1].split(/[\s,\/]+/).filter(Boolean).map(Number); return {r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1}; };
  const lum = ({r, g, b}) => { const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b); };
  const sobre = (c, f) => ({r: c.r * c.a + f.r * (1 - c.a), g: c.g * c.a + f.g * (1 - c.a), b: c.b * c.a + f.b * (1 - c.a), a: 1});
  const caminho = (e) => { const p = []; while (e && e !== document.body && e.parentElement) { const irmaos = Array.from(e.parentElement.children).filter(x => x.tagName === e.tagName); p.unshift(e.tagName.toLowerCase() + ':nth-of-type(' + (irmaos.indexOf(e) + 1) + ')'); e = e.parentElement; } return 'body > ' + p.join(' > '); };
  const fundo = (el) => {
    const camadas = []; let e = el;
    while (e && e.nodeType === 1) {
      const s = getComputedStyle(e);
      if (s.backgroundImage !== 'none') return null;
      const c = parse(s.backgroundColor);
      if (c && c.a > 0) { camadas.push(c); if (c.a >= 1) break; }
      e = e.parentElement;
    }
    let base = {r: 255, g: 255, b: 255, a: 1};
    for (const c of camadas.reverse()) base = sobre(c, base);
    return base;
  };
  const contraste = [], manual = [], semAlt = [], semNome = [], semRotulo = [];
  for (const e of document.body.querySelectorAll('*')) {
    if (e.closest('svg, [aria-hidden="true"], :disabled, [aria-disabled="true"]')) continue;
    const direto = Array.from(e.childNodes).some(n => n.nodeType === 3 && n.textContent.trim());
    if (!direto) continue;
    const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
    if (r.width === 0 || r.height === 0 || s.visibility === 'hidden' || parseFloat(s.opacity) === 0) continue;
    const cor = parse(s.color); const bg = fundo(e);
    if (!cor) continue;
    if (!bg) { manual.push(caminho(e)); continue; }
    const c = sobre(cor, bg);
    const L1 = lum(c), L2 = lum(bg);
    const razao = (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
    const tamanho = parseFloat(s.fontSize), peso = parseInt(s.fontWeight, 10);
    const grande = tamanho >= 24 || (tamanho >= 18.66 && peso >= 700);
    if (razao < (grande ? 3 : 4.5)) contraste.push({seletor: caminho(e), razao: Math.round(razao * 100) / 100, texto: e.textContent.trim().slice(0, 40)});
  }
  for (const img of document.querySelectorAll('img')) if (!img.hasAttribute('alt')) semAlt.push(img.getAttribute('src'));
  const nome = (e) => (e.getAttribute('aria-label') || e.getAttribute('title') || e.innerText || '').trim() || (e.getAttribute('aria-labelledby') && document.getElementById(e.getAttribute('aria-labelledby'))?.innerText) || (e.querySelector('img[alt]:not([alt=""])') ? 'img' : '');
  for (const e of document.querySelectorAll('a[href], button, [role=button]')) if (!nome(e)) semNome.push(caminho(e));
  for (const e of document.querySelectorAll('input:not([type=hidden]):not([type=submit]):not([type=button]), select, textarea')) {
    const rot = e.getAttribute('aria-label') || e.getAttribute('aria-labelledby') || (e.id && document.querySelector('label[for="' + e.id + '"]')) || e.closest('label');
    if (!rot) semRotulo.push(caminho(e));
  }
  return {contraste, manual: manual.slice(0, 20), semAlt, semNome, semRotulo};
}
"""

JS_FOCAVEIS = r"""
() => {
  const sel = 'a[href], button:not(:disabled), input:not(:disabled):not([type=hidden]), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])';
  const assinatura = (e) => { const s = getComputedStyle(e); return [s.outlineStyle, s.outlineWidth, s.outlineColor, s.boxShadow, s.borderColor, s.backgroundColor, s.color, s.textDecorationLine].join('|'); };
  const lista = Array.from(document.querySelectorAll(sel)).filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; });
  lista.forEach((e, i) => { e.dataset.vdFoco = String(i); });
  return lista.map(e => assinatura(e));
}
"""

JS_FOCO_ATUAL = r"""
() => {
  const e = document.activeElement;
  if (!e || !e.dataset || e.dataset.vdFoco === undefined) return null;
  const s = getComputedStyle(e);
  return {i: Number(e.dataset.vdFoco), assinatura: [s.outlineStyle, s.outlineWidth, s.outlineColor, s.boxShadow, s.borderColor, s.backgroundColor, s.color, s.textDecorationLine].join('|'), tag: e.tagName.toLowerCase(), texto: (e.innerText || e.getAttribute('aria-label') || '').trim().slice(0, 30)};
}
"""

JS_IMAGENS = r"""
() => Array.from(document.querySelectorAll('img')).map(img => {
  const r = img.getBoundingClientRect(); const s = getComputedStyle(img);
  return {src: img.getAttribute('src'), dimensoes: (img.hasAttribute('width') && img.hasAttribute('height')) || s.aspectRatio !== 'auto',
          abaixo: r.top + window.scrollY >= window.innerHeight, lazy: img.getAttribute('loading') === 'lazy'};
})
"""


def verificar_navegador(pasta: Path, desvios: dict, tem_movimento: bool, css_total: str) -> dict:
    from playwright.sync_api import sync_playwright

    from servir import iniciar_servidor

    servidor, base, entrada = iniciar_servidor(pasta, replay=False)
    externos_permitidos = nomes(desvios, "externo")
    criterios = {}
    try:
        with sync_playwright() as p:
            nav = abrir_navegador(p, offline=True)
            ctx = nav.new_context(viewport={"width": 1440, "height": 900})
            page = ctx.new_page()
            erros, externas = [], []
            page.on("console", lambda m: erros.append(m.text[:200]) if m.type == "error" else None)
            page.on("pageerror", lambda e: erros.append(str(e)[:200]))

            def ao_pedir(req):
                u = req.url
                if u.startswith(("http://", "https://")) and not u.startswith(base) and not any(u.startswith(x) for x in externos_permitidos):
                    externas.append(u)

            page.on("request", ao_pedir)
            page.goto(entrada, wait_until="load", timeout=60000)
            esperar_rede(page)
            page.wait_for_timeout(1200)
            imagens = page.evaluate(JS_IMAGENS)
            erros_reais = [e for e in erros if not any(x in e for x in externos_permitidos)]
            criterios["B6"] = {"aprovado": not erros_reais, "erros": erros_reais[:10]}
            criterios["B7"] = {"aprovado": not externas, "requisicoes_externas": sorted(set(externas))[:20]}

            # B8
            transbordos = {}
            for largura in LARGURAS:
                page.set_viewport_size({"width": largura, "height": 900})
                page.wait_for_timeout(500)
                w = page.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
                if w[0] > w[1]:
                    transbordos[largura] = w[0] - w[1]
            criterios["B8"] = {"aprovado": not transbordos, "transbordo_px": transbordos}
            page.set_viewport_size({"width": 1440, "height": 900})
            page.wait_for_timeout(400)

            # B10
            # rola para revelar elementos com entrada animada antes de medir contraste
            page.evaluate("async () => { for (let y = 0; y < document.body.scrollHeight; y += 500) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 120)); } window.scrollTo(0, 0); }")
            page.wait_for_timeout(1500)
            a11y = page.evaluate(JS_A11Y)
            aprovados = nomes(desvios, "contraste")
            contraste = [c for c in a11y["contraste"] if c["seletor"] not in aprovados]
            reduzido = (not tem_movimento) or "prefers-reduced-motion" in css_total
            sem_foco = []
            antes = page.evaluate(JS_FOCAVEIS)
            for _ in range(min(len(antes), 60)):
                page.keyboard.press("Tab")
                atual = page.evaluate(JS_FOCO_ATUAL)
                if atual and atual["assinatura"] == antes[atual["i"]]:
                    sem_foco.append(f"{atual['tag']}: {atual['texto']}")
            sem_foco = sorted(set(sem_foco) - nomes(desvios, "foco"))
            criterios["B10"] = {
                "aprovado": not contraste and not a11y["semAlt"] and not a11y["semNome"] and not a11y["semRotulo"] and reduzido and not sem_foco,
                "contraste_insuficiente": contraste[:15], "verificar_manualmente": a11y["manual"], "img_sem_alt": a11y["semAlt"],
                "sem_nome_acessivel": a11y["semNome"], "campos_sem_rotulo": a11y["semRotulo"],
                "prefers_reduced_motion": reduzido, "sem_foco_visivel": sem_foco[:15]}

            criterios["_imagens"] = imagens
            ctx.close()
            nav.close()
    finally:
        servidor.shutdown()
        servidor.server_close()
    return criterios


# ---------------------------------------------------------------------------


def verificar(pasta: Path, pastas_ds: list[Path] | None = None, log=print) -> dict:
    pasta = Path(pasta).resolve()
    plano = ler_plano(pasta)
    desvios = ler_desvios(pasta)
    if not pastas_ds:
        pastas_ds = [(pasta / d).resolve() if not Path(d).is_absolute() else Path(d) for d in plano["ds"]]
    manifestos = [m for m in (ler_json(Path(d) / "manifesto-ds.json") for d in pastas_ds) if m]
    criterios, extras = verificar_estatico(pasta, manifestos, plano, desvios)
    criterios.update(verificar_navegador(pasta, desvios, extras["tem_movimento"], extras["css_total"]))

    imagens = criterios.pop("_imagens")
    sem_dimensao = [i["src"] for i in imagens if not i["dimensoes"]]
    sem_lazy = [i["src"] for i in imagens if i["abaixo"] and not i["lazy"]]
    criterios["B11"] = {"aprovado": not sem_dimensao and not sem_lazy and not extras["sem_uso"],
                        "sem_dimensoes": sem_dimensao, "sem_lazy_abaixo_da_dobra": sem_lazy,
                        "arquivos_sem_uso": extras["sem_uso"][:20], "peso_total_kb": round(extras["peso"] / 1024, 1)}
    criterios["B13"] = {"aprovado": plano["existe"] and (pasta / "DESVIOS.md").exists(),
                        "plano": plano["existe"], "desvios": (pasta / "DESVIOS.md").exists()}

    ordem = [f"B{i}" for i in range(1, 14)]
    criterios = {k: criterios[k] for k in ordem}
    aprovado = all(c["aprovado"] for c in criterios.values())
    linhas = ["# Relatório de verificação", "", f"Manifestos usados: {', '.join(str(d) for d in pastas_ds) or 'nenhum'}", "",
              "| Critério | Resultado | Detalhes |", "|---|---|---|"]
    for k, c in criterios.items():
        detalhe = json.dumps({x: y for x, y in c.items() if x != "aprovado" and y not in ([], {}, None, True, False)}, ensure_ascii=False)
        linhas.append(f"| {k} | {'aprovado' if c['aprovado'] else 'reprovado'} | {detalhe[:300].replace('|', '/')} |")
    linhas += ["", f"**Resultado geral:** {'APROVADO' if aprovado else 'REPROVADO'}", ""]
    (pasta / "relatorio-verificacao.md").write_text("\n".join(linhas), encoding="utf-8")
    for k, c in criterios.items():
        log(f"{k}: {'ok' if c['aprovado'] else 'FALHOU'}")
    return {"criterios": criterios, "aprovado": aprovado}


def main():
    parser = argparse.ArgumentParser(description="Verifica um site gerado (B1–B13).")
    parser.add_argument("pasta")
    parser.add_argument("--ds", action="append", help="pasta de referência com manifesto-ds.json (pode repetir)")
    args = parser.parse_args()
    r = verificar(Path(args.pasta), [Path(d).resolve() for d in args.ds] if args.ds else None)
    if not r["aprovado"]:
        for k, c in r["criterios"].items():
            if not c["aprovado"]:
                print(f"\n{k}: " + json.dumps({x: y for x, y in c.items() if x != "aprovado"}, ensure_ascii=False)[:900])
    print("\nAPROVADO" if r["aprovado"] else "\nREPROVADO")
    sys.exit(0 if r["aprovado"] else 1)


if __name__ == "__main__":
    main()
