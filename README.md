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

## Como este projeto e construido

Spec Driven Development (SDD): a especificacao vem antes do codigo.
Tudo esta em `.specs/`.

Ordem: `spec.md` -> `plan.md` -> `tasks.md` -> branches git.

Comece lendo: `.specs/README.md` e `.specs/constitution.md`.

## Stack

- Python 3.11+
- FastMCP (SDK MCP de Python)
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
  skills/            # skills de alto nivel -- feature 0002+
tests/
```
