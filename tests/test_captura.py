import json
import tempfile
import unittest
from pathlib import Path

from apoio import FIXTURES, servir_modelo

import capturar
import verificar_captura


class TesteCaptura(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        trocas = {}
        cls.cdn, cdn_url = servir_modelo(FIXTURES / "captura" / "cdn", trocas)
        trocas["{{CDN}}"] = cdn_url
        cls.cdn_url = cdn_url
        cls.site, cls.site_url = servir_modelo(FIXTURES / "captura" / "site", {"{{CDN}}": cdn_url})
        cls.tmp = tempfile.TemporaryDirectory()
        cls.destino = Path(cls.tmp.name) / "ref"
        cls.captura = capturar.capturar(cls.site_url + "/", cls.destino, log=lambda *_: None)
        cls.index = (cls.destino / "index.html").read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.site.shutdown()
        try:
            cls.cdn.shutdown()
        except Exception:
            pass
        cls.tmp.cleanup()

    def test_arquivos_gerados(self):
        for nome in ("index.html", "origem.html", "renderizado.html", "captura.json"):
            self.assertTrue((self.destino / nome).exists(), nome)

    def test_recursos_do_cdn_viram_locais(self):
        self.assertNotIn(self.cdn_url + "/estilo.css", self.index)
        self.assertNotIn(self.cdn_url + "/lib.js", self.index)
        self.assertNotIn(self.cdn_url + "/img-800.svg", self.index)
        self.assertIn('href="assets/estilo_', self.index)
        css = next(self.destino.glob("assets/estilo_*.css")).read_text(encoding="utf-8")
        self.assertNotIn("fonte.woff2\"", css.replace("fonte_", ""))
        self.assertRegex(css, r'url\("fonte_[0-9a-f]{12}\.woff2"\)')

    def test_link_de_navegacao_preservado(self):
        self.assertIn('href="/outra-pagina"', self.index)

    def test_rastreador_neutralizado_e_marcado(self):
        self.assertIn('data-vd-neutralizado="rastreador"', self.index)
        self.assertEqual(len(self.captura["neutralizados"]), 1)

    def test_sem_injecao_de_css(self):
        self.assertNotIn("data-scroll-fix", self.index)
        self.assertNotIn("!important", self.index)

    def test_literal_em_js_reescrito_e_dinamico_capturado(self):
        js = next(self.destino.glob("assets/lib_*.js")).read_text(encoding="utf-8")
        self.assertIn("/assets/dados_", js)
        urls = {r["url"] for r in self.captura["recursos"]}
        self.assertIn(self.cdn_url + "/dinamico.json", urls)

    def test_extensoes(self):
        for r in self.captura["recursos"]:
            self.assertFalse(r["arquivo"].endswith(".es"), r)

    def test_verificacao_completa_e_offline(self):
        r = verificar_captura.verificar(self.destino, url_original=self.site_url + "/", log=lambda *_: None)
        detalhes = json.dumps(r["criterios"], ensure_ascii=False, indent=1)[:3000]
        for k in ("K1", "K2", "K3", "K4", "K5"):
            self.assertTrue(r["criterios"][k]["aprovado"], f"{k} falhou:\n{detalhes}")
        # com o CDN desligado, a captura continua funcionando (replay)
        self.cdn.shutdown()
        r2 = verificar_captura.verificar(self.destino, sem_original=True, log=lambda *_: None)
        self.assertTrue(r2["criterios"]["K1"]["aprovado"], json.dumps(r2["criterios"]["K1"], ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
