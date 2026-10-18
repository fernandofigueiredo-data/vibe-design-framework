#!/usr/bin/env python3
"""Confere a originalidade do repositório (parte do critério D5).

- Sequências de N ou mais palavras idênticas a textos de origem (--contra).
- Termos que não podem aparecer no repositório (--proibir), sem diferenciar maiúsculas.
- Regras CSS não triviais idênticas às de uma pasta de referências (--css-contra),
  comparadas apenas com os frames autorais.

Uso:
    python scripts/dev/verificar_originalidade.py --contra fonte1.txt fonte2.md \
        [--proibir termo ...] [--css-contra pasta] [--n 12]
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
EXTENSOES = {".md", ".html", ".css", ".js", ".py", ".json", ".txt", ".svg"}
IGNORAR_DIRS = {".git", ".venv", "__pycache__", "referencias", "sites", "THIRD_PARTY_LICENSES", "validacao"}
IGNORAR_ARQUIVOS = {"tailwind-browser.js", "lucide.min.js"}  # bibliotecas de terceiros empacotadas


def arquivos_do_repo():
    for raiz, dirs, nomes in os.walk(RAIZ):
        dirs[:] = [d for d in dirs if d not in IGNORAR_DIRS]
        for nome in nomes:
            caminho = Path(raiz) / nome
            if caminho.suffix.lower() in EXTENSOES and nome not in IGNORAR_ARQUIVOS:
                yield caminho


def palavras(texto: str) -> list[str]:
    texto = re.sub(r"<[^>]+>", " ", texto)
    return re.findall(r"[a-zà-ÿ0-9]+", texto.lower())


def ngramas(lista: list[str], n: int) -> set[tuple]:
    return {tuple(lista[i:i + n]) for i in range(len(lista) - n + 1)}


def regras_css(texto: str) -> set[str]:
    texto = re.sub(r"/\*.*?\*/", "", texto, flags=re.S)
    regras = set()
    for m in re.finditer(r"\{([^{}]+)\}", texto):
        decls = sorted(d.strip().lower() for d in m.group(1).split(";") if ":" in d)
        if len(decls) >= 3:
            regras.add("; ".join(re.sub(r"\s+", " ", d) for d in decls))
    return regras


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--contra", nargs="*", default=[], help="textos de origem que não podem ser reproduzidos")
    parser.add_argument("--proibir", nargs="*", default=[], help="termos que não podem aparecer no repositório")
    parser.add_argument("--css-contra", help="pasta de referências para comparar o CSS dos frames")
    parser.add_argument("--n", type=int, default=12)
    args = parser.parse_args()
    problemas = 0

    fontes = {}
    for c in args.contra:
        fontes[c] = ngramas(palavras(Path(c).read_text(encoding="utf-8", errors="replace")), args.n)
    for caminho in arquivos_do_repo():
        texto = caminho.read_text(encoding="utf-8", errors="replace")
        rel = caminho.relative_to(RAIZ)
        for termo in args.proibir:
            if termo.lower() in texto.lower():
                print(f"[termo proibido] {rel}: '{termo}'")
                problemas += 1
        if fontes:
            meus = ngramas(palavras(texto), args.n)
            for nome, conjunto in fontes.items():
                comuns = meus & conjunto
                if comuns:
                    exemplo = " ".join(next(iter(comuns)))
                    print(f"[{len(comuns)} sequência(s) de {args.n}+ palavras] {rel} × {Path(nome).name}: “{exemplo}”")
                    problemas += 1

    if args.css_contra:
        banco = set()
        for raiz, _, nomes in os.walk(args.css_contra):
            for nome in nomes:
                if nome.endswith((".css", ".html")):
                    banco |= regras_css(Path(raiz, nome).read_text(encoding="utf-8", errors="replace"))
        for caminho in (RAIZ / "examples" / "frames").rglob("*"):
            if caminho.suffix in (".css", ".html") and caminho.name not in IGNORAR_ARQUIVOS:
                comuns = regras_css(caminho.read_text(encoding="utf-8")) & banco
                for r in comuns:
                    print(f"[regra CSS idêntica ao banco] {caminho.relative_to(RAIZ)}: {r[:100]}")
                    problemas += 1

    print("OK: nenhuma ocorrência" if not problemas else f"{problemas} ocorrência(s)")
    sys.exit(0 if not problemas else 1)


if __name__ == "__main__":
    main()
