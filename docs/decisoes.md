# Decisões de projeto

Etiquetas usadas nos `SKILL.md`: `[F-NN]` para as decisões que definem o formato e o processo da extração, e `[D-NN]` para as decisões gerais do projeto. Os princípios estão em [metodologia.md](metodologia.md).

## Formato e processo da extração

Duas abordagens orientaram a skill de extração. A **abordagem catálogo** produz uma página de documentação com seções fixas (hero, tipografia, cores, componentes, layout, movimento, ícones). A **abordagem reconstrução** define um processo em etapas: analisar, normalizar assets, tratar SVGs, reescrever e listar a stack. As duas se complementam; onde conflitam, valem as decisões abaixo.

| ID | Decisão | Motivo |
|---|---|---|
| F-01 | A saída é um **catálogo** de seções fixas. Da página original, só o hero é clonado. | Um design system resume regras visuais; um clone da página inteira não resume nada. |
| F-02 | O documento é escrito do zero, mas o markup de cada componente é copiado da fonte com as mesmas classes. Valores visuais só vêm da fonte. | Une limpeza e fidelidade. Verificado por A5–A7. |
| F-03 | Vários arquivos novos são permitidos; nenhum arquivo existente é modificado. | O design system fica legível e reaproveitável. A1 garante a integridade. |
| F-04 | `<style>` e `<script>` inline vão para arquivos em `assets/ds/`, preservando a ordem de carga. Exceção: blocos `text/tailwindcss`, que o runtime do Tailwind 4 só lê inline. | Ordem de carga errada quebra o Tailwind e scripts dependentes. |
| F-05 | Todo o texto é traduzido para PT-BR (rótulos, amostras e `STACK.md`). Código, classes, caminhos, marcas e nomes próprios ficam como estão e vão para `glossario.json`. O texto traduzido do hero fica entre 0,8× e 1,3× o comprimento original. | Decisão do autor (D-01). O limite de comprimento evita que a tradução quebre o layout. |
| F-06 | A seção de tipografia é uma tabela com uma linha por estilo medido e o rótulo `tamanho / entrelinha` (ex.: `40px / 48px`). | É o item mais informativo e o mais verificável (A8). |
| F-07 | Estados estáticos só aparecem quando a fonte tem a classe ou o atributo (ex.: `disabled`). Hover e foco ficam interativos, com legenda. | Forçar o hover exigiria inventar classes. |
| F-08 | SVGs em quatro categorias: **A** Lucide (vira `<i data-lucide>` só se o runtime do Lucide estiver na pasta), **B** herda cor (fica inline), **C** cores fixas (vira arquivo em `assets/ds/svg/` e `<img>`), **D** Iconify (fica como está). | Preserva a herança de cor e não depende de runtime ausente. |
| F-09 | HTML indentado e legível. Só SVGs da categoria B são minificados. | Um artefato de portfólio precisa ser lido. |
| F-10 | O processo tem etapas fixas e termina num verificador por script, não numa autoavaliação. | P-08. |
| F-11 | Nav horizontal no topo com âncora para cada seção. | Navegação do catálogo. |
| F-12 | Nenhuma frase de "papel" ("você é um…") nas instruções; só restrições. | P-02. |
| F-13 | A entrada usa `$ARGUMENTS` (substituição nativa das skills). | Formato oficial do Claude Code. |
| F-14 | Nada que não exista na fonte entra no design system. | P-06. |
| F-15 | Injeções de ferramentas de captura antigas (ex.: `<style data-scroll-fix>`) são removidas numa cópia de análise antes do inventário. A captura própria não injeta nada. | Essas injeções forçam opacidade e transform e apagam animações. |

## Decisões gerais

| ID | Decisão |
|---|---|
| D-01 | Tudo em PT-BR no design system. |
| D-02 | Captura própria (`capturar.py`), sem ferramenta ou serviço externo. Serve o HTML de origem, reescreve URLs para arquivos locais e reproduz offline com replay por service worker. |
| D-03 | Exemplos públicos só com frames autorais (`examples/frames/`). Sites de terceiros capturados ficam em `referencias/`, fora do versionamento. |
| D-04 | Licença MIT. Fontes, ícones e bibliotecas empacotados mantêm suas licenças em `THIRD_PARTY_LICENSES/`. |
| D-05 | Boas práticas web fora da metodologia foram avaliadas uma a uma; as incluídas viram critérios B6–B12 da skill de criação. |
| D-06 | O Playwright (com Chromium) é a única dependência. O resto usa a biblioteca padrão do Python. |
| D-07 | README em PT-BR com um resumo curto em inglês. |
| D-08 | Arquivos criados pela extração ficam em `assets/ds/{css,js,svg}/`, para nunca colidir com assets da referência. |
| D-09 | Classes de documentação (nav do catálogo, tabela de tipografia) só são permitidas com prefixo `ds-`, no máximo 15, definidas em `assets/ds/css/ds-documentacao.css` e usando apenas cores e fontes da fonte. |
| D-10 | Capturas de construtores que publicam o site num iframe `srcdoc` recebem `<!DOCTYPE html>` quando não o têm, porque documentos srcdoc sempre renderizam em modo padrão. A alteração fica registrada em `captura.json`. |
| D-11 | O K2 compara prints nas mesmas posições absolutas de rolagem, medidas no original, e reprova prints uniformes (página em branco). |
