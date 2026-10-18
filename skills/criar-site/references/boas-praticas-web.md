# Boas práticas web

Critérios que não vêm da metodologia de design, mas foram avaliados um a um [D-05]. Entra o que é verificável, barato e compatível com a fidelidade ao design system. Fica de fora o que depende de domínio ou deploy, de ferramenta externa ou de um limite arbitrário.

## Incluídas (verificadas)

| Prática | Critério | Como cumprir |
|---|---|---|
| Sem rolagem horizontal em 360, 768 e 1440 px | B8 | Grades viram uma coluna; itens de grade com tabelas ou código ganham `min-width: 0`; tabelas largas ficam num contêiner com `overflow-x: auto`. |
| Nenhum erro de console | B6 | Todo script e asset referenciado existe; nada depende de rede. |
| Nada de requisições a terceiros | B7 | Fontes, bibliotecas e imagens ficam em `assets/`. Embeds pedidos no briefing vão para o `DESVIOS.md` como `[externo]`. |
| Metadados | B9 | `<html lang="pt-BR">`, `<title>`, `<meta name="description">`, `<meta name="viewport">`, `og:title` e `og:description`. |
| Hierarquia e ids | B9 | Um único `h1`; headings sem pular nível; `id`s únicos (as âncoras da nav dependem disso). |
| Alternativas e nomes | B10 | `alt` em toda `<img>` (vazio quando decorativa); botões só com ícone levam `aria-label`; todo campo tem `<label for>`. |
| Contraste AA | B10 | ≥ 4,5:1 em texto normal e ≥ 3:1 em texto grande (≥ 24 px, ou ≥ 18,66 px em negrito). Se falhar, troque por outra cor **da paleta** que passe. Se nenhuma passar, registre `[contraste]` e peça aprovação. Elementos desabilitados não contam. |
| Movimento reduzido | B10 | Toda página com animação tem `@media (prefers-reduced-motion: reduce)` desligando animações e transições. |
| Foco visível | B10 | Todo elemento focável muda de aparência no foco. Use o estado de foco do design system; se não houver, um contorno na cor de destaque da paleta, registrado como desvio. |
| Imagens estáveis | B11 | `width` e `height` (ou `aspect-ratio`) em toda `<img>`; `loading="lazy"` nas que estão abaixo da primeira dobra. |
| Assets enxutos | B11 | Nenhum arquivo sem uso em `assets/`. O peso total é reportado, sem limite. |
| Links externos seguros | B12 | `target="_blank"` sempre com `rel="noopener noreferrer"`. |
| Sem rastreadores | B12 | Nenhum script de analytics ou pixel. |

## Excluídas

| Prática | Motivo |
|---|---|
| Nota do Lighthouse ou orçamento de peso | Exige ferramenta extra, e qualquer limite seria arbitrário e conflitaria com design systems que usam WebGL. O peso é só reportado. |
| Validação W3C completa | Exige validador externo. O B9 cobre o essencial. |
| Canonical, sitemap e robots.txt | Dependem do domínio e do deploy. |
| Banner de cookies | Sem cookies de terceiros (B7 e B12), não há o que consentir. |
| Backend de formulário | A skill gera front-end estático; formulários sem destino ficam marcados como placeholder. |
| PWA, service worker, alternância de tema, multi-idioma | Fora do escopo, e seriam invenção quando o design system não os tem. |
| Minificação e build | O código precisa continuar legível. |
