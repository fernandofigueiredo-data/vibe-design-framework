# Relatório de extração · Ateliê Taipa

## Captura

- Origem: frame autoral `examples/frames/atelie-claro`, servido em localhost e capturado com `capturar.py`.
- 5 recursos salvos (1 CSS, 3 fontes e o selo em SVG), nenhum omitido, nenhum rastreador.
- K1–K5 aprovados: funciona offline, pior diferença visual de 0,00% e 100% dos estilos amostrados iguais.

## Decisões

- **Inventário:** `sanitizar.py` não encontrou injeções; `inventariar.py` refeito sobre o `index.html` (40 classes, 9 cores, 3 keyframes, 6 ícones, 7 estilos tipográficos, nenhuma biblioteca).
- **Assets normalizados:** a fonte não tem `<style>` inline; todo o CSS já está em `assets/atelie_cdb5ff0db780.css`, usado com o mesmo caminho. O `<script>` inline (revelação no scroll com `.revelar` → `.visto`) foi para `assets/ds/js/revelacao.js`, carregado no fim do body como na fonte.
- **Hero:** clone exato de `main > section:nth-of-type(1)` (`.abertura.coluna`), com a prancha animada. Só os textos mudaram, inclusive os rótulos do desenho, que agora descrevem a animação `desenhar`.
- **SVGs:** os 6 SVGs da fonte são da categoria B (stroke em `currentColor`) e continuam inline: a seta dos convites, as quatro plantas das obras e a prancha. O selo já era um arquivo da fonte (`assets/selo_abd6ec63baa5.svg`) e é usado com o mesmo caminho.
- **Tipografia:** os estilos dependem do contexto (`.etapa p`, `.numero span`, `.obra__nome em`). Cada amostra fica dentro do mesmo contexto, com `ds-contexto` zerando padding, borda e fundo.
- **Classes de documentação (9 de 15):** `ds-contexto`, `ds-linha`, `ds-nome`, `ds-rotulo`, `ds-amostras`, `ds-amostra`, `ds-legenda`, `ds-palco` e `ds-bloco`. Usam só variáveis da fonte (`--fio`, `--tinta-suave`, `--texto`).
- **Cores:** amostras em SVG com `fill` igual ao valor literal da fonte; as superfícies são os próprios componentes (`.numeros`, `.metodo`, `.indice`).
- **Movimento:** `subir`, `surgir` e `desenhar` tocam uma vez ao carregar, como na fonte. Um link "Recarregar nesta seção" abre a página já em `#movimento` para repeti-las.
- **Idioma:** a fonte já está em PT-BR, então não houve tradução (`traducao.json` vazio). O hero foi reescrito para apresentar o design system, com comprimento parecido ao original.

## Verificação (verificar_ds.py)

A1–A12 aprovados no primeiro ciclo, sem correções.
