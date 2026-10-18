# Convenções do design-system.html

O verificador (`verificar_ds.py`) depende destas convenções. Siga-as à risca.

## Documento

- `<html lang="pt-BR">`, `<meta charset="utf-8">`, `<meta name="viewport" …>` e um `<title>` em PT-BR: "Design system · <nome da referência>".
- No `<head>`, na mesma ordem da fonte: fontes, CSS da fonte (mesmos caminhos), runtimes que precisam ficar no head e os arquivos de `assets/ds/css/`. Cada import leva um comentário curto dizendo o que contém.
- Antes de `</body>`: os scripts da fonte e os de `assets/ds/js/`, com o mesmo tipo de comentário.
- Nenhum `<style>` nem `<script>` inline. As exceções são `<style type="text/tailwindcss">` e JSON-LD.
- Um atributo `style` só é permitido se o mesmo valor existir na fonte, por exemplo dentro do hero clonado.

## Navegação

O primeiro `<nav>` do body é a navegação do catálogo. Ele tem uma âncora `href="#<id>"` para cada seção, na mesma ordem das seções. Construa a nav com componentes e classes da própria fonte, como o menu original, e use `ds-*` só se não houver equivalente.

## Seções

Cada seção é `<section id="…" data-vd-secao>`, nesta ordem:

| id | Conteúdo |
|---|---|
| `hero` | O clone do hero original (seletor em `manifesto.hero.seletor`): mesmas tags, mesmas classes, mesma estrutura, mesmas imagens, animações e fundo. A `<section id="hero" data-vd-secao>` não tem classe e tem um único filho, que é o clone. Só os nós de texto mudam: apresente o design system em PT-BR, com comprimento parecido ao original. |
| `tipografia` | Uma linha por item de `manifesto.tipografia`. Cada linha é um elemento com `data-vd-estilo="<estilo exato do manifesto>"` (ex.: `Título 1`, `Negrito G`, `Parágrafo`, `Regular P`) e contém: o nome do estilo, uma amostra viva usando a **mesma tag e as mesmas classes** do `seletor_exemplo` e o rótulo `<tamanho> / <entrelinha>` exatamente como no manifesto (ex.: `92px / 90.2px`), alinhado à direita. A ordem segue o manifesto. |
| `cores` | Fundos (página, seção, cartão, vidro/blur, se houver), bordas, divisores, sobreposições e gradientes. Cada amostra usa as classes ou variáveis da fonte e traz uma legenda com o valor e onde ele é usado. |
| `componentes` | Botões, campos, cartões e selos que existem na fonte (ver `manifesto.componentes`), copiados com as mesmas classes. Mostre lado a lado os estados que a fonte permite produzir estaticamente (`disabled`, `aria-disabled`, variantes). Hover, foco e clique ficam interativos, com a legenda "passe o mouse" ou "use Tab". |
| `layout` | Contêineres, grades e espaçamentos de seção, com 2 ou 3 padrões reais da fonte (ver `manifesto.layout`): o layout do hero, uma grade e um bloco dividido. |
| `movimento` | Uma galeria com cada animação, transição e revelação da fonte, usando as mesmas classes e keyframes, com legenda de duração e curva (ver `manifesto.keyframes` e `manifesto.transicoes`). |
| `icones` | Só se `manifesto.total_icones > 0`. O mesmo sistema de ícones (Lucide, Iconify ou SVG próprio), com variações de tamanho e herança de cor, com o mesmo markup e as mesmas classes. |

## Classes de documentação

Se a fonte não tiver nenhuma classe que sirva para a estrutura do catálogo (por exemplo, a tabela de tipografia ou as legendas das amostras):

- crie no máximo 15 classes com prefixo `ds-`;
- defina-as em `assets/ds/css/ds-documentacao.css`;
- use nelas só cores, fontes e espaçamentos que já aparecem no manifesto, e nenhum `@keyframes` novo.

## Ícones e imagens

- Categoria A (Lucide): `<i data-lucide="nome" class="…classes originais sem lucide-*">`. Só use quando o runtime do Lucide estiver na pasta; se não estiver, mantenha o SVG inline.
- Categoria B (herda cor): SVG inline minificado numa linha.
- Categoria C (cores fixas): arquivo em `assets/ds/svg/<nome>.svg` e `<img src="assets/ds/svg/<nome>.svg" class="…" alt="…">`.
- Categoria D (Iconify): `<iconify-icon icon="…">` como na fonte.
