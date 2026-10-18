# Classificação de SVGs e ícones

O inventário já conta os ícones por categoria em `manifesto.icones`. Ao escrever o design system, classifique cada SVG que você copiar da fonte.

| Categoria | Como reconhecer | Como escrever |
|---|---|---|
| **A · Lucide** | `<svg class="lucide lucide-nome …">` ou `<i data-lucide="nome">` | `<i data-lucide="nome" class="classes originais, sem lucide e lucide-*">`. **Só se** a pasta tiver o runtime do Lucide (veja `manifesto.bibliotecas`) e ele for chamado (`lucide.createIcons()`, em `assets/ds/js/`). Sem runtime, trate como B. |
| **B · Herda cor** | Usa `currentColor` em `fill` ou `stroke`, ou não tem nenhuma cor fixa (a cor vem do CSS) | Mantenha inline e minifique numa linha. Nunca transforme em `<img>`: isso quebra a herança de cor e o hover. |
| **C · Cores fixas** | Só cores literais (hex, rgb) e nenhuma dependência de CSS, inclusive no hover | Salve em `assets/ds/svg/<nome-descritivo>.svg` e use `<img src="assets/ds/svg/<nome>.svg" class="classes originais" alt="descrição em PT-BR">`. |
| **D · Iconify** | `<iconify-icon icon="…">` | Mantenha igual. O runtime do Iconify precisa estar referenciado como na fonte. |

Regras:

- Na dúvida entre B e C, escolha B.
- O mesmo SVG repetido recebe sempre a mesma categoria.
- SVGs decorativos levam `aria-hidden="true"` se a fonte já os marcava assim. Não acrescente atributos que a fonte não tinha, exceto o `alt` obrigatório do `<img>` na categoria C.
- No hero clonado, a conversão entre categorias é aceita pelo verificador. Qualquer outra mudança de estrutura não é.
