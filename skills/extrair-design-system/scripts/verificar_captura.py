#!/usr/bin/env python3
"""Verifica uma captura contra os critérios K1–K5.

K1  Offline: servida em localhost com a rede bloqueada, nenhuma requisição falha
    além das listadas como omitidas em captura.json.
K2  Fidelidade visual: prints em 5 posições de rolagem; diferença de pixels
    abaixo do limite, ignorando <canvas> e <video>. Requer acesso ao original.
K3  Estilos calculados: font-family, font-size, color e background-color de
    elementos amostrados coincidem com o original. Requer acesso ao original.
K4  Sem injeções: comparado a origem.html, index.html não tem elemento novo nem
    atributo novo além de data-vd-*.
K5  Extensões coerentes com o content-type (nenhum .es, nenhum .html espúrio).

Uso:
    python verificar_captura.py <pasta> [--sem-original] [--url-original URL]
                                [--limite-pixels 0.02] [--limite-estilos 0.95]
Gera <pasta>/.vd/verificacao-captura.json e devolve código 0 (aprovado) ou 1.
"""

from __future__ import annotations

import argparse
import base64
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from capturar import escolher_frame  # noqa: E402
from servir import iniciar_servidor  # noqa: E402
from vd_comum import (  # noqa: E402
    EXTENSAO_POR_TIPO,
    abrir_navegador,
    escrever_json,
    esperar_rede,
    ler_json,
    ler_texto,
    tipo_base,
)

POSICOES = [0.0, 0.25, 0.5, 0.75, 1.0]
ESPERA_MS = 1800

JS_AMOSTRA = r"""
(n) => {
  const todos = Array.from(document.body.querySelectorAll('*')).filter(e => {
    const r = e.getBoundingClientRect();
    if (r.width < 4 || r.height < 4) return false;
    const t = e.tagName.toLowerCase();
    return !['script','style','svg','path','canvas','video','iframe','noscript','br'].includes(t);
  });
  const passo = Math.max(1, Math.floor(todos.length / n));
  const caminho = (e) => {
    const partes = [];
    while (e && e !== document.body) {
      const pai = e.parentElement;
      const irmaos = Array.from(pai.children).filter(x => x.tagName === e.tagName);
      partes.unshift(e.tagName.toLowerCase() + ':nth-of-type(' + (irmaos.indexOf(e) + 1) + ')');
      e = pai;
    }
    return 'body > ' + partes.join(' > ');
  };
  const saida = [];
  for (let i = 0; i < todos.length && saida.length < n; i += passo) {
    const e = todos[i], s = getComputedStyle(e);
    saida.push({seletor: caminho(e), fonte: s.fontFamily, tamanho: s.fontSize, cor: s.color, fundo: s.backgroundColor});
  }
  return saida;
}
"""

JS_ESTILOS_DE = r"""
(seletores) => seletores.map(sel => {
  const e = document.querySelector(sel);
  if (!e) return null;
  const s = getComputedStyle(e);
  return {fonte: s.fontFamily, tamanho: s.fontSize, cor: s.color, fundo: s.backgroundColor};
})
"""

JS_MASCARAS = r"""
() => Array.from(document.querySelectorAll('canvas, video, iframe')).map(e => {
  const r = e.getBoundingClientRect();
  return [r.left, r.top, r.width, r.height];
}).filter(r => r[2] > 0 && r[3] > 0)
"""

JS_DIFERENCA = r"""
async ([a, b, mascaras, limiar]) => {
  const carregar = (src) => new Promise((ok, erro) => { const i = new Image(); i.onload = () => ok(i); i.onerror = erro; i.src = src; });
  const [ia, ib] = await Promise.all([carregar(a), carregar(b)]);
  const w = Math.min(ia.width, ib.width), h = Math.min(ia.height, ib.height);
  const pixels = (img) => { const c = new OffscreenCanvas(w, h); const x = c.getContext('2d'); x.drawImage(img, 0, 0); return x.getImageData(0, 0, w, h).data; };
  const pa = pixels(ia), pb = pixels(ib);
  const ignorar = new Uint8Array(w * h);
  for (const [l, t, mw, mh] of mascaras) {
    for (let y = Math.max(0, Math.floor(t)); y < Math.min(h, Math.ceil(t + mh)); y++)
      for (let x = Math.max(0, Math.floor(l)); x < Math.min(w, Math.ceil(l + mw)); x++) ignorar[y * w + x] = 1;
  }
  const uniformidade = (px) => { let iguais = 0; for (let p = 0; p < w * h; p++) { const i = p * 4; if (Math.abs(px[i] - px[0]) < 8 && Math.abs(px[i+1] - px[1]) < 8 && Math.abs(px[i+2] - px[2]) < 8) iguais++; } return iguais / (w * h); };
  let diferentes = 0, considerados = 0;
  for (let p = 0; p < w * h; p++) {
    if (ignorar[p]) continue;
    considerados++;
    const i = p * 4;
    if (Math.abs(pa[i] - pb[i]) > limiar || Math.abs(pa[i+1] - pb[i+1]) > limiar || Math.abs(pa[i+2] - pb[i+2]) > limiar) diferentes++;
  }
  return {diferentes, considerados, proporcao: considerados ? diferentes / considerados : 0, uniforme_a: uniformidade(pa), uniforme_b: uniformidade(pb)};
}
"""


