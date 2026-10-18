#!/usr/bin/env python3
"""Verifica um design-system.html contra os critérios A1–A12.

A1  Nenhum arquivo que já existia foi alterado (hashes de .vd/hashes-antes.json).
A2  Nav no topo com âncora para cada seção; toda âncora aponta para um id existente.
A3  Seções na ordem hero, tipografia, cores, componentes, layout, movimento, icones;
    "icones" existe se e somente se a fonte tem ícones.
A4  O hero reproduz a árvore de tags e classes do hero original (só o texto muda).
A5  Classes do design system ⊆ classes da fonte (exceto classes ds-* de documentação,
    no máximo 15, definidas em assets/ds/css/ds-documentacao.css).
A6  Cores literais ⊆ cores da fonte.
A7  font-family e @keyframes ⊆ os da fonte.
A8  Uma linha por estilo tipográfico do manifesto, com rótulo "Npx / Npx" igual ao medido.
A9  Referências locais resolvem; sem duplicatas; sem <style>/<script> inline (exceto
    text/tailwindcss e JSON-LD); atributos style só se copiados da fonte; sem data-scroll-fix.
A10 STACK.md lista exatamente as bibliotecas do manifesto.
A11 lang="pt-BR" e nenhum texto visível (2+ palavras) igual ao da fonte, salvo termos do
    glossário (só quando a fonte não está em português).
A12 Textos traduzidos do hero com comprimento entre 0,8× e 1,3× o original; nenhum texto
    do hero transborda.

Uso:
    python verificar_ds.py <pasta> [--sem-render]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vd_comum import (  # noqa: E402
    ATRIBUTOS_COR_SVG,
    abrir_navegador,
    caminho_do_no,
    classes_de_css,
    cores_em,
    encontrar,
    encontrar_todos,
    escrever_json,
    esperar_rede,
    familias_de_declaracao,
    fontes_em_classes,
    fontes_em_css,
    hashes_da_pasta,
    idioma_do_documento,
    iter_nos,
    keyframes_em_css,
    ler_json,
    ler_texto,
    no_por_caminho,
    parse_html,
    referencias_do_html,
    resolver_local,
    eh_url_local,
    textos_visiveis,
    urls_de_css,
)

ORDEM = ["hero", "tipografia", "cores", "componentes", "layout", "movimento", "icones"]
MAX_CLASSES_DOC = 15
RAZAO_MIN, RAZAO_MAX = 0.8, 1.3
RE_ROTULO = re.compile(r"(\d+(?:\.\d+)?)px\s*/\s*(\d+(?:\.\d+)?)px")


def _resultado(aprovado: bool, **extra) -> dict:
    return {"aprovado": aprovado, **extra}


# ---------------------------------------------------------------------------
# Assinatura estrutural (A4)
# ---------------------------------------------------------------------------

IGNORAR_A4 = {"script", "style", "noscript", "template"}


def _eh_icone(no) -> bool:
    if no.tag in ("svg", "iconify-icon"):
        return True
    if no.tag == "i" and no.attr("data-lucide"):
        return True
    if no.tag == "img" and (no.attr("src") or "").startswith("assets/ds/svg/"):
        return True
    return False


def assinatura(no) -> tuple:
    if _eh_icone(no):
        return ("ícone",)
    filhos = tuple(assinatura(f) for f in no.elementos if f.tag not in IGNORAR_A4)
    return (no.tag, tuple(sorted(no.classes)), filhos)


def primeira_diferenca(a, b, caminho="hero") -> str | None:
    if a == b:
        return None
    if a[0] != b[0] or (len(a) > 1 and len(b) > 1 and a[1] != b[1]):
        return f"{caminho}: original {a[:2]} × design system {b[:2]}"
    if len(a) < 3 or len(b) < 3:
        return f"{caminho}: estrutura difere"
    if len(a[2]) != len(b[2]):
        return f"{caminho} <{a[0]}>: {len(a[2])} filhos no original, {len(b[2])} no design system"
    for i, (x, y) in enumerate(zip(a[2], b[2])):
        d = primeira_diferenca(x, y, f"{caminho} > {x[0]}[{i}]")
        if d:
            return d
    return None


# ---------------------------------------------------------------------------
# Verificação
# ---------------------------------------------------------------------------


def novos_css(pasta: Path) -> dict[str, str]:
    base = pasta / "assets" / "ds" / "css"
    return {p.relative_to(pasta).as_posix(): ler_texto(p) for p in sorted(base.glob("*.css"))} if base.exists() else {}


def verificar(pasta: Path, renderizar: bool = True, log=print) -> dict:
    pasta = Path(pasta).resolve()
    ds_caminho = pasta / "design-system.html"
    manifesto = ler_json(pasta / "manifesto-ds.json")
    if not ds_caminho.exists() or manifesto is None:
        raise FileNotFoundError("design-system.html e manifesto-ds.json são necessários")
    ds_html = ler_texto(ds_caminho)
    ds = parse_html(ds_html)
    pagina_fonte = manifesto.get("pagina_analisada", "index.html")
    fonte = parse_html(ler_texto(pasta / pagina_fonte))
    css_novos = novos_css(pasta)
    css_novos_texto = "\n".join(css_novos.values())
    criterios = {}

    # A1 -------------------------------------------------------------------
    antes = ler_json(pasta / ".vd" / "hashes-antes.json", {}) or {}
    agora = hashes_da_pasta(pasta)
    alterados = [k for k, v in antes.items() if agora.get(k) != v]
    criterios["A1"] = _resultado(bool(antes) and not alterados, alterados=alterados[:20],
                                 **({"detalhe": ".vd/hashes-antes.json ausente"} if not antes else {}))

    # A2 / A3 ----------------------------------------------------------------
    secoes = [n for n in iter_nos(ds) if n.tag == "section" and n.tem_attr("data-vd-secao")]
    ids = [n.attr("id") or "" for n in secoes]
    nav = encontrar(encontrar(ds, "body") or ds, "nav")
    ancoras = [(a.attr("href") or "")[1:] for a in encontrar_todos(nav, "a")] if nav else []
    ids_todos = {n.attr("id") for n in iter_nos(ds) if n.attr("id")}
    sem_ancora = [i for i in ids if i not in ancoras]
    quebradas = [a for a in ancoras if a not in ids_todos]
    criterios["A2"] = _resultado(nav is not None and not sem_ancora and not quebradas and bool(ancoras),
                                 sem_ancora=sem_ancora, ancoras_quebradas=quebradas)

    tem_icones = manifesto.get("total_icones", 0) > 0
    esperado = [s for s in ORDEM if s != "icones" or tem_icones]
    criterios["A3"] = _resultado(ids == esperado, encontrado=ids, esperado=esperado)

    # A4 ---------------------------------------------------------------------
    hero_ds = next((n for n in secoes if n.attr("id") == "hero"), None)
    hero_fonte = no_por_caminho(fonte, manifesto["hero"]["seletor"]) if manifesto.get("hero") else None
    if hero_ds is None or hero_fonte is None:
        criterios["A4"] = _resultado(False, detalhe="hero ausente no design system ou não localizado na fonte")
    else:
        filhos = [f for f in hero_ds.elementos if f.tag not in IGNORAR_A4]
        if len(filhos) != 1:
            criterios["A4"] = _resultado(False, detalhe=f"section#hero deve ter um único filho (o clone); tem {len(filhos)}")
        else:
            diff = primeira_diferenca(assinatura(hero_fonte), assinatura(filhos[0]))
            criterios["A4"] = _resultado(diff is None, diferenca=diff)

    # A5 ---------------------------------------------------------------------
    classes_fonte = set(manifesto["classes"])
    classes_ds = set()
    for n in iter_nos(ds):
        classes_ds |= set(n.classes)
    doc_css = (pasta / "assets" / "ds" / "css" / "ds-documentacao.css")
    classes_doc_definidas = classes_de_css(ler_texto(doc_css)) if doc_css.exists() else set()
    classes_doc = {c for c in classes_ds - classes_fonte if c.startswith("ds-")}
    doc_sem_definicao = sorted(c for c in classes_doc if c not in classes_doc_definidas)
    inventadas = sorted(c for c in classes_ds - classes_fonte if not c.startswith("ds-"))
    criterios["A5"] = _resultado(not inventadas and not doc_sem_definicao and len(classes_doc) <= MAX_CLASSES_DOC,
                                 inventadas=inventadas[:30], classes_documentacao=sorted(classes_doc),
                                 documentacao_sem_definicao=doc_sem_definicao)

    # A6 ---------------------------------------------------------------------
    texto_cores = css_novos_texto + "\n" + " ".join(classes_ds)
    for n in iter_nos(ds):
        for k, v in n.attrs:
            if v and (k == "style" or k in ATRIBUTOS_COR_SVG):
                texto_cores += f"\n{v}"
        if n.tag == "style":
            texto_cores += "\n" + n.texto_bruto()
    cores_fonte = set(manifesto["cores"])
    cores_novas = sorted(c for c in cores_em(texto_cores) if c not in cores_fonte)
    criterios["A6"] = _resultado(not cores_novas, cores_fora_da_fonte=cores_novas[:20])

    # A7 ---------------------------------------------------------------------
    fontes_ds = fontes_em_css(css_novos_texto) | fontes_em_classes(classes_ds)
    for n in iter_nos(ds):
        estilo = n.attr("style") or ""
        for m in re.finditer(r"font-family\s*:\s*([^;]+)", estilo):
            fontes_ds |= familias_de_declaracao(m.group(1))
        if n.attr("font-family"):
            fontes_ds |= familias_de_declaracao(n.attr("font-family"))
        if n.tag == "style":
            fontes_ds |= fontes_em_css(n.texto_bruto())
    fontes_fonte = set(manifesto["fontes"])
    fontes_novas = sorted(f for f in fontes_ds if f not in fontes_fonte)
    kf_novos = sorted(k for k in keyframes_em_css(css_novos_texto) if k not in set(manifesto["keyframes"]))
    criterios["A7"] = _resultado(not fontes_novas and not kf_novos, fontes_fora_da_fonte=fontes_novas, keyframes_fora_da_fonte=kf_novos)

    # A8 ---------------------------------------------------------------------
    estilos = {e["estilo"]: e for e in manifesto.get("tipografia", [])}
    linhas = [n for n in iter_nos(ds) if n.attr("data-vd-estilo")]
    problemas = []
    vistos = set()
    for linha in linhas:
        nome = linha.attr("data-vd-estilo")
        vistos.add(nome)
        if nome not in estilos:
            problemas.append(f"{nome}: estilo não existe no manifesto")
            continue
        trechos = [" ".join(t.split()) for n in [linha] + list(iter_nos(linha)) for t in n.filhos if isinstance(t, str)]
        m = next((RE_ROTULO.search(t) for t in trechos if RE_ROTULO.search(t)), None)
        esperado_rotulo = f"{estilos[nome]['tamanho']} / {estilos[nome]['entrelinha']}"
        if not m:
            problemas.append(f"{nome}: sem rótulo Npx / Npx (esperado {esperado_rotulo})")
        elif f"{m.group(1)}px / {m.group(2)}px" != esperado_rotulo:
            problemas.append(f"{nome}: rótulo {m.group(0)} difere do medido {esperado_rotulo}")
    faltando = [e for e in estilos if e not in vistos]
    criterios["A8"] = _resultado(bool(estilos) and not problemas and not faltando and len(linhas) == len(estilos),
                                 problemas=problemas, estilos_faltando=faltando)

    # A9 ---------------------------------------------------------------------
    quebradas, vistas, duplicadas = [], set(), []
    for n, attr, url in referencias_do_html(ds):
        if not eh_url_local(url):
            continue
        alvo = resolver_local(pasta, url)
        if alvo is None or not alvo.exists():
            quebradas.append(url)
        if attr in ("src", "href") and n.tag in ("script", "link"):
            if url in vistas:
                duplicadas.append(url)
            vistas.add(url)
    for caminho_css, texto in css_novos.items():
        for url in urls_de_css(texto):
            if eh_url_local(url):
                alvo = resolver_local((pasta / caminho_css).parent, url)
                if alvo is None or not alvo.exists():
                    quebradas.append(f"{caminho_css}: {url}")
    inline_proibido = []
    for n in iter_nos(ds):
        if n.tag == "style" and (n.attr("type") or "").lower() != "text/tailwindcss":
            inline_proibido.append("<style>")
        if n.tag == "script" and not n.attr("src") and n.texto_bruto().strip() and (n.attr("type") or "").lower() != "application/ld+json":
            inline_proibido.append("<script> inline")
    estilos_fonte = {v for n in iter_nos(fonte) for k, v in n.attrs if k == "style" and v}
    renderizado = pasta / "renderizado.html"
    if renderizado.exists():
        estilos_fonte |= {v for n in iter_nos(parse_html(ler_texto(renderizado))) for k, v in n.attrs if k == "style" and v}
    estilos_inventados = sorted({v for n in iter_nos(ds) for k, v in n.attrs if k == "style" and v and v not in estilos_fonte})
    criterios["A9"] = _resultado(not quebradas and not duplicadas and not inline_proibido and not estilos_inventados
                                 and "data-scroll-fix" not in ds_html,
                                 referencias_quebradas=quebradas[:20], duplicadas=duplicadas, inline=inline_proibido[:10],
                                 atributos_style_fora_da_fonte=estilos_inventados[:10])

    # A10 --------------------------------------------------------------------
    stack = pasta / "STACK.md"
    nomes_stack = set()
    sem_descricao = []
    if stack.exists():
        for linha in ler_texto(stack).splitlines():
            m = re.match(r"\s*[-*]\s+\*\*(.+?)\*\*\s*[—–-]\s*(.*)", linha)
            if m:
                nomes_stack.add(m.group(1).strip().lower())
                if not m.group(2).strip():
                    sem_descricao.append(m.group(1))
    nomes_manifesto = {b["nome"].lower() for b in manifesto.get("bibliotecas", [])}
    criterios["A10"] = _resultado(stack.exists() and nomes_stack == nomes_manifesto and not sem_descricao,
                                  faltando=sorted(nomes_manifesto - nomes_stack), a_mais=sorted(nomes_stack - nomes_manifesto),
                                  sem_descricao=sem_descricao)

    # A11 --------------------------------------------------------------------
    lang = idioma_do_documento(ds)
    fonte_em_pt = (manifesto.get("idioma_fonte") or "").startswith("pt")
    glossario = [t.lower() for t in (ler_json(pasta / "glossario.json", {}) or {}).get("termos", [])]
    nao_traduzidos = []
    if not fonte_em_pt:
        textos_fonte = set(textos_visiveis(fonte, 2))
        if renderizado.exists():
            textos_fonte |= set(textos_visiveis(parse_html(ler_texto(renderizado)), 2))
        for t in textos_visiveis(ds, 2):
            if t not in textos_fonte:
                continue
            resto = t.lower()
            for termo in sorted(glossario, key=len, reverse=True):
                resto = resto.replace(termo, " ")
            if len([p for p in re.split(r"\W+", resto) if p]) >= 2:
                nao_traduzidos.append(t)
    criterios["A11"] = _resultado(lang == "pt-br" and not nao_traduzidos, lang=lang, fonte_em_portugues=fonte_em_pt,
                                  nao_traduzidos=nao_traduzidos[:15])

    # A12 --------------------------------------------------------------------
    traducao = ler_json(pasta / "traducao.json", []) or []
    fora_da_faixa = []
    if not fonte_em_pt:
        for item in traducao:
            if item.get("onde") != "hero":
                continue
            origem, destino = item.get("origem", ""), item.get("traducao", "")
            if origem and destino:
                razao = len(destino) / len(origem)
                if not (RAZAO_MIN <= razao <= RAZAO_MAX):
                    fora_da_faixa.append({"origem": origem[:60], "traducao": destino[:60], "razao": round(razao, 2)})
    transbordos = None
    if renderizar:
        transbordos = medir_transbordo(pasta)
    criterios["A12"] = _resultado(not fora_da_faixa and not transbordos,
                                  fora_da_faixa=fora_da_faixa, transbordos=transbordos,
                                  **({"detalhe": "transbordo não medido (--sem-render)"} if transbordos is None else {}))

    resultado = {"pasta": str(pasta), "criterios": criterios, "aprovado": all(c["aprovado"] for c in criterios.values())}
    for k, c in criterios.items():
        log(f"{k}: {'ok' if c['aprovado'] else 'FALHOU'}")
    escrever_json(pasta / ".vd" / "verificacao-ds.json", resultado)
    return resultado


JS_TRANSBORDO = r"""
() => {
  const hero = document.getElementById('hero');
  if (!hero) return ['#hero ausente'];
  const saida = [];
  for (const e of hero.querySelectorAll('*')) {
    if (e.closest('svg')) continue;
    const temTexto = Array.from(e.childNodes).some(n => n.nodeType === 3 && n.textContent.trim());
    if (!temTexto) continue;
    const s = getComputedStyle(e);
    if (s.overflow === 'visible' && s.textOverflow !== 'ellipsis' && e.scrollWidth > e.clientWidth + 1 && e.clientWidth > 0)
      saida.push(e.tagName.toLowerCase() + ': ' + e.textContent.trim().slice(0, 40));
  }
  return saida;
}
"""


def medir_transbordo(pasta: Path) -> list[str]:
    from playwright.sync_api import sync_playwright

    from servir import iniciar_servidor

    replay = (pasta / "captura.json").exists()
    servidor, _, entrada = iniciar_servidor(pasta, replay=replay, entrada="/design-system.html")
    try:
        with sync_playwright() as p:
            nav = abrir_navegador(p, offline=True)
            page = nav.new_page(viewport={"width": 1440, "height": 900})
            page.goto(entrada, wait_until="load", timeout=60000)
            if replay:
                page.wait_for_url(re.compile(r"design-system\.html"), timeout=20000)
            esperar_rede(page)
            page.wait_for_timeout(1500)
            saida = page.evaluate(JS_TRANSBORDO)
            nav.close()
    finally:
        servidor.shutdown()
        servidor.server_close()
    return saida


def main():
    parser = argparse.ArgumentParser(description="Verifica design-system.html (A1–A12).")
    parser.add_argument("pasta")
    parser.add_argument("--sem-render", action="store_true")
    args = parser.parse_args()
    r = verificar(Path(args.pasta), renderizar=not args.sem_render)
    if not r["aprovado"]:
        import json
        for k, c in r["criterios"].items():
            if not c["aprovado"]:
                print(f"\n{k}: " + json.dumps({x: y for x, y in c.items() if x != "aprovado"}, ensure_ascii=False)[:800])
    print("\nAPROVADO" if r["aprovado"] else "\nREPROVADO")
    sys.exit(0 if r["aprovado"] else 1)


if __name__ == "__main__":
    main()
