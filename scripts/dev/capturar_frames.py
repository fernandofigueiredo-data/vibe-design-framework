#!/usr/bin/env python3
"""Reproduz a parte pública do critério D1: serve cada frame autoral em localhost,
captura com capturar.py e verifica com verificar_captura.py (K1–K5).

Uso:
    python scripts/dev/capturar_frames.py [nome-do-frame ...] [--destino examples/pipeline]
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "skills" / "extrair-design-system" / "scripts"))
import capturar  # noqa: E402
import verificar_captura  # noqa: E402
from servir import iniciar_servidor  # noqa: E402

FRAMES = RAIZ / "examples" / "frames"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("frames", nargs="*")
    parser.add_argument("--destino", default=str(RAIZ / "examples" / "pipeline"))
    parser.add_argument("--substituir", action="store_true", help="apaga a captura anterior do frame antes de capturar")
    args = parser.parse_args()
    nomes = args.frames or sorted(p.name for p in FRAMES.iterdir() if (p / "index.html").exists())
    resumo = {}
    for nome in nomes:
        destino = Path(args.destino) / nome
        if destino.exists():
            if not args.substituir:
                print(f"{destino} já existe (use --substituir)")
                continue
            shutil.rmtree(destino)
        servidor, base, _ = iniciar_servidor(FRAMES / nome, replay=False)
        try:
            print(f"== {nome}")
            capturar.capturar(base + "/index.html", destino)
            r = verificar_captura.verificar(destino, url_original=base + "/index.html")
            resumo[nome] = {k: v["aprovado"] for k, v in r["criterios"].items()}
        finally:
            servidor.shutdown()
            servidor.server_close()
    print(json.dumps(resumo, ensure_ascii=False, indent=2))
    sys.exit(0 if all(all(v is not False for v in c.values()) for c in resumo.values()) else 1)


if __name__ == "__main__":
    main()
