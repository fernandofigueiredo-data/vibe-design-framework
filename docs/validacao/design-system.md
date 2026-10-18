# Validação dos design systems (A1–A12)

Data: 18/10/2026. Verificador: `skills/extrair-design-system/scripts/verificar_ds.py`.

| Referência | Idioma da fonte | Ciclos de correção | Resultado |
|---|---|---|---|
| Observatório (frame autoral, `examples/pipeline/observatorio-noturno`) | pt-BR | 1 (faltava o `STACK.md`) | A1–A12 aprovados |
| Ateliê Taipa (frame autoral, `examples/pipeline/atelie-claro`) | pt-BR | 0 | A1–A12 aprovados |
| Serra Azul (frame autoral, `examples/pipeline/painel-operacional`, Tailwind 4 e Lucide locais) | pt-BR | 0 | A1–A12 aprovados |
| volta-ev (página pública real, capturada em `referencias/`, fora do versionamento) | en | 2 (3 classes inventadas; defeito do verificador na leitura de rótulos, corrigido) | A1–A12 aprovados, inclusive tradução (A11) e comprimento do hero (A12) |
| genlabs (página pública real, capturada em `referencias/`, fora do versionamento) | en | 0 | A1–A12 aprovados, inclusive tradução (A11) e comprimento do hero (A12) |
| condor-landingpage (página pública real, capturada em `referencias/`, fora do versionamento) | en (declarado no `lang`; o texto da página está em português) | 0 | A1–A12 aprovados, inclusive A11 e A12 |

Critério D1 atendido: A1–A12 aprovados em 3 páginas reais e nos 3 frames autorais.

## Observações

- Nos dois frames novos, o inventário foi refeito com `inventariar.py` antes da extração. No painel, o bloco `<style type="text/tailwindcss">` ficou inline e o catálogo usa só utilitários que já existiam na fonte, porque o Tailwind 4 gera as classes a partir do DOM.
- Nas duas páginas reais novas, o hero e os componentes foram copiados do HTML da fonte por extração exata do trecho, trocando só os nós de texto. Os scripts da plataforma de publicação ficaram de fora, como na volta-ev.
- A condor-landingpage declara `lang="en"` com texto em português. O verificador segue o `lang`, então a checagem de texto repetido (A11) e de comprimento do hero (A12) foi aplicada mesmo assim.
- Depois da primeira aprovação, ajustes só visuais (descendente cortado no hero do Ateliê, widget e ícones vazios nas páginas reais) foram feitos e verificados de novo.

## Prints

- `docs/img/ds-atelie-1440x900.png`: primeira dobra do design system do Ateliê Taipa.
- `docs/img/ds-painel-1440x900.png`: primeira dobra do design system do Serra Azul.
