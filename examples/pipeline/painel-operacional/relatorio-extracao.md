# Relatório de extração · Serra Azul

## Captura

- Origem: frame autoral `examples/frames/painel-operacional`, servido em localhost e capturado com `capturar.py`.
- 9 recursos salvos (CSS de fontes, 6 fontes IBM Plex, runtime do Tailwind 4 e runtime do Lucide), nenhum omitido, nenhum rastreador.
- K1–K5 aprovados: funciona offline, pior diferença visual de 0,00% e 100% dos estilos amostrados iguais.

## Decisões

- **Inventário:** `sanitizar.py` não encontrou injeções; `inventariar.py` refeito sobre o `index.html` (175 classes, 12 cores, 2 keyframes, 18 ícones, 7 estilos tipográficos; bibliotecas Tailwind CSS e Lucide).
- **Assets normalizados:** o bloco `<style type="text/tailwindcss">` (tema com cores, fontes, as animações `entrada` e `crescer` e o foco) ficou inline, como manda a skill, logo depois do runtime do Tailwind 4. O `<script>` inline `lucide.createIcons()` foi para `assets/ds/js/icones.js`, carregado depois do runtime do Lucide.
- **Hero:** clone exato do topo fixo (`header` com sobrescrito, título, busca, sino e botão). Só os textos mudaram; o placeholder e o `aria-label` também foram reescritos para o catálogo.
- **Navegação:** a barra lateral da fonte virou a navegação do catálogo, com as mesmas classes e os ícones Lucide que já existiam na página (nenhum ícone novo).
- **SVGs:** 16 ícones Lucide (categoria A, runtime local presente) viraram `<i data-lucide>` com as classes originais. O gráfico de linhas e o mapa de zonas são da categoria B (contornos em `currentColor`) e ficaram inline.
- **Classes:** como o Tailwind 4 gera as classes a partir do DOM, o catálogo usa só utilitários que já existiam na fonte. Uma tentativa com `text-agua` (cor do tema sem uso na fonte) foi descartada antes da verificação.
- **Classes de documentação (3 de 15):** `ds-linha`, `ds-nome` e `ds-rotulo`, com cores literais da fonte (#dedfd8, #55595f) e a família IBM Plex Mono.
- **Cores:** amostras com os utilitários `bg-*` do tema; as três cores sem utilitário na fonte (grafite-suave, fio e alerta-texto) usam SVG com `fill` literal.
- **Idioma:** a fonte já está em PT-BR, então não houve tradução (`traducao.json` vazio).

## Verificação (verificar_ds.py)

A1–A12 aprovados no primeiro ciclo, sem correções.
