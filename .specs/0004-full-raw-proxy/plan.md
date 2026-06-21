# 0004 — Proxy dinâmico · plan.md

## Visão geral do fluxo

```
server.py (lifespan)
  └── setup_proxy(mcp, client)          ← novo, em app/core/proxy.py
        └── client.list_tools()         ← novo método no GameClient
              └── transport.list_tools() ← novo método no Transport/StubTransport
        └── register_proxies(mcp, tools, client)
              └── _make_proxy(tool) → fn async
              └── mcp.add_tool(fn, name, description, params)
```

## Arquivos alterados / criados

### `app/transports/stub.py` (alterar)

Adicionar `list_tools() -> list[ToolSchema]`.
Devolve uma lista hardcoded com os tools que o stub simula
(usado em testes para não precisar de SpaceMolt real).

### `app/game_client.py` (alterar)

Adicionar `list_tools() -> list[ToolSchema]` que delega ao transport.

### `app/core/proxy.py` (novo)

Único arquivo novo de produção. Responsabilidades:

```python
@dataclass
class ToolSchema:
    name: str
    description: str
    params: list[ParamSchema]   # nome, tipo, required, description

@dataclass
class ParamSchema:
    name: str
    type: str          # "string", "integer", "boolean"
    required: bool
    description: str

async def setup_proxy(mcp: FastMCP, client: GameClient) -> None:
    """Descobre tools e registra proxies. Chamado no lifespan do server."""
    ...

def _make_proxy(client: GameClient, tool_name: str) -> Callable:
    """Cria a função proxy para um tool específico."""
    ...
```

`setup_proxy` não precisa saber os nomes dos tools — só itera o que o
transport devolver.

### `app/registry.py` (alterar)

Remover os 3 tools hardcoded (`get_status`, `mine`, `travel`) de
`register_raw_tools`. O proxy dinâmico os substitui.

Manter `register_skills` intacto.

### `app/server.py` (alterar)

No lifespan, chamar `setup_proxy` depois de `init_dev_logging`:

```python
@asynccontextmanager
async def lifespan(server):
    await init_dev_logging(port=_DEV_LOG_PORT)
    await setup_proxy(mcp, client)
    yield
```

## Injeção de `session_id`

O `session_id` vem de `os.environ["SPACEMOLT_SESSION_ID"]` (já existe no
`GameClient`). O proxy injeta antes de repassar — a LLM nunca precisa
informar.

## Compatibilidade com o StubTransport

O `StubTransport.list_tools()` devolve uma lista de 3–5 tools fictícios com
schemas simples. Isso permite que os testes existentes continuem passando sem
conexão real.

## Como o FastMCP suporta registro dinâmico

`FastMCP` expõe `mcp.add_tool(fn, name, description)`. Para incluir o schema
de parâmetros, criamos a função proxy com assinatura dinâmica usando
`inspect` + `types.FunctionType`, ou usamos a API de baixo nível do MCP SDK
(`mcp._tool_manager.add_tool`).

**Decisão de implementação**: começar com a abordagem mais simples que funciona.
Se `mcp.add_tool` aceitar um schema explícito, usar isso. Senão, criar
funções com assinatura dinâmica via `exec` ou `functools`.
A decisão exata fica para o passo de implementação, depois de verificar a API
disponível.

## Testes

`tests/core/test_proxy.py`:

- `test_setup_proxy_registers_stub_tools`: chama `setup_proxy` com um
  FastMCP de teste e o StubTransport. Confirma que os tools aparecem.
- `test_proxy_injects_session_id`: chama um proxy registrado e confirma
  que `session_id` foi injetado na chamada ao transport.
- `test_proxy_logs_call`: confirma que o log INFO aparece.
- `test_setup_proxy_fallback_on_error`: simula falha em `list_tools` e
  confirma que o gateway sobe assim mesmo.
