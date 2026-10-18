---
name: extrair-design-system
description: Captura um site de referência com fidelidade (offline, sem injeções) e extrai dele um design system verificável em PT-BR (design-system.html, STACK.md e manifesto-ds.json). Use quando pedirem para capturar, baixar ou clonar uma referência, extrair ou gerar o design system, o "DNA visual" ou o design-system.html de uma URL ou de um index.html.
argument-hint: "[url-ou-caminho-do-index.html] [pasta-destino]"
---

# Extrair design system

Entrada: `$ARGUMENTS`. É uma URL `http(s)` (captura a referência primeiro) ou o caminho de uma pasta (ou de um `index.html`) que já tenha `index.html` e `assets/` [P-18]. Se vier uma URL sem pasta de destino, use `referencias/<nome-do-host>`.

Os scripts ficam em `${CLAUDE_SKILL_DIR}/scripts/` e precisam do Playwright. Rode-os com `python3`. Se faltar o módulo, use `uv run --with playwright python3 …` ou peça para instalar com `pip install playwright` e `python3 -m playwright install chromium`.

## Regras

1. Nada que não exista na fonte entra no design system: classes, cores, fontes, keyframes, componentes [P-06] [F-14].
2. Nenhum arquivo existente na pasta é alterado. Só se criam arquivos novos [F-03].
3. Valores visuais são lidos do código, nunca deduzidos de print [P-03] [P-04].
4. O hero é um clone do original com as mesmas tags e classes. Só o texto muda [F-01].
5. Todo texto visível fica em PT-BR, exceto o que está no glossário [F-05] [D-01].
6. Uma etapa termina por completo antes da próxima [F-10].
7. A verificação é feita por script. Ao falhar, corrija só o item reprovado [P-08] [P-09].

## Etapas

### 0. Capturar (só se a entrada for URL) [D-02] [P-17]

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/capturar.py" "<url>" "<pasta>"
python3 "${CLAUDE_SKILL_DIR}/scripts/verificar_captura.py" "<pasta>"
```

O código de saída 2 significa login, CAPTCHA ou desafio anti-bot. Pare e explique: a captura não contorna proteções. Se K1–K5 reprovarem, mostre o relatório (`<pasta>/.vd/verificacao-captura.json`) e pergunte se deve seguir. Detalhes em [references/captura-modo-fidelidade.md](references/captura-modo-fidelidade.md).

### 1. Preparar [F-15]

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/sanitizar.py" "<pasta>"
```

Registra os hashes de todos os arquivos (base do A1). Se o `index.html` vier com injeções de capturas antigas, gera `vd-analise.html` sem elas.

### 2. Inventariar [P-05] [P-07]

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/inventariar.py" "<pasta>"
```

Leia o `manifesto-ds.json` inteiro antes de escrever qualquer coisa. Ele traz classes, cores, fontes, keyframes, transições, estados, ícones por categoria, o seletor do hero, os estilos tipográficos medidos (com o tamanho e a entrelinha exatos), os componentes e os padrões de layout. Leia também o HTML de origem (`pagina_analisada`) e, se existir, o `renderizado.html`, que mostra o markup gerado por JavaScript.

### 3. Normalizar assets [F-04] [D-08]

Copie cada `<style>` e `<script>` inline da fonte para arquivos novos em `assets/ds/css/` e `assets/ds/js/`, nomeados pela função (`animacoes.css`, `revelacao.js`, `tailwind-config.js`). Mantenha a ordem de carga: um script de configuração vem logo depois do runtime que o lê. Exceções: blocos `<style type="text/tailwindcss">` ficam inline, e `<script type="application/ld+json">` não é copiado.

### 4. Classificar ícones e SVGs [F-08]

Siga [references/classificacao-svg.md](references/classificacao-svg.md). Quando houver dúvida entre herdar cor (B) e cor fixa (C), escolha B.

### 5. Escrever `design-system.html` [F-01] [F-02] [F-06] [F-07] [F-09] [F-11]

Escreva do zero, seção por seção, seguindo as convenções de [references/secoes-design-system.md](references/secoes-design-system.md): nav, hero, tipografia, cores, componentes, layout, movimento e ícones (esta última só se `total_icones > 0`). Use os mesmos CSS, JS e fontes da fonte (mesmos caminhos), mais os arquivos de `assets/ds/`. Se precisar de estrutura de documentação sem equivalente na fonte, use no máximo 15 classes `ds-*`, definidas em `assets/ds/css/ds-documentacao.css` e só com cores e fontes do manifesto [D-09].

Traduza conforme [references/traducao-pt-br.md](references/traducao-pt-br.md) e grave `glossario.json` e `traducao.json`.

### 6. Escrever `STACK.md` [F-14]

Escreva uma linha por biblioteca de `manifesto.bibliotecas`, nem mais nem menos, no formato `- **Nome** — o que faz nesta página`, em PT-BR.

### 7. Verificar [F-10] [P-08] [P-09]

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/verificar_ds.py" "<pasta>"
```

Para cada critério reprovado, corrija só o que o relatório aponta e rode de novo, até no máximo 3 ciclos. Se ainda houver falhas, pare e reporte quais e por quê; não declare sucesso. Por fim, escreva o `relatorio-extracao.md`: o que foi capturado, decisões tomadas (categorias de SVG, termos do glossário, classes `ds-*`) e o resultado de A1–A12.

## Saída

Na pasta da referência, todos como arquivos novos: `design-system.html`, `STACK.md`, `manifesto-ds.json`, `glossario.json`, `traducao.json`, `relatorio-extracao.md` e `assets/ds/`. A extração está concluída quando o `verificar_ds.py` imprime `APROVADO` (e, se houve captura, `verificar_captura.py` também).
