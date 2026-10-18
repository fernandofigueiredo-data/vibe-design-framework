# Etapas e formato do PLANO.md

O verificador lê o `PLANO.md`. Mantenha estes formatos.

```markdown
# Plano · <nome do projeto>

Design system primário: ../../referencias/<nome>
Design system secundário: ../../referencias/<outro>   (opcional)

## Briefing
(modelo de references/briefing.md)

## Recombinação
(só com dois design systems: o que vem de cada um)
- Fontes e cores: primário
- Cartões de preço: secundário (.preco-card, .preco-card--destaque)

## Seções
- #inicio — apresentar a proposta e levar à ação principal — hero do primário (.hero, .hero__grade, .botao)
- #recursos — três benefícios com ícone — .instrumentos, .cartao, .cartao__icone
- #prova — números e depoimento — .leituras, .leitura
- #contato — formulário de interesse — .formulario, .campo, .botao

## Conteúdo
### #inicio
Título: …
Texto: …
Botões: …

## Assets copiados da referência
- assets/observatorio_dd78fa76af3d.css
- assets/instrument-serif-latin-400-normal_eb2fa9c2b36a.woff2
```

Regras do plano:

- Cada seção de nível superior do site (`<section>` fora de outra seção) aparece aqui com o mesmo `id`. Cabeçalho e rodapé não são seções.
- Cada seção indica quais componentes do design system usa. Se precisar de algo que o design system não tem, registre no plano e depois no `DESVIOS.md`.
- Os caminhos dos design systems são relativos à pasta do site ou absolutos.

## Pontos de aprovação

| Momento | O que mostrar | O que perguntar |
|---|---|---|
| Depois do plano | `PLANO.md` | "Posso seguir com este plano?" |
| Depois do hero | Print ou link local do hero e o resultado do verificador | "O hero está no caminho certo?" |
| No fim | Relatório de verificação e prints em 1440 e 390 px | "Algo a ajustar antes de encerrar?" |

## Ciclo por seção

1. Construir a seção com markup e classes copiados do design system.
2. Checklist anti-amador.
3. `verificar_site.py`.
4. Corrigir só o que falhou.
