# 0005 — Transport real (HTTP/MCP) · spec.md

## O quê

Substituir o `StubTransport` por um `MCPTransport` real que conecta ao SpaceMolt
via `streamablehttp_client` e implementa o protocolo MCP completo.

## Porquê

Hoje o gateway só funciona com o `StubTransport`, que devolve respostas de
mentira. Todos os proxies e skills são registrados corretamente, mas nenhuma
chamada chega de fato ao SpaceMolt. Sem o transport real, o gateway não serve
para nada em produção.

O antigo projeto (`D:\Projects\SpaceMolt\agent\core\mcp_client.py`) já resolveu
esse problema com `streamablehttp_client` + `ClientSession`. A feature 0005
traz essa solução para o gateway, adaptada à interface `MCPTransport` já
definida em `app/game_client.py`.

## Comportamento esperado

### Startup

1. `build_client()` em `server.py` lê `SPACEMOLT_SESSION_ID` e `SPACEMOLT_URL`
   do ambiente.
2. Se `SPACEMOLT_URL` estiver definida (modo real), cria `StreamableHTTPTransport`.
3. Se não (modo dev/CI), continua com `StubTransport`.
4. O transport real abre a conexão MCP (`streamablehttp_client`) e chama
   `session.initialize()` durante o lifespan.
5. `list_tools()` faz `session.list_tools()` e converte o resultado para
   `list[ToolSchema]` (o formato interno do gateway).
6. Ao encerrar o lifespan, a conexão é fechada (AsyncExitStack).

### Durante uma chamada

1. `call_tool(tool_name, arguments)` chama `session.call_tool(tool_name, arguments)`.
2. Extrai o texto de `result.content` (bloco `TextContent`).
3. Tenta fazer `json.loads`. Se falhar, devolve `{"result": text}`.
4. Se o JSON contém `{"error": {...}}`, levanta `SpaceMoltError(code, message)`.
5. Aplica throttle mínimo de 300 ms entre chamadas de ação (mesmo limite do
   projeto antigo) para evitar rate-limit do SpaceMolt.
6. Em caso de 429, retry com backoff: 15 s, 30 s, 60 s.

## Regras

- O `GameClient` **não muda** — ele só conhece a interface `MCPTransport`.
  Todo o comportamento real fica no `StreamableHTTPTransport`.
- O `StubTransport` continua existindo e passando nos testes — é o default
  quando `SPACEMOLT_URL` não está definida.
- `session_id` é injetado pelo `GameClient`, não pelo transport.
- O transport **não** faz login — a autenticação é responsabilidade externa.
  O `session_id` já deve estar disponível via variável de ambiente.
- Erros de rede são propagados como exceções (não engolidos silenciosamente).

## Variáveis de ambiente

| Variável | Obrigatória? | Descrição |
|---|---|---|
| `SPACEMOLT_URL` | Não | URL do MCP do SpaceMolt. Se ausente, usa StubTransport. Default: `https://game.spacemolt.com/mcp` quando definida sem valor |
| `SPACEMOLT_SESSION_ID` | Sim (modo real) | Session id da conta. Injetado em cada chamada pelo GameClient |

## Fora de escopo

- Login/registro dentro do gateway — o operador obtém o `session_id` externamente.
- Reconexão automática se a sessão expirar (tratado em feature futura).
- Pool de conexões ou múltiplos transports simultâneos.
- Transformação ou validação dos parâmetros além do que o SpaceMolt já faz.

## Pronto quando

- `SPACEMOLT_URL=https://game.spacemolt.com/mcp SPACEMOLT_SESSION_ID=<id> python -m app.server`
  → gateway conecta ao SpaceMolt real, lista os tools reais, proxies funcionam.
- Uma chamada `spacemolt(action="get_status")` via MCP Inspector devolve o
  status real do personagem.
- Os testes existentes continuam passando (usam `StubTransport`).
- A seleção stub vs real é transparente: `build_client()` decide com base
  nas variáveis de ambiente.
