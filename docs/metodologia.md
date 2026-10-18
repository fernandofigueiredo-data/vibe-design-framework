# Metodologia

Os princípios abaixo orientam as duas skills. Cada regra dos arquivos `SKILL.md` aponta para um deles pela etiqueta `[P-NN]`. Decisões de projeto ficam em [decisoes.md](decisoes.md) (`[F-NN]` e `[D-NN]`).

## Por que modelos geram sites genéricos

**P-01 · Um pedido só produz o site médio.** Modelos de linguagem aprenderam com a média da web. Um único pedido amplo ("faça uma landing page escura com neon") devolve essa média: layout previsível, paleta batida, pouca profundidade. O trabalho precisa ser dividido em etapas pequenas, cada uma com uma decisão clara.

**P-02 · Função e estética competem pela atenção do modelo.** Quando o mesmo pedido exige código que funcione e visual refinado, o modelo prioriza o que não quebra. Por isso a estética é decidida antes, num artefato próprio (o design system), e a construção apenas aplica essas decisões. Atribuir "cargos" ao modelo ("aja como designer premiado") não resolve o problema e não é usado aqui.

**P-03 · Imagem orienta layout, não estilo.** Um print mostra onde as coisas ficam, mas não diz qual fonte, qual peso, qual curva de animação ou o que acontece no hover. Ao descrever a imagem para si mesmo, o modelo perde esses detalhes. Prints servem só para estrutura.

**P-04 · Código-fonte é a descrição exata.** Todo site é texto (HTML, CSS, JS). Entregar esse texto ao modelo elimina a adivinhação: a cor é o valor hexadecimal, a fonte é o nome declarado, a animação é o keyframe escrito. Todo valor visual usado deve existir na fonte.

## O design system como contrato

**P-05 · O design system reúne o DNA visual.** Tipografia (famílias, tamanhos, pesos e entrelinhas por papel), cores e superfícies, componentes com seus estados, padrões de layout e movimento. É um documento em código, navegável, que outra etapa pode consultar.

**P-06 · Extrair é organizar, não redesenhar.** A extração cataloga o que existe. Não inventa classes, não "melhora" cores, não acrescenta componentes. Se algo não está na fonte, não entra.

**P-07 · O que extrair com prioridade.** Classes e animações com seus tempos e curvas; tipografia e cores associadas a cada papel (título, botão, fundo); a construção real de cards, menus e botões.

**P-08 · Resultados variam: verifique sempre.** O mesmo pedido gera saídas diferentes a cada execução. Nenhuma saída é aceita pela autoavaliação do modelo; scripts determinísticos conferem cada critério.

**P-09 · Corrija o ponto, não o todo.** Quando algo falha, corrige-se apenas o item reprovado e verifica-se de novo. Regenerar tudo descarta o que estava certo.

## O papel de quem usa

**P-10 · Quem usa dirige e revisa.** A pessoa define objetivo, estilo e conteúdo, aprova o plano e revisa o resultado. O modelo executa. Por isso a skill de criação tem pontos de aprovação.

**P-11 · Toda referência tem três partes.** O HTML da página, a pasta de assets (fontes, imagens, CSS, JS) e o design system processado. Sem as três, a referência não está pronta.

**P-12 · Sinais de amadorismo a evitar.** Roxo e rosa genéricos, degradês azuis de sempre, seções com cortes óbvios, fundos chapados sem profundidade, tipografia sem cuidado, ausência de movimento e excesso de espaço vazio sem intenção.

**P-13 · Identidades podem ser combinadas.** Um site novo pode unir elementos de duas referências, desde que fique declarado de onde vem cada decisão.

**P-14 · Escolher bem as referências vale mais que inventar.** Antes de construir, seleciona-se a referência certa para o objetivo.

**P-15 · Técnica acima de ferramenta.** Um modelo modesto com o design system certo supera um modelo forte que só recebeu prints e adjetivos. Nenhuma regra deste framework depende de um modelo específico.

**P-16 · O escopo vai além de landing pages.** Os mesmos princípios valem para dashboards e aplicações web.

**P-17 · Capturar exige um navegador real.** Páginas modernas carregam conteúdo com JavaScript e sob demanda. A captura usa um navegador de verdade, rola a página inteira e não atravessa logins nem proteções.

**P-18 · A entrada é um arquivo, não uma descrição.** A extração recebe o caminho do `index.html` (ou a URL a capturar), nunca um resumo em texto do site.
