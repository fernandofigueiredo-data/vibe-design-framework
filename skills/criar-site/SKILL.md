---
name: criar-site
description: Cria um site, landing page, dashboard ou app web em etapas, a partir de um ou dois design systems extraídos (design-system.html + manifesto-ds.json), com aprovação do plano e do hero, uma seção por vez e verificação automática de fidelidade, acessibilidade e boas práticas. Use quando pedirem para criar, montar ou gerar um site ou página a partir de uma referência ou design system.
argument-hint: "[pasta-do-design-system] [pasta-do-site]"
---

# Criar site

Entrada: `$ARGUMENTS`. Normalmente é a pasta de uma referência que já tem `design-system.html` e `manifesto-ds.json`, e opcionalmente a pasta de destino do site (padrão `sites/<nome-do-projeto>`). Se não houver design system, use antes a skill `extrair-design-system`.

O verificador fica em `${CLAUDE_SKILL_DIR}/scripts/verificar_site.py` e precisa do Playwright (veja a skill de extração).

## Regras

1. Nunca gere o site inteiro de uma vez. Construa uma seção por iteração [P-01].
2. A estética vem do design system. Cada classe, cor, fonte e keyframe usado existe num manifesto declarado, ou fica registrado em `DESVIOS.md` com motivo [P-02] [P-04].
3. Prints e imagens só orientam layout, nunca valores de estilo [P-03].
4. Quem pediu o site aprova o plano e o hero antes de você seguir [P-10].
5. Não invente conteúdo do cliente: pergunte o que faltar ou use marcadores explícitos (`[preço a definir]`) [P-10].
6. Revise cada seção com o checklist anti-amador [P-12].
7. Verifique por script e corrija só o que falhar, até 3 ciclos [P-08] [P-09].

## Etapas

### 1. Briefing

Preencha o modelo de [references/briefing.md](references/briefing.md) com o que a pessoa disse. Pergunte, em uma única mensagem, só o que faltar para decidir objetivo, público, tipo (`landing`, `dashboard` ou `app`) [P-16], seções e conteúdo.

### 2. Seleção do design system [P-11] [P-14]

Confirme que a pasta tem `index.html`, `assets/`, `design-system.html` e `manifesto-ds.json`. Leia o manifesto e o design system. Se forem combinados dois design systems [P-13], decida qual é o primário e liste quais tokens vêm do secundário: fontes, cores, componentes ou movimento.

### 3. Plano (`PLANO.md`) e primeira aprovação

Escreva o `PLANO.md` seguindo [references/etapas.md](references/etapas.md):

- design systems declarados (`Design system primário: <caminho>`);
- lista de seções no formato `- #id — objetivo — componentes do design system usados`;
- conteúdo de cada seção;
- assets que serão copiados.

Mostre o plano e **espere aprovação**.

### 4. Hero e segunda aprovação

Crie a pasta do site e copie da referência só os assets necessários (CSS, JS, fontes e imagens que serão usados), preservando os caminhos relativos. Construa o `<head>` completo (metadados de [references/boas-praticas-web.md](references/boas-praticas-web.md)) e o hero, usando a estrutura e as classes do hero e dos componentes do design system. Rode o verificador, mostre o resultado e **espere aprovação**.

### 5. Uma seção por vez [P-01] [P-12]

Para cada seção do plano:

1. construa com componentes e classes do design system;
2. aplique o checklist de [references/checklist-anti-amador.md](references/checklist-anti-amador.md);
3. rode o verificador;
4. corrija antes de seguir para a próxima.

### 6. Integração

Nav com âncoras para as seções, rodapé, scripts de movimento do design system (revelação no scroll e contadores) e `prefers-reduced-motion`.

### 7. Verificação final [P-08] [P-09]

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/verificar_site.py" "<pasta-do-site>"
```

O script lê os design systems declarados no `PLANO.md` e grava `relatorio-verificacao.md`. Para cada critério reprovado, corrija só o apontado. Um desvio intencional (por exemplo, uma classe utilitária do Tailwind que a referência não usa) vai para o `DESVIOS.md` no formato:

```
- [classe] md:grid-cols-3 — grade de 3 colunas no plano de preços
- [cor] #ffffff — texto sobre o botão laranja para atingir contraste AA
- [contraste] body > main > … — aprovado pelo usuário em 2026-10-18
- [externo] https://www.youtube-nocookie.com/ — vídeo pedido no briefing
- [foco] a: Logo — foco indicado pelo contorno do cabeçalho
```

Desvios de contraste e de foco só valem com a aprovação explícita da pessoa, registrada com a data.

## Saída

Em `<pasta-do-site>`: `index.html`, `assets/`, `PLANO.md`, `DESVIOS.md` (mesmo vazio, com o título) e `relatorio-verificacao.md`. O site está pronto quando o verificador imprime `APROVADO` e a pessoa aprovou o resultado final.
