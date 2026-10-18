# Validação da instalação (critério D4)

Data: 18/10/2026. Origem: `github.com/fernandofigueiredo-data/vibe-design-framework`, branch `main`, commit `55f155f`.

## Ambiente

- macOS, Claude Code 2.1.302, Python 3.14.7.
- Configuração do Claude Code **isolada** numa pasta temporária (`CLAUDE_CONFIG_DIR`). Nenhum plugin ou marketplace prévio, nenhuma configuração do autor.
- Python num **venv novo**, sem pacotes instalados.

## Passos do README

| Passo | Comando | Resultado |
|---|---|---|
| 1 | `claude plugin marketplace add fernandofigueiredo-data/vibe-design-framework` | Marketplace clonado do GitHub e validado |
| 2 | `claude plugin install vibe-design@vibe-design-framework` | Plugin instalado e habilitado. `claude plugin details` lista as 2 skills (`criar-site` e `extrair-design-system`), com custo fixo de cerca de 196 tokens por sessão |
| 3 | `pip install playwright` | Playwright 1.64.0 |
| 4 | `python3 -m playwright install chromium` | Chromium instalado |
| 5 | Usar as skills | Ver abaixo |

**Passo 5:**

- **Sessão:** carregada a cópia exata que o passo 2 instalou (`--plugin-dir` apontando para o cache do plugin, porque a configuração isolada não tem login), a sessão lista `vibe-design:criar-site` e `vibe-design:extrair-design-system`.
- **Testes:** os 24 testes passam rodando a partir dessa cópia, com o venv do passo 3.
- **Verificadores:** `verificar_ds.py` (Observatório) e `verificar_site.py` (Maré) imprimem `APROVADO`.

## Conclusão

Critério D4 atendido: 5 passos, só o README como guia, instalação direto do GitHub.

O Playwright instalado (1.64) é mais novo que o travado no `uv.lock`, e os testes passam nas duas versões.
