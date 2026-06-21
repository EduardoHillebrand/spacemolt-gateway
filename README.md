# SpaceMolt Gateway

Gateway MCP que fica na frente do SpaceMolt. A LLM so fala com este gateway,
que serve como **porta de entrada unica** para o jogo.

```
   LLM (Claude Code / agente)
          |  (fala so com o gateway)
          v
   +-----------------------+
   |   SpaceMolt Gateway   |
   |  +---------------+    |
   |  | proxy (cru)   |----+--> ferramentas cruas (mine, travel...)
   |  +---------------+    |
   |  +---------------+    |
   |  | skills (alto  |    |    ex: mining_run = minera ate encher,
   |  | nivel)        |    |        volta pra base e vende
   |  +---------------+    |
   +-----------+-----------+
               v
          MCP oficial do SpaceMolt
```

## Por que existe

Sem o gateway, a LLM precisa fazer dezenas de chamadas pequenas pra cada tarefa
e gasta token decidindo coisa obvia. O gateway empacota essas sequencias em
**skills de alto nivel** que ja vem com a logica pronta. A LLM pede "minera e
vende", o gateway faz o resto.

## Como subir

### 1. Instalar dependencias

```bash
python -m venv .venv

# Windows (PowerShell)
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate

pip install -e ".[dev]"
```

### 2. Configurar

Exporte o ID de sessao do SpaceMolt antes de subir:

```bash
# Windows (PowerShell)
$env:SPACEMOLT_SESSION_ID = "seu-session-id-aqui"

# Linux / macOS
export SPACEMOLT_SESSION_ID="seu-session-id-aqui"
```

O session ID vem de `spacemolt_auth` (action=login ou register).
Se a variavel nao estiver definida, o gateway sobe em modo stub.

### 3. Rodar

```bash
python -m app.server
```

O gateway fica ouvindo via **stdio**, o transporte padrao do MCP.
Ao subir, o canal de log WebSocket tambem sobe automaticamente na porta 7788
(ou na porta definida por `DEVLOG_PORT`).

### 4. Conectar

**Claude Desktop** -- adicione em `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "spacemolt-gateway": {
      "command": "python",
      "args": ["-m", "app.server"],
      "cwd": "/caminho/para/spacemolt-gateway",
      "env": {
        "SPACEMOLT_SESSION_ID": "seu-session-id"
      }
    }
  }
}
```

**MCP Inspector** (verificacao rapida):

```bash
npx @modelcontextprotocol/inspector python -m app.server
```

### 5. Verificar

Apos conectar, o gateway lista as ferramentas:

- `get_status` -- estado atual da nave
- `mine` -- extrai recursos no POI atual
- `travel` -- viaja para um POI no sistema atual

Chamada de teste:

```
get_status()
# modo stub  -> "[STUB] spacemolt(action='get_status', session_id='stub-session')"
# modo real  -> dados reais do SpaceMolt
```

## Canal de log ao vivo (devlog)

Quando o gateway sobe, um servidor WebSocket sobe junto na porta **7788**.
Qualquer cliente WebSocket pode assinar um nivel e acompanhar os logs ao vivo.

### Niveis disponiveis

| Assinar | Recebe |
|---------|--------|
| `error` | so error |
| `warning` | warning + error |
| `info` | info + warning + error (tudo) |

### Como conectar

Com `websocat` (instale com `cargo install websocat` ou baixe o binario):

```bash
# ver tudo
websocat "ws://localhost:7788/?level=info"

# so erros
websocat "ws://localhost:7788/?level=error"
```

No navegador (console do DevTools):

```js
const ws = new WebSocket("ws://localhost:7788/?level=info");
ws.onmessage = e => console.log(JSON.parse(e.data));
```

### Formato da mensagem

Cada linha e um JSON com os campos:

```json
{
  "level":   "info",
  "module":  "app.skills.mining.executor",
  "message": "mine_until: volta 3, cargo 42/100",
  "time":    "2026-06-21T12:34:56.789000+00:00"
}
```

### Comportamento

- Conectou depois? Perdeu o que passou. Nao ha historico.
- Sem cliente conectado? Zero overhead -- nenhum dado e guardado.
- Fila cheia? O log mais antigo e descartado. O gateway nunca trava.
- Porta diferente? Defina `DEVLOG_PORT` antes de subir.

## Como este projeto e construido

Spec Driven Development (SDD): a especificacao vem antes do codigo.
Tudo esta em `.specs/`.

Ordem: `spec.md` -> `plan.md` -> `tasks.md` -> branches git.

Comece lendo: `.specs/README.md` e `.specs/constitution.md`.

## Stack

- Python 3.11+
- FastMCP (SDK MCP de Python)
- websockets >= 13 (canal de log)
- Sem nuvem: roda local.

## Estrutura

```
app/
  server.py          # registra as ferramentas e sobe o MCP
  game_client.py     # camada fina que chama o MCP cru do SpaceMolt
  registry.py        # conecta raw tools e skills ao servidor
  transports/
    stub.py          # transport de desenvolvimento (sem conexao real)
  core/
    errors.py        # erros do gateway (PreconditionError)
    devlog/          # canal de log WebSocket ao vivo
      levels.py      # regra de filtro por nivel
      bus.py         # fan-out para assinantes
      handler.py     # logging.Handler nao-bloqueante
      ws_server.py   # servidor WebSocket
      setup.py       # init_dev_logging() -- ponto de entrada
  skills/            # skills de alto nivel -- feature 0002+
tests/
```

## Ferramentas disponíveis

O gateway expõe dois tipos de tool:

### Proxies automáticos (descobertos no boot)

Ao subir, o gateway chama `list_tools()` no transport e registra um proxy para
cada tool descoberto. Toda chamada é logada automaticamente no devlog.

| Tool | Params obrigatórios | Params opcionais |
|------|---------------------|------------------|
| `spacemolt` | `action` | `id`, `quantity`, `price`, `message` |
| `spacemolt_auth` | `action` | `username`, `password`, `registration_code` |
| `spacemolt_market` | `action` | `id`, `quantity`, `price_each`, `order_id` |
| `spacemolt_ship` | `action` | `id`, `slot`, `ship_name` |
| `spacemolt_facility` | `action` | `id`, `item_id`, `quantity` |

O `session_id` é **sempre injetado automaticamente** — não aparece nos params.

### Skills de alto nível

| Tool | O que faz |
|------|-----------|
| `mining_run(home_base?)` | Minera até encher, volta pra base, vende tudo |

### Configuração no Claude Desktop

Configure **apenas o gateway** — não o SpaceMolt diretamente:

```json
{
  "mcpServers": {
    "spacemolt-gateway": {
      "command": "D:\\Projects\\spacemolt-gateway\\.venv\\Scripts\\python.exe",
      "args": ["-m", "app.server"],
      "cwd": "D:\\Projects\\spacemolt-gateway",
      "env": {
        "SPACEMOLT_SESSION_ID": "seu-session-id"
      }
    }
  }
}
```
