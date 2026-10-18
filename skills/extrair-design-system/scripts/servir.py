#!/usr/bin/env python3
"""Serve uma pasta de referência (ou de site) em localhost, sem depender da internet.

Com replay ativo (padrão quando existe captura.json), um service worker responde
a qualquer requisição de outra origem a partir do mapa URL → arquivo da captura.
O que não está no mapa recebe 404: a página nunca sai para a rede.

Uso:
    python servir.py <pasta> [--porta 8765] [--sem-replay] [--permitir-rede]
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vd_comum import TIPO_POR_EXTENSAO, ler_json  # noqa: E402

SW_JS = r"""
const MAPA_URL = '/__vd/mapa.json';
let mapaPromise = null;
function carregarMapa() {
  if (!mapaPromise) mapaPromise = fetch(MAPA_URL, {cache: 'no-store'}).then(r => r.json());
  return mapaPromise;
}
self.addEventListener('install', e => { e.waitUntil(carregarMapa().then(() => self.skipWaiting())); });
self.addEventListener('activate', e => { e.waitUntil(self.clients.claim()); });
function procurar(mapa, href) {
  const u = new URL(href);
  u.hash = '';
  const exato = u.href;
  if (mapa.urls[exato]) return mapa.urls[exato];
  const semQuery = u.origin + u.pathname;
  if (mapa.urls[semQuery]) return mapa.urls[semQuery];
  if (mapa.sem_query[semQuery]) return mapa.sem_query[semQuery];
  return null;
}
self.addEventListener('fetch', e => {
  const u = new URL(e.request.url);
  if (u.origin === self.location.origin) return;
  if (!/^https?:$/.test(u.protocol)) return;
  e.respondWith((async () => {
    const mapa = await carregarMapa();
    const alvo = procurar(mapa, e.request.url);
    if (alvo) {
      const r = await fetch('/' + alvo);
      const h = new Headers();
      h.set('content-type', r.headers.get('content-type') || 'application/octet-stream');
      h.set('access-control-allow-origin', '*');
      h.set('x-vd-replay', '1');
      return new Response(r.body, {status: 200, headers: h});
    }
    if (mapa.permitir_rede) return fetch(e.request);
    return new Response('', {status: 404, statusText: 'vd: fora da captura', headers: {'access-control-allow-origin': '*', 'x-vd-replay': '404'}});
  })());
});
"""

PAGINA_INICIAL = """<!doctype html><html lang="pt-BR"><meta charset="utf-8"><title>Carregando captura…</title>
<body style="font:14px system-ui;padding:2rem">Preparando a reprodução offline…
<script>
(async () => {
  const destino = %s;
  if (!('serviceWorker' in navigator)) { location.replace(destino); return; }
  await navigator.serviceWorker.register('/__vd/sw.js', {scope: '/'});
  await navigator.serviceWorker.ready;
  if (!navigator.serviceWorker.controller) {
    await new Promise(r => navigator.serviceWorker.addEventListener('controllerchange', r, {once: true}));
  }
  location.replace(destino);
})();
</script></body></html>"""


def montar_mapa(pasta: Path, permitir_rede: bool = False) -> dict:
    captura = ler_json(pasta / "captura.json", {}) or {}
    urls: dict[str, str] = {}
    sem_query: dict[str, str] = {}
    for rec in captura.get("recursos", []):
        arquivo = rec.get("arquivo")
        if not arquivo:
            continue
        for chave in [rec.get("url")] + list(rec.get("aliases", [])):
            if not chave:
                continue
            chave = chave.split("#", 1)[0]
            urls[chave] = arquivo
            partes = urlsplit(chave)
            sem_query.setdefault(f"{partes.scheme}://{partes.netloc}{partes.path}", arquivo)
    return {"urls": urls, "sem_query": sem_query, "permitir_rede": permitir_rede}


class Servidor(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 256  # páginas modernas abrem dezenas de conexões de uma vez


class Manipulador(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map, **{k: v for k, v in TIPO_POR_EXTENSAO.items()}}

    def __init__(self, *args, config=None, **kwargs):
        self.config = config
        super().__init__(*args, **kwargs)

    def log_message(self, formato, *args):  # silencioso
        if self.config.get("verboso"):
            super().log_message(formato, *args)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _responder(self, corpo: bytes, tipo: str, extra: dict | None = None):
        self.send_response(200)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(corpo)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(corpo)

    def do_GET(self):
        caminho = urlsplit(self.path).path
        if caminho == "/__vd/sw.js":
            return self._responder(SW_JS.encode(), "text/javascript; charset=utf-8", {"Service-Worker-Allowed": "/"})
        if caminho == "/__vd/mapa.json":
            return self._responder(json.dumps(self.config["mapa"]).encode(), "application/json")
        if caminho == "/" and self.config["replay"]:
            destino = json.dumps(self.config["entrada"])
            return self._responder((PAGINA_INICIAL % destino).encode(), "text/html; charset=utf-8")
        return super().do_GET()

    do_HEAD = do_GET


def iniciar_servidor(pasta: Path, porta: int = 0, replay: bool | None = None, permitir_rede: bool = False,
                     entrada: str = "/index.html", verboso: bool = False):
    """Sobe o servidor numa thread. Devolve (servidor, url_base, url_de_entrada)."""
    pasta = Path(pasta).resolve()
    if replay is None:
        replay = (pasta / "captura.json").exists()
    config = {
        "replay": replay,
        "mapa": montar_mapa(pasta, permitir_rede),
        "entrada": entrada,
        "verboso": verboso,
    }
    manipulador = partial(Manipulador, directory=str(pasta), config=config)
    servidor = Servidor(("127.0.0.1", porta), manipulador)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{servidor.server_address[1]}"
    return servidor, base, base + ("/" if replay else entrada)


def main():
    parser = argparse.ArgumentParser(description="Serve uma pasta em localhost com replay offline.")
    parser.add_argument("pasta")
    parser.add_argument("--porta", type=int, default=8765)
    parser.add_argument("--sem-replay", action="store_true", help="não registra o service worker de replay")
    parser.add_argument("--permitir-rede", action="store_true", help="deixa passar o que não está na captura")
    args = parser.parse_args()
    pasta = Path(args.pasta)
    if not (pasta / "index.html").exists():
        sys.exit(f"erro: {pasta}/index.html não encontrado")
    try:
        servidor, _, entrada = iniciar_servidor(pasta, args.porta, replay=None if not args.sem_replay else False,
                                                permitir_rede=args.permitir_rede, verboso=True)
    except OSError:
        servidor, _, entrada = iniciar_servidor(pasta, 0, replay=None if not args.sem_replay else False,
                                                permitir_rede=args.permitir_rede, verboso=True)
    print(f"Servindo {pasta} em {entrada}  (Ctrl+C para encerrar)")
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        servidor.shutdown()


if __name__ == "__main__":
    main()
