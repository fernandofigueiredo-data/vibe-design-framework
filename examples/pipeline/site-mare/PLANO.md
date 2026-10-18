# Plano · Maré

Design system primário: ../observatorio-noturno

## Briefing

- **Projeto:** Maré, boletim de balneabilidade em tempo quase real para praias do litoral paulista (fictício).
- **Objetivo da página:** prefeituras agendarem uma conversa para conectar seus pontos de coleta.
- **Público:** secretarias de meio ambiente e turismo; chegam por indicação e já conhecem os boletins semanais.
- **Tipo:** landing.
- **Tom:** confiável, calmo, preciso.
- **Conteúdo disponível:** todo fictício, escrito para o exemplo; números marcados como de exemplo no rodapé.
- **Seções desejadas:** apresentação, como funciona, boletim do dia, para prefeituras, contato.
- **Restrições:** PT-BR; sem vídeo; formulário sem destino (placeholder).
- **Referência:** design system do Observatório (frame autoral).

## Aprovações

Exemplo de portfólio gerado de ponta a ponta pelo autor do framework. As aprovações do plano e do hero foram feitas pelo próprio autor.

## Seções
- #inicio — apresentar o boletim contínuo e levar ao contato — hero do Observatório (.hero, .hero__grade, .orbita, .leituras, .botao)
- #como-funciona — três etapas do boletim — .secao, .secao__cabeca, .instrumentos, .cartao, .cartao__icone
- #boletim — gráfico de coliformes e eventos do dia — .mapa, .mapa__grafico, .traco, .evento
- #prefeituras — dois formatos de contratação — .planos, .plano, .plano--destaque
- #contato — formulário de interesse — .contato, .formulario, .campo, .botao

## Conteúdo
### #inicio
Rótulo: Balneabilidade contínua · litoral paulista
Título: A praia de hoje, medida *hoje*.
Texto: boletim que se atualiza a cada coleta automática, com a causa provável de cada mudança.
Botões: Agendar conversa · Ver o boletim de hoje
Leituras: 38 pontos de coleta · 6 h entre amostras · 9 municípios

### #como-funciona
Coletar, explicar, avisar — três cartões numerados.

### #boletim
Gráfico de 24 h com faixa de referência e dois eventos; três eventos à direita.

### #prefeituras
Piloto (ativo) e Rede estadual (lista de espera, botão desabilitado).

### #contato
E-mail institucional e município.

## Assets copiados da referência
- assets/observatorio_dd78fa76af3d.css
- assets/animacoes.css (do assets/ds/css do design system)
- assets/revelacao.js (do assets/ds/js do design system)
- assets/instrument-serif-latin-400-normal_eb2fa9c2b36a.woff2
- assets/instrument-serif-latin-400-italic_82085662d2d2.woff2
- assets/jetbrains-mono-latin-wght-normal_59fbfa343a3b.woff2
