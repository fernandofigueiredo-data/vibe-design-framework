#!/usr/bin/env python3
"""Etapa 1 da extração: registra o estado inicial da pasta e prepara a cópia de análise.

- Grava .vd/hashes-antes.json com o hash de todos os arquivos existentes (base do critério A1).
- Se o index.html tiver injeções de ferramentas de captura antigas (ex.: <style data-scroll-fix>),
  gera vd-analise.html sem elas. O index.html nunca é alterado.

Uso:
    python sanitizar.py <pasta>
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vd_comum import escrever_json, hashes_da_pasta, ler_json, ler_texto  # noqa: E402

# Blocos injetados por ferramentas de captura que alteram o visual original
INJECOES = [
    ("style data-scroll-fix", re.compile(r"<style\b[^>]*\bdata-scroll-fix\b[^>]*>.*?</style\s*>", re.S | re.I)),
]

ARQUIVOS_GERADOS = ("design-system.html", "STACK.md", "manifesto-ds.json", "glossario.json", "traducao.json",
                    "relatorio-extracao.md", "vd-analise.html")


def registrar_hashes_antes(pasta: Path) -> dict:
    caminho = pasta / ".vd" / "hashes-antes.json"
    existente = ler_json(caminho)
    if existente:
        return existente
    hashes = {k: v for k, v in hashes_da_pasta(pasta).items()
              if k not in ARQUIVOS_GERADOS and not k.startswith("assets/ds/")}
    escrever_json(caminho, hashes)
    return hashes


def sanitizar(pasta: Path) -> dict:
    pasta = Path(pasta).resolve()
    index = pasta / "index.html"
    if not index.exists():
        raise FileNotFoundError(f"{index} não encontrado")
    hashes = registrar_hashes_antes(pasta)
    texto = ler_texto(index)
    removidos = []
    for nome, padrao in INJECOES:
        texto, n = padrao.subn("", texto)
        if n:
            removidos.append({"injecao": nome, "ocorrencias": n})
    relatorio = {"arquivos_registrados": len(hashes), "injecoes_removidas": removidos,
                 "copia_de_analise": "vd-analise.html" if removidos else None}
    if removidos:
        (pasta / "vd-analise.html").write_text(texto, encoding="utf-8")
    escrever_json(pasta / ".vd" / "sanitizacao.json", relatorio)
    return relatorio


def main():
    parser = argparse.ArgumentParser(description="Registra o estado inicial e remove injeções de captura numa cópia.")
    parser.add_argument("pasta")
    args = parser.parse_args()
    r = sanitizar(Path(args.pasta))
    print(f"{r['arquivos_registrados']} arquivos registrados em .vd/hashes-antes.json")
    if r["injecoes_removidas"]:
        for i in r["injecoes_removidas"]:
            print(f"removido na cópia de análise: {i['injecao']} ({i['ocorrencias']}x) → vd-analise.html")
    else:
        print("nenhuma injeção encontrada")


if __name__ == "__main__":
    main()
