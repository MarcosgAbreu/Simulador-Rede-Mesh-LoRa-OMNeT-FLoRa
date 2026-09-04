# Rede Mesh LoRa — OMNeT++/FLoRa e IDE Python

Projeto de simulação de uma rede mesh LoRa com nodos estáticos, ativação aleatória, roteamento multi-hop, logs estruturados e vídeo MPEG.

## Dependências fixadas

- OMNeT++ 6.4.0
- INET 4.6.0
- FLoRa 1.3.0
- Python 3 com Tkinter, Matplotlib e Pillow
- FFmpeg com codificação MPEG-2

O FLoRa fornece os componentes LoRa do ambiente. A topologia mesh é uma extensão customizada deste projeto e não é LoRaWAN padrão.

## Instalação no WSL2

No Ubuntu dentro do WSL2, a partir deste diretório:

```bash
./scripts/install_wsl2.sh
source scripts/env.sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
```

## Como rodar

## Execução

Interface gráfica:

```bash
source scripts/env.sh
PYTHONPATH=src python3 -m lora_mesh.gui
```

Linha de comando:

```bash
source scripts/env.sh
PYTHONPATH=src python3 -m lora_mesh.cli \
  --nodes 10 \
  --area-m 1000 \
  --activation-min-s 0 \
  --activation-max-s 3600 \
  --simulation-time-s 14400 \
  --seed 1
```

Os campos de ativação e duração usam segundos. Os valores padrão correspondem a `0–1 hora` para ativação e `4 horas` de tempo máximo.

## Saídas

Cada execução cria uma pasta em `runs/` com:

- `parameters.json`: parâmetros completos;
- `scenario.ini`: configuração usada pelo simulador;
- `events.jsonl`: um evento JSON por linha;
- `run.log`: comando e saída do OMNeT++;
- `report.json`: métricas de entrega, perdas, saltos, latência, RSSI e SNR;
- `event-index.json`: uma cena de vídeo por evento;
- `video.mpg`: vídeo MPEG-2;
- `frames/`: imagens intermediárias.

## Eventos

Os eventos incluem ciclo de vida, ativação, descoberta de vizinhos, criação de mensagens, transmissões, recepção, encaminhamento, entrega, descarte e retransmissão. Cada registro transporta, quando disponível, tempo simulado, nodo, posição, mensagem, salto, TTL, frequência, largura de banda, SF, potência, RSSI e SNR.

## Testes

```bash
PYTHONPATH=src python3 -m pytest -q
```

O teste integrado precisa do executável OMNeT++ compilado. Para validar somente a camada Python, rode os testes unitários.

## AU915

O cenário utiliza canais uplink de 125 kHz da faixa AU915, seleção determinística baseada na seed, potência de 14 dBm e SF7–SF12. Os parâmetros ficam no INI para permitir calibração posterior. A configuração não substitui validação regulatória ou planejamento de rádio em campo.
# Simulador-Rede-Mesh-LoRa-OMNeT-FLoRa
