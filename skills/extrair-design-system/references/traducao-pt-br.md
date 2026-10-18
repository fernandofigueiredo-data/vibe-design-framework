# Tradução para PT-BR

Todo texto visível do design system fica em português do Brasil: títulos, parágrafos, rótulos, botões, itens de menu, selos, legendas e textos de amostra.

## O que não se traduz

- Código, nomes de classe, caminhos, valores (`#0a0a0a`, `40px / 48px`) e identificadores técnicos.
- Marcas, nomes de produto, nomes próprios e siglas.

Liste cada um desses termos em `glossario.json`, assim:

```json
{"termos": ["Volta", "EV", "Lucide", "Tailwind CSS", "SaaS"]}
```

O verificador aceita um texto igual ao da fonte só quando, sem os termos do glossário, sobra menos de duas palavras.

## Comprimento

O texto traduzido do hero deve ter entre **0,8× e 1,3×** o comprimento do original, contado em caracteres. Prefira formulações curtas: o português costuma ser mais longo que o inglês. Nenhum texto do hero pode transbordar do seu contêiner.

## Registro da tradução

Grave em `traducao.json` cada texto do hero (e, opcionalmente, os demais):

```json
[
  {"onde": "hero", "origem": "Real-time vehicle monitoring", "traducao": "Monitoramento do veículo ao vivo"}
]
```

Se a fonte já estiver em português (`manifesto.idioma_fonte` começa com `pt`), a tradução e a checagem de comprimento não se aplicam. Mesmo assim, o hero do design system apresenta o próprio design system em vez do produto original.
