# 0005-B — Transport sob demanda · spec.md

## O quê

Substituir a conexão MCP persistente do `StreamableHTTPTransport` por uma
conexão **sob demanda**: abrir sessão, fazer a chamada, fechar sessão.

## Porquê

A implementação atual (`connect()` abre uma sessão permanente) mantém um
GET SSE stream aberto o tempo todo. O SpaceMolt fecha esse stream rapidamente
e a biblioteca MCP reconecta em loop — gerando dezenas de mensagens
`GET stream disconnected, reconnecting in 1000ms...` por segundo mesmo quando
o gateway está completamente ocioso.

Efeitos concretos:
- CPU e rede desperdiçados: o gateway bate no SpaceMolt várias vezes/segundo
  sem nenhuma chamada pendente.
- Risco de rate-limit por excesso de GETs ociosos.
- Logs poluídos, dificultando leitura de eventos reais.

## Comportamento esperado

### Lifecycle

- `connect()` → **no-op** (apenas valida que a URL foi configurada, sem abrir conexão).
- `disconnect()` → **no-op**.
- A interface `MCPTransport` continua sendo respeitada — quem chama
  `client.connect()` / `client.disconnect()` não precisa saber que são no-ops.

### Durante uma chamada (`call_tool` / `list_tools`)

1. Abre um `AsyncExitStack` local.
2. Entra no contexto `streamablehttp_client(url)`.
3. Cria e inicializa um `ClientSession`.
4. Faz a chamada (`call_tool` ou `list_tools`).
5. Fecha o `AsyncExitStack` (stack local, não compartilhado).

Cada chamada é completamente independente. Nenhum estado de sessão persiste
entre chamadas.

### Throttle e retry

Permanecem iguais — o `_last_call_t` continua no objeto e o throttle de
300 ms continua sendo aplicado antes de abrir a sessão.

## Regras

- O `GameClient` **não muda** — a mudança é transparente para quem usa o transport.
- O throttle de 300 ms permanece: `_last_call_t` é atributo de instância.
- O retry de 429 permanece: continua dentro de `call_tool`.
- O overhead por chamada é aceito: uma inicialização MCP extra (~50 ms) é
  desprezível comparado ao tempo de jogo.
- Nenhum stream ocioso → nenhum loop de reconexão → logs limpos.

## Fora de escopo

- Pool de conexões ou sessão reutilizável.
- Conexão persistente opcional via flag.

## Pronto quando

- Gateway rodando sem nenhuma chamada ativa → zero mensagens de reconexão no log.
- `call_tool` e `list_tools` continuam funcionando normalmente.
- Todos os testes existentes continuam passando.
