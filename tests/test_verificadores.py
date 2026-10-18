"""Os verificadores aprovam saídas corretas e reprovam saídas com defeitos conhecidos."""

import re
import shutil
import tempfile
import unittest
from pathlib import Path

from apoio import RAIZ

import verificar_ds
import verificar_site

PIPELINE = RAIZ / "examples" / "pipeline"


class TesteVerificarDS(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pasta = Path(self.tmp.name) / "observatorio-noturno"
        shutil.copytree(PIPELINE / "observatorio-noturno", self.pasta)
        self.ds = self.pasta / "design-system.html"

    def tearDown(self):
        self.tmp.cleanup()

    def verificar(self):
        return verificar_ds.verificar(self.pasta, renderizar=False, log=lambda *_: None)["criterios"]

    def trocar(self, antes, depois):
        texto = self.ds.read_text(encoding="utf-8")
        self.assertIn(antes, texto)
        self.ds.write_text(texto.replace(antes, depois, 1), encoding="utf-8")

    def test_exemplo_aprovado(self):
        c = self.verificar()
        self.assertTrue(all(v["aprovado"] for k, v in c.items() if k != "A12"), {k: v for k, v in c.items() if not v["aprovado"]})

    def test_classe_inventada_reprova_a5(self):
        self.trocar('class="cartao"', 'class="cartao cartao--brilhante"')
        self.assertFalse(self.verificar()["A5"]["aprovado"])

    def test_cor_inventada_reprova_a6(self):
        self.trocar('fill="#5fd3bc"', 'fill="#a855f7"')
        self.assertFalse(self.verificar()["A6"]["aprovado"])

    def test_rotulo_errado_reprova_a8(self):
        self.trocar("92px / 90.2px", "90px / 90px")
        self.assertFalse(self.verificar()["A8"]["aprovado"])

    def test_hero_alterado_reprova_a4(self):
        self.trocar('<span class="rotulo aparecer">Design system', '<span class="rotulo">Design system')
        self.assertFalse(self.verificar()["A4"]["aprovado"])

    def test_secao_fora_de_ordem_reprova_a3(self):
        texto = self.ds.read_text(encoding="utf-8")
        texto = texto.replace('id="cores" data-vd-secao', 'id="TEMP" data-vd-secao').replace('id="componentes" data-vd-secao', 'id="cores" data-vd-secao').replace('id="TEMP" data-vd-secao', 'id="componentes" data-vd-secao')
        self.ds.write_text(texto, encoding="utf-8")
        self.assertFalse(self.verificar()["A3"]["aprovado"])

    def test_style_inline_reprova_a9(self):
        self.trocar("</head>", "<style>.x{color:red}</style></head>")
        self.assertFalse(self.verificar()["A9"]["aprovado"])

    def test_arquivo_original_alterado_reprova_a1(self):
        with open(self.pasta / "index.html", "a", encoding="utf-8") as f:
            f.write("<!-- alterado -->")
        self.assertFalse(self.verificar()["A1"]["aprovado"])

    def test_stack_com_biblioteca_inexistente_reprova_a10(self):
        (self.pasta / "STACK.md").write_text("- **GSAP** — animações\n", encoding="utf-8")
        self.assertFalse(self.verificar()["A10"]["aprovado"])


class TesteVerificarSite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        base = Path(cls.tmp.name)
        shutil.copytree(PIPELINE / "observatorio-noturno", base / "observatorio-noturno")
        shutil.copytree(PIPELINE / "site-mare", base / "site-mare")
        cls.site = base / "site-mare"

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        self.original = (self.site / "index.html").read_text(encoding="utf-8")

    def tearDown(self):
        (self.site / "index.html").write_text(self.original, encoding="utf-8")

    def trocar(self, antes, depois):
        self.assertIn(antes, self.original)
        (self.site / "index.html").write_text(self.original.replace(antes, depois, 1), encoding="utf-8")

    def verificar(self):
        return verificar_site.verificar(self.site, log=lambda *_: None)["criterios"]

    def test_exemplo_aprovado(self):
        c = self.verificar()
        self.assertTrue(all(v["aprovado"] for v in c.values()), {k: v for k, v in c.items() if not v["aprovado"]})

    def test_defeitos_sao_reprovados(self):
        self.trocar('<h3>Coletar</h3>', '<h3 class="text-purple" style="color:#a855f7">Coletar</h3><img src="assets/inexistente.png">'
                    '<script src="https://www.googletagmanager.com/gtag/js"></script>')
        texto = (self.site / "index.html").read_text(encoding="utf-8").replace("</main>", '<section id="extra"></section></main>')
        (self.site / "index.html").write_text(texto, encoding="utf-8")
        c = self.verificar()
        for k in ("B1", "B2", "B3", "B4", "B7", "B10", "B12"):
            self.assertFalse(c[k]["aprovado"], k)


if __name__ == "__main__":
    unittest.main()
