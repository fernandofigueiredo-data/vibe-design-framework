# Testes automatizados

`uv run python -m unittest discover -s tests`

| Arquivo | O que cobre |
|---|---|
| `tests/test_captura.py` | Captura de um site servido em localhost com um CDN falso noutra porta: reescrita de CSS, JS e srcset, link de navegação preservado, rastreador neutralizado, extensões, K1–K5 e funcionamento com o CDN desligado (replay). |
| `tests/test_inventario.py` | Tailwind com config inline e classes arbitrárias, Lucide nos dois formatos, Iconify, categorias de SVG, classes adicionadas por JS, sanitização de `data-scroll-fix` sem alterar o original, hashes registrados uma única vez. |
| `tests/test_verificadores.py` | `verificar_ds.py` aprova o exemplo e reprova classe inventada (A5), cor inventada (A6), rótulo errado (A8), hero alterado (A4), seção fora de ordem (A3), `<style>` inline (A9), arquivo original alterado (A1) e biblioteca inexistente no STACK (A10). `verificar_site.py` aprova o Maré e reprova seção fora do plano, referência quebrada, classe e cor inventadas, requisição externa, imagem sem `alt` e rastreador. |
