# Validação da captura (K1–K5)

Gerado a partir de `.vd/verificacao-captura.json` de cada captura. Data: 18/10/2026.

## Frames autorais (reproduzível: `python scripts/dev/capturar_frames.py --substituir`)

| Frame | K1 | K2 | K3 | K4 | K5 | Pior diferença visual | Estilos iguais |
|---|---|---|---|---|---|---|---|
| atelie-claro | ok | ok | ok | ok | ok | 0.00% | 1.0 |
| observatorio-noturno | ok | ok | ok | ok | ok | 0.06% | 1.0 |
| painel-operacional | ok | ok | ok | ok | ok | 0.00% | 1.0 |

## Páginas públicas reais (capturadas localmente em `referencias/`, fora do versionamento)

| Página | K1 | K2 | K3 | K4 | K5 | Pior diferença visual | Estilos iguais |
|---|---|---|---|---|---|---|---|
| https://condor-landingpage.aura.build/ | ok | ok | ok | ok | ok | 0.41% | 1.0 |
| https://genlabs.aura.build/ | ok | ok | ok | ok | ok | 0.53% | 1.0 |
| https://volta-ev.aura.build/ | ok | ok | ok | ok | ok | 0.04% | 1.0 |

As três páginas reais são publicadas por um construtor de sites dentro de um iframe `srcdoc`, com recursos em CDNs; uma delas (volta-ev) tem uma cena WebGL do Unicorn Studio carregada em tempo de execução. Todas funcionam offline pelo replay do `servir.py`.
