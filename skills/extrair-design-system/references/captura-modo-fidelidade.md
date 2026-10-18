# Captura em modo fidelidade

`capturar.py` grava uma cópia da página que funciona sem internet e é fiel ao original.

## O que ela faz

1. Abre a URL no Chromium (Playwright) com o user agent padrão, sem disfarce de automação.
2. Grava todas as respostas de rede: HTML, CSS, JS, fontes, imagens, vídeos, JSON e dados de WebGL.
3. Espera a rede ficar ociosa e rola a página até o fim para disparar lazy-load e revelações. Depois volta ao topo.
4. Se a página for só um invólucro com um iframe ocupando a tela (padrão de construtores de sites), usa o documento interno. Documentos `srcdoc` sem doctype recebem `<!DOCTYPE html>`, porque é assim que o navegador os renderiza.
5. Salva o **HTML de origem**, não o DOM já animado, e reescreve para `assets/` todas as URLs capturadas: atributos, `url()` e `@import` do CSS, `srcset` e literais de URL dentro de JS e JSON.
6. Baixa também o que o HTML e o CSS citam mas o navegador não pediu: tamanhos alternativos de `srcset`, pesos de fonte, imagens de hover.
7. Neutraliza scripts de analytics conhecidos com `type="text/plain"` e `data-vd-neutralizado`. Eles não têm efeito visual.

## O que ela nunca faz

- Injetar CSS ou JS, forçar opacidade, remover animações ou smooth scroll, ou bloquear vídeos.
- Contornar login, CAPTCHA ou desafio anti-bot. Nesses casos a captura **aborta** com código 2.
- Rastrear outras páginas do site. Ela captura uma página por vez.

Toda alteração necessária fica marcada com `data-vd-*` e registrada em `captura.json` (`alteracoes`).

## Arquivos gerados

| Arquivo | Para quê |
|---|---|
| `index.html` | A página servida: o HTML de origem com URLs locais. |
| `origem.html` | O HTML exatamente como veio do servidor (auditoria e K4). |
| `renderizado.html` | O DOM depois do JavaScript, só para análise. Não servir. |
| `assets/` | Todos os recursos, com nome `base_hash12.ext` e extensão coerente com o tipo. |
| `captura.json` | O mapa URL → arquivo, os recursos omitidos com motivo, os rastreadores neutralizados e as alterações. |

## Como abrir

```bash
python3 scripts/servir.py <pasta>
```

O `servir.py` serve a pasta em `localhost` e registra um service worker que responde a qualquer URL externa a partir do `captura.json`. Isso cobre URLs montadas em tempo de execução, que a reescrita estática não alcança. O que não está na captura recebe 404: a página nunca sai para a rede. Abrir o `index.html` com duplo clique (`file://`) não é suportado.

## Critérios (verificar_captura.py)

| ID | Critério |
|---|---|
| K1 | Servida com a rede bloqueada, nenhuma requisição falha nem sai para a rede, exceto as listadas como omitidas. |
| K2 | Prints em 5 posições de rolagem (as mesmas posições absolutas no original e na captura) diferem em no máximo 2% dos pixels, ignorando `<canvas>`, `<video>` e `<iframe>`. Prints todos uniformes reprovam. |
| K3 | Pelo menos 95% de 50 elementos amostrados têm `font-family`, `font-size`, `color` e `background-color` iguais aos do original. |
| K4 | Comparado ao `origem.html`, o `index.html` não tem elemento novo nem atributo novo além de `data-vd-*` (e `type` em rastreador neutralizado). |
| K5 | Todo arquivo em `assets/` tem extensão coerente com o content-type. |

K2 e K3 precisam acessar o site original. Se não houver acesso, use `--sem-original` e registre que eles não foram verificados.
