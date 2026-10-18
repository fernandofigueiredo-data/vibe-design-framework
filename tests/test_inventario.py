import shutil
import tempfile
import unittest
from pathlib import Path

from apoio import FIXTURES

import inventariar
import sanitizar


def copiar(nome: str, destino: Path) -> Path:
    alvo = destino / nome
    shutil.copytree(FIXTURES / "inventario" / nome, alvo)
    return alvo


class TesteInventario(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_tailwind_config_cores_fontes_e_classes_arbitrarias(self):
        pasta = copiar("tailwind-config", self.dir)
        m = inventariar.inventariar(pasta, renderizar=False)
        self.assertIn("Tailwind CSS", [b["nome"] for b in m["bibliotecas"]])
        self.assertIn("#0f766e", m["cores"])      # cor do tailwind.config inline
        self.assertIn("#0b0f14", m["cores"])      # cor de classe arbitrária bg-[...]
        self.assertIn("#115e59", m["cores"])      # cor de estado hover:bg-[...]
        self.assertIn("fixture display", m["fontes"])
        self.assertIn("hover:bg-[#115e59]", m["estados"]["classes"])
        self.assertEqual(m["idioma_fonte"], "en")

    def test_lucide_nos_dois_formatos_e_categorias_de_svg(self):
        pasta = copiar("lucide-misto", self.dir)
        m = inventariar.inventariar(pasta, renderizar=False)
        nomes = {i["nome"] for i in m["icones"]["A_lucide"]}
        self.assertEqual(nomes, {"search", "bell"})
        self.assertEqual(m["icones"]["B_heranca"]["quantidade"], 1)
        self.assertEqual(m["icones"]["C_cores_fixas"]["quantidade"], 1)
        self.assertEqual(m["total_icones"], 4)
        self.assertIn("visivel", m["classes"])    # classe adicionada por JS

    def test_iconify(self):
        pasta = copiar("iconify", self.dir)
        m = inventariar.inventariar(pasta, renderizar=False)
        self.assertEqual(m["icones"]["D_iconify"], [{"nome": "solar:bolt-linear", "ocorrencias": 2}])
        self.assertIn("Iconify", [b["nome"] for b in m["bibliotecas"]])

    def test_scroll_fix_removido_so_na_copia(self):
        pasta = copiar("scroll-fix", self.dir)
        original = (pasta / "index.html").read_text(encoding="utf-8")
        r = sanitizar.sanitizar(pasta)
        self.assertEqual(r["injecoes_removidas"][0]["injecao"], "style data-scroll-fix")
        self.assertEqual((pasta / "index.html").read_text(encoding="utf-8"), original)
        self.assertNotIn("data-scroll-fix", (pasta / "vd-analise.html").read_text(encoding="utf-8"))
        m = inventariar.inventariar(pasta, renderizar=False)
        self.assertEqual(m["pagina_analisada"], "vd-analise.html")
        self.assertNotIn("opacity-0", m["classes"])  # classe só existia no bloco injetado
        self.assertIn("entrar", m["keyframes"])

    def test_hashes_antes_registrados_uma_vez(self):
        pasta = copiar("iconify", self.dir)
        sanitizar.sanitizar(pasta)
        primeiro = (pasta / ".vd" / "hashes-antes.json").read_text()
        (pasta / "novo.txt").write_text("x")
        sanitizar.sanitizar(pasta)
        self.assertEqual((pasta / ".vd" / "hashes-antes.json").read_text(), primeiro)


if __name__ == "__main__":
    unittest.main()
