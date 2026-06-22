# 0005 — Transport real · tasks.md

- [ ] **020_http-transport** — Criar `app/transports/streamable_http.py` com
      `StreamableHTTPTransport` e `SpaceMoltError`. Implementar `connect`,
      `disconnect`, `call_tool` (throttle + retry + parse), `list_tools`
      (conversão `Tool MCP → ToolSchema`). Verificar / adicionar dependência
      `mcp[client]` no `pyproject.toml`. Testes unitários em
      `tests/transports/test_streamable_http.py` (session fake injetado,
      sem conexão real): conversão de schema, parse text/json/error, throttle,
      retry 429. Todos os testes existentes continuam passando.

- [ ] **021_client-connect** — Adicionar `connect()` e `disconnect()` no
      `GameClient` (duck typing via `hasattr`). Atualizar `server.py` lifespan
      para chamar `_client.connect()` antes e `_client.disconnect()` depois.
      Atualizar `build_client()` para detectar `SPACEMOLT_URL` e instanciar
      `StreamableHTTPTransport` ou `StubTransport`. Testes: `GameClient.connect`
      delega ao transport quando o método existe; quando não existe, não levanta.
      Todos os testes existentes continuam passando.

- [ ] **022_transport-manual-check** — Subir o gateway com
      `SPACEMOLT_URL=https://game.spacemolt.com/mcp` e `SPACEMOLT_SESSION_ID`
      real. Confirmar no MCP Inspector que: (a) todos os tools do SpaceMolt
      aparecem na lista, (b) `spacemolt(action="get_status")` devolve o
      status real, (c) o devlog mostra as chamadas. Anotar quaisquer diferenças
      entre os tools listados aqui e os do `StubTransport`; ajustar o stub se
      necessário.
