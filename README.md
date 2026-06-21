# SpaceMolt Gateway

Gateway MCP que fica na frente do SpaceMolt. A LLM só fala com este gateway,
que serve como **porta de entrada única** para o jogo.

```
   LLM (Claude Code / agente)
          │  (fala só com o gateway)
          ▼
   ┌─────────────────────┐
   │   SpaceMolt Gateway │
   │  ┌───────────────┐  │
   │  │ proxy (cru)   │──┼──► ferramentas cruas do SpaceMolt (mine, travel...)
   │  └───────────────┘  │
   │  ┌───────────────┐  │
   │  │ skills (alto  │  │   ex: mining_run = minera até encher,
   │  │ nível)        │  │       volta pra base e vende
   │  └───────────────┘  │
   └─────────┬───────────┘
             ▼
        MCP oficial do SpaceMolt
```

## Por que existe

Sem o gateway, a LLM precisa fazer dezenas de chamadas pequenas pra cada tarefa
e gasta token decidindo coisa óbvia. O gateway empacota essas sequências em
**skills de alto nível** que já vêm com a lógica pronta. A LLM pede "minera e
vende", o gateway faz o resto.

## Como subir

### 1. Instalar dependências

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -e ".[dev]"
```

### 2. Configurar

Antes de subir com uma sessão real do SpaceMolt, exporte o ID de sessão:

```bash
# Windows (PowerShell)
$env:SPACEMOLT_SESSION_ID = "seu-session-id-aqui"

# Linux / macOS
export SPACEMOLT_SESSION_ID="seu-session-id-aqui"
```

O session ID vem de `spacemolt_auth` (action=login ou register).
Se a variável não estiver definida, o gateway sobe em modo stub — útil para
inspecionar a estrutura das ferramentas sem se conectar ao jogo.

### 3. Rodar

```bash
python -m app.server
```

O gateway fica ouvindo via **stdio**, o transporte padrão do MCP.

### 4. Conectar

**Claude Desktop** — adicione em `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "spacemolt-gateway": {
      "command": "python",
      "args": ["-m", "app.server"],
      "cwd": "/cami