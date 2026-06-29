# 0005-B — Transport sob demanda · plan.md

## Mudança única: `app/transports/streamable_http.py`

### `connect()` e `disconnect()` → no-op

```python
async def connect(self) -> None:
    """No-op: conexão aberta por chamada, não de forma persistente."""
    log.debug("StreamableHTTPTransport: on-demand mode, no persistent connection")

async def disconnect(self) -> None:
    """No-op: não há sessão persistente para fechar."""
    pass
```

Remove: `self._session`, `self._exit_stack` como atributos de instância.

### `call_tool()` → abre/fecha sessão por chamada

```python
async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
    # Throttle (mantido)
    now = time.monotonic()
    gap = now - self._last_call_t
    if gap < _MIN_CALL_GAP_S:
        await asyncio.sleep(_MIN_CALL_GAP_S - gap)

    # Sessão sob demanda
    async with AsyncExitStack() as stack:
        transport = await stack.enter_async_context(streamablehttp_client(self._url))
        read, write, _ = transport
        session = await stack.enter_async_context(ClientSession(read, write))
        await session.initialize()

        # Retry de 429 (mantido)
        for attempt in range(len(_RETRY_WAITS) + 1):
            try:
                raw = await session.call_tool(tool_name, arguments)
                self._last_call_t = time.monotonic()
                break
            except Exception as exc:
                ...  # lógica de retry existente

    return _parse_content(raw)
```

### `list_tools()` → abre/fecha sessão por chamada

```python
async def list_tools(self) -> list[ToolSchema]:
    async with AsyncExitStack() as stack:
        transport = await stack.enter_async_context(streamablehttp_client(self._url))
        read, write, _ = transport
        session = await stack.enter_async_context(ClientSession(read, write))
        await session.initialize()
        response = await session.list_tools()
    return [_tool_to_schema(t) for t in response.tools]
```

### `__init__()` → remove atributos de sessão

Mantém apenas: `self._url`, `self._last_call_t`.
Remove: `self._session`, `self._exit_stack`.

## Testes

Testes existentes em `tests/transports/test_streamable_http.py` já injetam
uma sessão falsa diretamente — precisarão ser adaptados para a nova estrutura
(injetar via patch do `streamablehttp_client` e `ClientSession`).

## Branch

`033_ondemand-transport`
