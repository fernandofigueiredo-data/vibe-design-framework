#!/usr/bin/env python3
"""Gera prints "da home" de uma pasta servida em localhost.

Uso:
    python scripts/dev/gerar_prints.py <pasta> <prefixo-de-saida> [--pagina index.html]
        [--tamanhos 1440x900,390x844] [--pagina-inteira]

Exemplo:
    python scripts/dev/gerar_prints.py examples/frames/atelie-claro docs/img/frame-atelie-claro
    → docs/img/frame-atelie-claro-1440x900.png e docs/img/frame-atelie-claro-390x844.png
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "skills" / "extrair-design-system" / "scripts"))
from servir import iniciar_servidor  # noqa: E402
from vd_comum import abrir_navegador, esperar_rede  # noqa: E402


def gerar(pasta: Path, prefixo: Path, pagina: str = "index.html", tamanhos=((1440, 900), (390, 844)),
          pagina_inteira: bool = False, espera_ms: int = 2600) -> list[Path]:
    from playwright.sync_api import sync_playwright

    servidor, base, entrada = iniciar_servidor(pasta, replay=None, entrada="/" + pagina)
    replay = entrada.endswith("/")
    saidas = []
    try:
        with sync_playwright() as p:
            nav = abrir_navegador(p, offline=True)
            for largura, altura in tamanhos:
                ctx = nav.new_context(viewport={"width": largura, "height": altura}, device_scale_factor=2)
                page = ctx.new_page()
                page.goto(entrada, wait_until="load")
                if replay:
                    page.wait_for_url("**/" + pagina, timeout=20000)
                esperar_rede(page)
                if pagina_inteira:
                    # rola para disparar revelações antes do print inteiro
                    page.evaluate("async () => { for (let y = 0; y < document.body.scrollHeight; y += 400) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 300)); } window.scrollTo(0, document.body.scrollHeight); await new Promise(r => setTimeout(r, 900)); window.scrollTo(0, 0); }")
                page.wait_for_timeout(espera_ms)
                destino = Path(f"{prefixo}-{largura}x{altura}.png")
                destino.parent.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(destino), full_page=pagina_inteira)
                saidas.append(destino)
                ctx.close()
            nav.close()
    finally:
        servidor.shutdown()
        servidor.server_close()
    return saidas


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pasta")
    parser.add_argument("prefixo")
    parser.add_argument("--pagina", default="index.html")
    parser.add_argument("--tamanhos", default="1440x900,390x844")
    parser.add_argument("--pagina-inteira", action="store_true")
    args = parser.parse_args()
    tamanhos = [tuple(int(v) for v in t.split("x")) for t in args.tamanhos.split(",")]
    for s in gerar(Path(args.pasta), Path(args.prefixo), args.pagina, tamanhos, args.pagina_inteira):
        print(s)


if __name__ == "__main__":
    main()