JS_ALTURA = "Math.max(document.documentElement.scrollHeight, document.body ? document.body.scrollHeight : 0)"


def _rolavel(alvo) -> int:
    return max(0, alvo.evaluate(JS_ALTURA) - alvo.evaluate("window.innerHeight"))


def _posicionar(alvo, fracao: float) -> None:
    alvo.evaluate("y => window.scrollTo(0, y)", int(_rolavel(alvo) * fracao))
    alvo.wait_for_timeout(ESPERA_MS)


def _rolar_para(alvo, y: int) -> None:
    alvo.evaluate("y => window.scrollTo(0, y)", y)
    alvo.wait_for_timeout(ESPERA_MS)


# ---------------------------------------------------------------------------
# K4: comparação estrutural origem × index
# ---------------------------------------------------------------------------

_RE_TAG = re.compile(r"""<([A-Za-z][\w:-]*)((?:"[^"]*"|'[^']*'|[^'">])*)>""")
_RE_ATTR = re.compile(r"""([^\s=/>"']+)(?:\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]+))?""")


def _assinatura(texto: str) -> list[tuple[str, frozenset]]:
    texto = re.sub(r"<!--.*?-->", "", texto, flags=re.S)
    texto = re.sub(r"(<(script|style)\b[^>]*>).*?(</\2\s*>)", r"\1\3", texto, flags=re.S | re.I)
    sinal = []
    for m in _RE_TAG.finditer(texto):
        nomes = frozenset(a.group(1).lower() for a in _RE_ATTR.finditer(m.group(2)) if a.group(1) != "/")
        sinal.append((m.group(1).lower(), nomes))
    return sinal


def k4(pasta: Path) -> dict:
    origem = pasta / "origem.html"
    if not origem.exists():
        return {"aprovado": False, "detalhe": "origem.html ausente"}
    a = _assinatura(ler_texto(origem))
    b = _assinatura(ler_texto(pasta / "index.html"))
    problemas = []
    if len(a) != len(b):
        problemas.append(f"número de tags difere: origem {len(a)}, captura {len(b)}")
    for i, (ta, tb) in enumerate(zip(a, b)):
        if ta[0] != tb[0]:
            problemas.append(f"tag {i}: {ta[0]} → {tb[0]}")
            break
        novos = {x for x in tb[1] - ta[1] if not x.startswith("data-vd-") and x != "type"}
        sumidos = {x for x in ta[1] - tb[1] if x != "integrity"}
        if novos or sumidos:
            problemas.append(f"<{ta[0]}> #{i}: novos={sorted(novos)} removidos={sorted(sumidos)}")
    if "data-scroll-fix" in ler_texto(pasta / "index.html"):
        problemas.append("bloco data-scroll-fix presente")
    return {"aprovado": not problemas, "problemas": problemas[:20]}


# ---------------------------------------------------------------------------
# K5: extensões
# ---------------------------------------------------------------------------


def k5(pasta: Path, captura: dict) -> dict:
    problemas = []
    for rec in captura.get("recursos", []):
        arquivo = rec["arquivo"]
        ext = Path(arquivo).suffix.lower()
        esperado = EXTENSAO_POR_TIPO.get(tipo_base(rec.get("tipo")))
        if ext == ".es":
            problemas.append(f"{arquivo}: extensão .es")
        elif ext == ".html" and tipo_base(rec.get("tipo")) != "text/html":
            problemas.append(f"{arquivo}: .html para {rec.get('tipo')}")
        elif esperado and esperado != ext:
            problemas.append(f"{arquivo}: esperado {esperado} para {rec.get('tipo')}")
        if not (pasta / arquivo).exists():
            problemas.append(f"{arquivo}: arquivo ausente")
    return {"aprovado": not problemas, "problemas": problemas[:30]}


