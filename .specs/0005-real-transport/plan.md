# 0005 — Transport real · plan.md

## Visão geral do fluxo

```
server.py
  └── build_client()
        ├── SPACEMOLT_URL definida? → StreamableHTTPTransport(url)
        └── não definida?           → StubTransport()

lifespan (server.py)
  └── await client.connect()        ← novo método no GameClient
        └── transport.connect()     ← abre a sessão MCP real
  └── setup_proxy(mcp, client)      ← já existe
  └── register_skills(mcp, client)  ← já existe
  └── yield
  └── await client.disconnect()     ← fecha a sessão MCP

app/transports/streamable_http.py   ← arquivo novo
  ├── StreamableHTTPTransport
  │     ├── connect()    → streamablehttp_client + ClientSession.initialize()
  │     ├── disconnect() → AsyncExitStack.aclose()
  │     ├── call_tool()  → session.call_tool() + parse + throttle + retry
  │     └── list_tools() → session.list_tools() → list[ToolSchema]
  └── SpaceMoltError(code, message)
```

## Arquivos alterados / criados

### `app/transports/streamable_http.py` (novo)

Único arquivo novo de produção. Responsabilidades:

```python
class SpaceMoltError(Exception):
    """Erro semântico retornado pelo jogo (code + message)."""

class StreamableHTTPTransport:
    """Transport real via streamablehttp_client + ClientSession."""

    def __init__(self, url: str) -> None: ...

    async def connect(self) -> None:
        # Abre streamablehttp_client(url), ClientSession,
        # chama session.initialize()

    async def disconnect(self) -> None:
        # AsyncExitStack.aclose()

    async def call_tool(self, tool_name: str, arguments: dict) -> Any:
        # throttle 300 ms, retry 429 (15/30/60 s),
        # extrai text de result.content,
        # json.loads ou {"result": text},
        # levanta SpaceMoltError se {"error": ...}

    async def list_tools(self) -> list[ToolSchema]:
        # session.list_tools() → converte Tool MCP → ToolSchema interno
```

### `app/game_client.py` (alterar)

Adicionar métodos `connect()` e `disconnect()` que delegam ao transport
**somente se** o transport implementar esses métodos (duck typing / hasattr).
O `StubTransport` não precisa implementar — `hasattr` retorna False e
o GameClient não chama.

```python
async def connect(self) -> None:
    if hasattr(self._transport, "connect"):
        await self._transport.connect()

async def disconnect(self) -> None:
    if hasattr(self._transport, "disconnect"):
        await self._transport.disconnect()
```

Alternativamente, adicionar `connect`/`disconnect` no protocolo `MCPTransport`
com implementação padrão vazia (passa a ser classe abstrata em vez de Protocol).
**Decisão**: usar `hasattr` para não forçar o `StubTransport` a mudar.

### `app/server.py` (alterar)

No lifespan, chamar `connect` antes e `disconnect` depois:

```python
@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[None]:
    await init_dev_logging(port=_DEV_LOG_PORT)
    if _client is not None:
        await _client.connect()          # ← novo
        await setup_proxy(mcp, _client)
        register_skills(mcp, _client)
    yield
    if _client is not None:
        await _client.disconnect()       # ← novo
```

`build_client()` atualizado para detectar `SPACEMOLT_URL`:

```python
def build_client() -> GameClient:
    session_id = os.environ.get("SPACEMOLT_SESSION_ID", "stub-session")
    url = os.environ.get("SPACEMOLT_URL")
    if url:
        from app.transports.streamable_http import StreamableHTTPTransport
        transport = StreamableHTTPTransport(url)
    else:
        transport = StubTransport()
    return GameClient(transport=transport, session_id=session_id)
```

### `app/transports/__init__.py` (sem mudança)

### Dependência nova

`mcp[client]` (ou `mcp` com extras que incluem `streamable_http`).
Verificar se já está no `pyproject.toml`. Se não, adicionar.

## Conversão `Tool MCP → ToolSchema`

O `session.list_tools()` retorna objetos `mcp.types.Tool`:

```
Tool(
    name="spacemolt",
    description="...",
    inputSchema={
        "type": "object",
        "properties": {
            "action":   {"type": "string",  "description": "..."},
            "id":       {"type": "string"},
            "quantity": {"type": "integer"},
        },
        "required": ["action"]
    }
)
```

Conversão:

```python
def _tool_to_schema(tool: mcp.types.Tool) -> ToolSchema:
    props = tool.inputSchema.get("properties", {})
    required = set(tool.inputSchema.get("required", []))
    params = [
        ParamSchema(
            name=name,
            type=prop.get("type", "string"),
            required=name in required,
            description=prop.get("description", ""),
        )
        for name, prop in props.items()
        if name != "session_id"   # session_id é injetado, não exposto
    ]
    return ToolSchema(
        name=tool.name,
        description=tool.description or "",
        params=params,
    )
```

## Throttle e retry

Igual ao projeto antigo:

- `_MIN_CALL_GAP_S = 0.30` — espera para preencher o gap desde a última chamada.
- Em 429: retry com `_RETRY_WAITS = (15, 30, 60)`. Na 4ª falha, re-levanta.
- O throttle e retry ficam dentro de `call_tool`, não no `GameClient`.

## Testes

`tests/transports/test_streamable_http.py` (novo):

- `test_list_tools_converts_mcp_schema`: injeta `session` fake com
  `list_tools()` que retorna objetos `Tool`. Confirma conversão para
  `list[ToolSchema]` correta (tipos, required, sem session_id).
- `test_call_tool_parses_text_content`: `session.call_tool` retorna
  `[TextContent(text='{"ok":true}')]`. Confirma retorno `{"ok": True}`.
- `test_call_tool_parses_plain_text`: resposta não é JSON →
  retorna `{"result": "texto cru"}`.
- `test_call_tool_raises_spacemolt_error`: resposta contém `{"error":{...}}` →
  levanta `SpaceMoltError`.
- `test_throttle_sleeps_between_calls`: chama `call_tool` duas vezes em
  sequência rápida. Confirma que `asyncio.sleep` foi chamado com valor > 0.
- `test_retry_on_429`: `session.call_tool` levanta exceção com "429" na
  1ª chamada, sucesso na 2ª. Confirma que a chamada é retentada.

**Nota**: os testes acima injetam um `session` falso diretamente no transport
(sem precisar de conexão real). `connect()` / `disconnect()` ficam de fora
dos testes unitários — são verificados no manual check.

## Testes existentes (não mudam)

- `tests/test_server_smoke.py` — usa `mcp` sem lifespan, continua ok.
- `tests/test_registry.py` — usa `StubTransport`, continua ok.
- `tests/core/test_proxy.py` — usa `StubTransport`, continua ok.
