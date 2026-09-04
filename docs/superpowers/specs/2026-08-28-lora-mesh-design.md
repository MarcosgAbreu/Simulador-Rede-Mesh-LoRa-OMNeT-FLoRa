# Design: simulador e IDE de rede mesh LoRa

## Objetivo

Entregar um projeto executável no WSL2 que instale o ambiente OMNeT++/INET/FLoRa, simule uma rede mesh LoRa com nodos estáticos distribuídos aleatoriamente em uma área quadrada e ofereça uma IDE Python para parametrizar, executar, visualizar e reproduzir os eventos da simulação.

O projeto inicial terá como cenário padrão:

- área de `1000 m x 1000 m`;
- número de nodos configurável;
- ativação aleatória entre `0` e `3600 s`;
- duração máxima de `14400 s` (4 horas);
- posições aleatórias determinísticas por semente;
- gateway de observabilidade no centro da área;
- nodos sem restrição de energia;
- vídeo MPEG com duração de `300 ms` por evento.

## Restrições e decisões técnicas

FLoRa representa originalmente LoRaWAN em topologia estrela. A topologia mesh será adicionada por módulos do projeto: cada nodo manterá vizinhos alcançáveis, escolherá o próximo salto e encaminhará pacotes até o gateway. A extensão usará componentes compatíveis com o modelo de rádio e propagação do INET/FLoRa, mas não afirmará que o protocolo é LoRaWAN padrão.

Para AU915, o cenário documentará os canais e a configuração selecionada, incluindo frequência, largura de banda, fator de espalhamento, potência e limites de saltos. A configuração deverá ser facilmente substituível por outra regulamentação local. Valores que dependam da versão instalada do FLoRa/INET serão isolados em um arquivo de configuração, em vez de espalhados nos módulos.

## Arquitetura

### Instalação

`scripts/install_wsl2.sh` verificará Ubuntu/WSL2, instalará compilador, bibliotecas gráficas, Python, FFmpeg e ferramentas de build, baixará versões fixadas de OMNeT++, INET e FLoRa, compilará cada dependência e gerará um arquivo de ambiente. O script será idempotente e interromperá com mensagem clara quando precisar de confirmação, espaço em disco ou pacote indisponível.

### Simulação

Os módulos principais serão:

- `MeshNode`: inicialização aleatória, descoberta de vizinhos, geração e recepção de mensagens;
- `MeshRouting`: seleção do próximo salto, prevenção de loops, TTL e retransmissões;
- `MeshGateway`: destino observável e coletor de métricas;
- `MeshEventLogger`: gravação de eventos estruturados;
- configuração NED/INI: topologia, rádio, propagação, AU915 e parâmetros vindos da GUI.

Os nodos permanecerão estáticos. A ativação será agendada individualmente com uma distribuição uniforme no intervalo informado. Mensagens de aplicação serão geradas apenas por nodos ativos e terão identificador único, origem, destino, TTL e payload.

### IDE Python

A GUI usará Tkinter, evitando uma dependência gráfica adicional. Campos obrigatórios:

- quantidade de nodos;
- lado da área em metros;
- ativação mínima e máxima em segundos;
- tempo máximo simulado em segundos;
- semente aleatória;
- diretório de saída.

Também exibirá o comando executado, o progresso, erros de validação, o caminho dos logs e o caminho do vídeo. A execução ocorrerá em subprocesso para não bloquear a janela.

### Renderização

O renderizador consumirá `events.jsonl`, sem depender de parsing frágil do texto do OMNeT++. Cada evento produzirá uma cena com:

- mapa da área;
- posições e estado dos nodos;
- enlaces ativos ou rota atual;
- origem, destino e salto da mensagem;
- instante simulado;
- tipo do evento e dados de rádio relevantes.

Eventos muito próximos no tempo continuam sendo cenas distintas. Cada cena será mantida por `300 ms`. O FFmpeg fará a codificação para MPEG; o renderizador também produzirá um índice de eventos para auditoria.

## Contrato de eventos

Cada linha do log será um objeto JSON com campos comuns:

```json
{
  "time_s": 12.4,
  "event": "PACKET_FORWARDED",
  "node_id": "node[3]",
  "message_id": "msg-000001",
  "source_id": "node[7]",
  "destination_id": "gateway",
  "next_hop_id": "node[3]",
  "hop": 2,
  "ttl": 8,
  "position_m": {"x": 412.0, "y": 671.0},
  "frequency_hz": 915200000,
  "bandwidth_hz": 125000,
  "spreading_factor": 9,
  "tx_power_dbm": 14.0,
  "payload_bytes": 24,
  "status": "accepted"
}
```

Eventos mínimos: `SIMULATION_STARTED`, `NODE_ACTIVATED`, `NEIGHBOR_DISCOVERED`, `MESSAGE_CREATED`, `TRANSMISSION_STARTED`, `PACKET_RECEIVED`, `PACKET_FORWARDED`, `PACKET_DELIVERED`, `PACKET_DROPPED`, `RETRANSMISSION_SCHEDULED` e `SIMULATION_FINISHED`.

Os logs também registrarão motivo de descarte, RSSI, SNR, colisão, rota selecionada e latência quando esses valores estiverem disponíveis no modelo de rádio.

## Tratamento de erros

A GUI validará inteiros positivos, área maior que zero, intervalos ordenados e duração suficiente para a ativação máxima. Falhas de instalação, compilação ou execução serão preservadas em `run.log` e mostradas na interface. Se não houver eventos válidos, o vídeo não será criado e a mensagem explicará a causa. O processo será cancelável sem apagar resultados anteriores.

## Testes e critérios de aceite

1. O script de instalação pode ser executado novamente sem corromper o ambiente.
2. Uma simulação mínima gera saída com início/fim e pelo menos um evento de ativação.
3. Nenhum nodo é ativado antes do mínimo ou depois do máximo configurado.
4. Com a mesma semente e parâmetros, posições e tempos de ativação são reproduzíveis.
5. O log contém origem, destino, salto, tempo, posição e parâmetros de rádio dos eventos de pacote.
6. A GUI rejeita parâmetros inválidos e executa o cenário válido.
7. O renderizador gera um MPEG reproduzível, com uma cena por evento e `300 ms` por cena.
8. O relatório resume mensagens criadas, entregues, perdidas, saltos, latência, RSSI/SNR e taxa de entrega.

## Fora do escopo inicial

Mobilidade, bateria, segurança criptográfica, ADR completo, confirmação LoRaWAN, múltiplos gateways, interferência externa calibrada e uma implementação certificada de regulamentação AU915 não farão parte da primeira versão. A estrutura deixará pontos de extensão para esses recursos.
