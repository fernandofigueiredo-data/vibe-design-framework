# Relatório de extração · Observatório

## Captura

- Origem: frame autoral `examples/frames/observatorio-noturno`, servido em localhost e capturado com `capturar.py`.
- 4 recursos salvos (1 CSS e 3 fontes), nenhum omitido, nenhum rastreador.
- K1–K5 aprovados: funciona offline, pior diferença visual de 0,06% e 100% dos estilos amostrados iguais.

## Decisões

- **Assets normalizados:** o bloco `<style>` inline (keyframes `girar`, `pulsar` e `cintilar`) foi para `assets/ds/css/animacoes.css`. O `<script>` inline (revelação no scroll e contador) foi para `assets/ds/js/revelacao.js`, carregado no fim do body como na fonte.
- **SVGs:** 5 ícones da categoria B (stroke em `currentColor`) continuam inline. A marca e o céu estrelado são da categoria C. A marca virou `assets/ds/svg/marca-observatorio.svg`; o céu fica no hero clonado, onde a estrutura precisa ser mantida.
- **Tipografia:** os estilos da fonte dependem do contexto (`.hero h1`, `.secao h2`, `.cartao h3`). Cada amostra fica dentro do mesmo contexto, com a classe de documentação `ds-contexto`, que só zera padding, borda e fundo.
- **Classes de documentação (9 de 15):** `ds-contexto`, `ds-linha`, `ds-nome`, `ds-rotulo`, `ds-amostras`, `ds-amostra`, `ds-legenda`, `ds-palco` e `ds-bloco`. Todas usam só variáveis da fonte (`--linha`, `--texto-suave`, `--mono`, `--raio`).
- **Cores:** as amostras são SVGs com `fill` igual ao valor literal da fonte. As superfícies são os próprios componentes (`.cartao`, `.plano`, `.plano--destaque` e `.leituras`).
- **Idioma:** a fonte já está em PT-BR, então não houve tradução. O hero foi reescrito para apresentar o design system, com comprimento parecido ao original.

## Verificação (verificar_ds.py)

A1–A12 aprovados.
