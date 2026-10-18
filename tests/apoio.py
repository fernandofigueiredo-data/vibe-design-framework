"""Apoio aos testes: servidores locais e caminhos."""

from __future__ import annotations

import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SCRIPTS_A = RAIZ / "skills" / "extrair-design-system" / "scripts"
SCRIPTS_B = RAIZ / "skills" / "criar-site" / "scripts"
FIXTURES = RAIZ / "tests" / "fixtures"
for p in (SCRIPTS_A, SCRIPTS_B):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


class _Modelo(SimpleHTTPRequestHandler):
    """Serve arquivos trocando {{CDN}} pela URL do servidor de CDN e index.template.html por index.html."""

    def __init__(self, *a, trocas=None, **k):
        self.trocas = trocas or {}
        super().__init__(*a, **k)

    def log_message(self, *a):
        pass

    def do_GET(self):
        caminho = self.path.split("?")[0]
        if caminho in ("/", "/index.html"):
            caminho = "/index.template.html"
        arquivo = Path(self.directory) / caminho.lstrip("/")
        if not arquivo.is_file():
            self.send_error(404)
            return
        dados = arquivo.read_bytes()
        if arquivo.suffix in {".html", ".css", ".js", ".json", ".svg"}:
            texto = dados.decode("utf-8")
            for k, v in self.trocas.items():
                texto = texto.replace(k, v)
            dados = texto.encode("utf-8")
        tipo = self.guess_type(str(arquivo).replace(".template.html", ".html"))
        self.send_response(200)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(dados)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(dados)


def servir_modelo(pasta: Path, trocas: dict | None = None):
    trocas = trocas if trocas is not None else {}
    servidor = ThreadingHTTPServer(("127.0.0.1", 0), partial(_Modelo, directory=str(pasta), trocas=trocas))
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    return servidor, f"http://127.0.0.1:{servidor.server_address[1]}"