# ---------------------------------------------------------------------------
# Verificação completa
# ---------------------------------------------------------------------------


def verificar(pasta: Path, url_original: str | None = None, sem_original: bool = False,
              limite_pixels: float = 0.02, limite_estilos: float = 0.95, log=print) -> dict:
    from playwright.sync_api import sync_playwright

    pasta = Path(pasta).resolve()
    captura = ler_json(pasta / "captura.json", {}) or {}
    viewport = captura.get("viewport") or {"largura": 1440, "altura": 900}
    tela = {"width": viewport["largura"], "height": viewport["altura"]}
    omitidos = {o["url"] for o in captura.get("omitidos", [])}
    url_original = url_original or captura.get("url_documento") or captura.get("url")
    resultado = {"pasta": str(pasta), "criterios": {}}

    servidor, base_local, entrada = iniciar_servidor(pasta)
    try:
        with sync_playwright() as p:
            # ---- K1 --------------------------------------------------------
            nav = abrir_navegador(p, offline=True)
            ctx = nav.new_context(viewport=tela, device_scale_factor=1)
            page = ctx.new_page()
            falhas = []

            def externa(u: str) -> bool:
                return not u.startswith(base_local) and u.startswith(("http://", "https://"))

            def ao_falhar(req):
                u = req.url.split("#")[0]
                if u not in omitidos and not u.endswith("/favicon.ico"):
                    falhas.append({"url": u, "erro": req.failure})

            def ao_responder(resp):
                u = resp.url.split("#")[0]
                if resp.status >= 400 and u not in omitidos and not u.endswith("/favicon.ico"):
                    falhas.append({"url": u, "erro": f"HTTP {resp.status}"})
                elif externa(u) and not resp.from_service_worker:
                    falhas.append({"url": u, "erro": "saiu para a rede (não veio da captura)"})

            page.on("requestfailed", ao_falhar)
            page.on("response", ao_responder)
            page.goto(entrada, wait_until="load", timeout=60000)
            page.wait_for_url(re.compile(r".*/index\.html.*"), timeout=20000) if entrada.endswith("/") else None
            esperar_rede(page)
            for f in POSICOES:
                _posicionar(page, f)
            esperar_rede(page)
            unicas = {f["url"]: f for f in falhas}
            resultado["criterios"]["K1"] = {
                "aprovado": not unicas,
                "falhas": list(unicas.values())[:30],
                "externas": sum(1 for u in unicas if externa(u)),
            }
            log(f"K1 offline: {'ok' if not unicas else f'{len(unicas)} falha(s)'}")

            page.evaluate("window.scrollTo(0,0)")
            page.wait_for_timeout(ESPERA_MS)
            amostra_captura_fn = page  # usada em K3

            # ---- K2/K3 (original online) ------------------------------------
            if sem_original or not url_original:
                resultado["criterios"]["K2"] = {"aprovado": None, "detalhe": "não verificado: sem acesso ao original"}
                resultado["criterios"]["K3"] = {"aprovado": None, "detalhe": "não verificado: sem acesso ao original"}
            else:
                nav_on = abrir_navegador(p)
                ctx_on = nav_on.new_context(viewport=tela, device_scale_factor=1, service_workers="block")
                orig = ctx_on.new_page()
                orig.goto(url_original, wait_until="load", timeout=60000)
                esperar_rede(orig)
                alvo_orig, _ = escolher_frame(orig)  # invólucro de construtor: o conteúdo está no iframe
                for f in POSICOES:
                    _posicionar(alvo_orig, f)
                alvo_orig.evaluate("window.scrollTo(0,0)")
                orig.wait_for_timeout(ESPERA_MS)

                # K3: amostra no original, compara na captura
                amostra = alvo_orig.evaluate(JS_AMOSTRA, 50)
                estilos = amostra_captura_fn.evaluate(JS_ESTILOS_DE, [a["seletor"] for a in amostra])
                iguais, divergentes = 0, []
                for a, b in zip(amostra, estilos):
                    alvo = {k: a[k] for k in ("fonte", "tamanho", "cor", "fundo")}
                    if b == alvo:
                        iguais += 1
                    else:
                        divergentes.append({"seletor": a["seletor"], "original": alvo, "captura": b})
                proporcao = iguais / len(amostra) if amostra else 1.0
                resultado["criterios"]["K3"] = {"aprovado": proporcao >= limite_estilos, "proporcao": round(proporcao, 3),
                                                "limite": limite_estilos, "divergentes": divergentes[:10]}
                log(f"K3 estilos: {proporcao:.0%} iguais")

                # K2: prints nas mesmas posições absolutas (calculadas no original)
                comparacoes, uniformes = [], []
                pagina_diff = ctx.new_page()
                pagina_diff.goto(base_local + "/__vd/mapa.json")
                rolavel_orig, rolavel_cap = _rolavel(alvo_orig), _rolavel(page)
                altura_orig, altura_cap = alvo_orig.evaluate(JS_ALTURA), page.evaluate(JS_ALTURA)
                pasta_prints = pasta / ".vd" / "prints"
                pasta_prints.mkdir(parents=True, exist_ok=True)
                for f in POSICOES:
                    y = int(rolavel_orig * f)
                    _rolar_para(alvo_orig, y)
                    _rolar_para(page, min(y, rolavel_cap))
                    print_orig, print_cap = orig.screenshot(), page.screenshot()
                    mascaras = alvo_orig.evaluate(JS_MASCARAS) + page.evaluate(JS_MASCARAS)
                    a = "data:image/png;base64," + base64.b64encode(print_orig).decode()
                    b = "data:image/png;base64," + base64.b64encode(print_cap).decode()
                    d = pagina_diff.evaluate(JS_DIFERENCA, [a, b, mascaras, 32])
                    comparacoes.append({"posicao": f, "y": y, "proporcao": round(d["proporcao"], 4)})
                    if max(d["uniforme_a"], d["uniforme_b"]) > 0.995:
                        uniformes.append(f)
                    (pasta_prints / f"original-{int(f*100):03d}.png").write_bytes(print_orig)
                    (pasta_prints / f"captura-{int(f*100):03d}.png").write_bytes(print_cap)
                pior = max(c["proporcao"] for c in comparacoes)
                todas_uniformes = len(uniformes) == len(POSICOES)
                resultado["criterios"]["K2"] = {"aprovado": pior <= limite_pixels and not todas_uniformes, "pior": pior,
                                                "limite": limite_pixels, "posicoes": comparacoes,
                                                "altura_original": altura_orig, "altura_captura": altura_cap,
                                                "prints_uniformes": uniformes,
                                                **({"detalhe": "todos os prints são uniformes: página em branco"} if todas_uniformes else {})}
                log(f"K2 visual: pior diferença {pior:.2%} (alturas: original {altura_orig}px, captura {altura_cap}px)")
                ctx_on.close()
                nav_on.close()
            ctx.close()
            nav.close()
    finally:
        servidor.shutdown()
        servidor.server_close()

    resultado["criterios"]["K4"] = k4(pasta)
    log(f"K4 sem injeções: {'ok' if resultado['criterios']['K4']['aprovado'] else 'falhou'}")
    resultado["criterios"]["K5"] = k5(pasta, captura)
    log(f"K5 extensões: {'ok' if resultado['criterios']['K5']['aprovado'] else 'falhou'}")
    avaliados = [c["aprovado"] for c in resultado["criterios"].values() if c["aprovado"] is not None]
    resultado["aprovado"] = all(avaliados)
    escrever_json(pasta / ".vd" / "verificacao-captura.json", resultado)
    return resultado


def main():
    parser = argparse.ArgumentParser(description="Verifica uma captura (K1–K5).")
    parser.add_argument("pasta")
    parser.add_argument("--url-original")
    parser.add_argument("--sem-original", action="store_true", help="pula K2 e K3 (não acessa o site original)")
    parser.add_argument("--limite-pixels", type=float, default=0.02)
    parser.add_argument("--limite-estilos", type=float, default=0.95)
    args = parser.parse_args()
    r = verificar(Path(args.pasta), args.url_original, args.sem_original, args.limite_pixels, args.limite_estilos)
    print("APROVADO" if r["aprovado"] else "REPROVADO")
    sys.exit(0 if r["aprovado"] else 1)


if __name__ == "__main__":
    main()
