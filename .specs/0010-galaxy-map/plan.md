# 0010 — Galaxy Map · plan.md

## Visão geral do fluxo

```
server.py (lifespan)
  └── galaxy_map_service.start(mcp)   ← novo, arranca task de background
        ├── _http_load_stations()      ← GET /api/stations (uma request, todas as estações)
        └── asyncio.create_task(
              _http_scan_all_systems() ← varre /api/map/system/{id} um por um, loop eterno
            )

tool "galaxy_info" (registrada no FastMCP)
  └── query_galaxy(query: str) → str
        └── lê data/galaxy_map.json (cache local) e formata resposta
```

## Estrutura de arquivos

```
app/core/galaxy/
  __init__.py
  mapper.py      # GalaxyMapper: HTTP scanner + disk cache
  query.py       # query_galaxy(query) → str  (lê o cache, formata resposta)
  tool.py        # registra galaxy_info no FastMCP

data/
  galaxy_map.json   # criado/atualizado pelo mapper em runtime (gitignored)

tests/core/galaxy/
  test_query.py     # testa query_galaxy com cache fake injetado
  test_mapper.py    # testa _parse_station_response, _parse_system_response
```

## Schema do cache (`galaxy_map.json`)

```json
{
  "updated_at": "2025-06-01T12:00:00",
  "stations_loaded": true,
  "stations_loaded_at": "2025-06-01T12:00:05",
  "total_systems": 505,
  "scanned_systems": 312,
  "systems": {
    "sol": {
      "id": "abc123",
      "name": "Sol",
      "empire": "solarian",
      "police_level": 90,
      "security_status": "maximum",
      "pois": [
        {"id": "confederacy_central_command", "name": "...", "type": "station",
         "has_base": true, "minable": false},
        {"id": "sol_belt_1", "name": "...", "type": "asteroid_belt",
         "has_base": false, "minable": true}
      ],
      "has_base": true,
      "has_refuel": true,
      "has_repair": true,
      "has_shipyard": false,
      "has_market": true,
      "connections": ["sirius", "alpha_centauri"],
      "scanned_at": "2025-06-01T12:05:00",
      "source": "http_scan"
    }
  }
}
```

`source` indica a origem dos dados:
- `"stations_api"` — dados básicos do `/api/stations` (has_base e serviços, sem POIs)
- `"http_scan"` — dados completos do `/api/map/system/{id}` (POIs, police_level)
- `"basic_only"` — apenas nome e id, ainda não escaneado

## `mapper.py` — `GalaxyMapper`

```python
_STATIONS_URL = "https://game.spacemolt.com/api/stations"
_SYSTEM_URL   = "https://game.spacemolt.com/api/map/system/{system_id}"
_SCAN_DELAY_MIN = 1.0   # segundos
_SCAN_DELAY_MAX = 3.0
_RESCAN_WAIT    = 300   # 5 min entre passagens completas

class GalaxyMapper:
    def __init__(self, data_path: Path): ...

    async def start(self, mcp: FastMCP) -> None:
        """Carrega cache existente, registra a tool e inicia tasks."""

    async def _http_get(self, url: str) -> dict:
        """GET assíncrono sem autenticação (httpx.AsyncClient)."""

    async def _load_stations(self) -> None:
        """Chama /api/stations, atualiza cache, persiste."""

    async def _scan_all_systems_bg(self) -> None:
        """Loop eterno: varre /api/map/system/{id} para cada sistema."""

    def _load_cache(self) -> dict:
        """Lê galaxy_map.json do disco. Retorna {} se não existir."""

    def _write_cache(self, cache: dict) -> None:
        """Serializa para JSON e salva atomicamente."""

    def _parse_station_response(self, data: dict) -> list[dict]:
        """Extrai lista de estações da resposta de /api/stations."""

    def _parse_system_response(self, data: dict, sys_id: str, sys_name: str) -> dict:
        """Extrai campos relevantes da resposta de /api/map/system/{id}."""
```

**Nota sobre dependência HTTP:** usar `httpx` (já é dependência transitiva do
`mcp` SDK) em vez de `requests` — funciona com `asyncio.to_thread` ou nativamente
com `httpx.AsyncClient`. Se não estiver disponível, adicionar ao `pyproject.toml`.

## `query.py` — `query_galaxy`

Função pura que recebe a string de query e o cache como dict:

```python
def query_galaxy(query: str, cache: dict) -> str:
    """
    Parse de query e formatação da resposta.
    Nunca faz chamada HTTP — só lê o cache.
    """
```

Formatos de query e comportamento:

| Query | Parse | Retorno |
|---|---|---|
| `"system:<nome>"` | lookup `cache["systems"][nome.lower()]` | POIs, serviços, polícia |
| `"station:<nome>"` | idem | só serviços da estação |
| `"nearest_fuel:<nome>"` | BFS sobre `connections` no cache | nome + distância em hops |
| `"systems_with:<serviço>"` | filtra `cache["systems"]` por `has_refuel` etc. | lista de nomes |
| `"empire:<nome>"` | filtra por `empire` | lista de nomes |
| `"map_status"` | campos de metadados | resumo em texto |

**BFS para `nearest_fuel`**: percorre o grafo de conexões usando os dados já no
cache. Se um sistema não estiver no cache ainda, ignora-o no BFS (não chama HTTP).
Teto de profundidade: 5 hops (evita BFS infinito em grafos grandes).

## `tool.py` — registro no FastMCP

```python
def register(mcp: FastMCP, mapper: GalaxyMapper) -> None:
    @mcp.tool(description=(
        "Query the galaxy map built from the SpaceMolt public API. "
        "Queries: system:<name>, station:<name>, nearest_fuel:<system>, "
        "systems_with:<service>, empire:<name>, map_status. "
        "Returns cached data — no game action, no rate limit cost."
    ))
    async def galaxy_info(query: str) -> str:
        cache = mapper._load_cache()
        return query_galaxy(query, cache)
```

## Integração com `server.py`

```python
# server.py

from app.core.galaxy.mapper import GalaxyMapper

_galaxy_mapper: GalaxyMapper | None = None

@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[None]:
    await init_dev_logging(port=_DEV_LOG_PORT)
    if _client is not None:
        await _client.connect()
        await setup_proxy(mcp, _client)
        register_skills(mcp, _client)
    if _galaxy_mapper is not None:
        await _galaxy_mapper.start(mcp)   # registra tool + inicia tasks
    yield
    if _client is not None:
        await _client.disconnect()

def main() -> None:
    global _client, _galaxy_mapper
    _client = build_client()
    _galaxy_mapper = GalaxyMapper(data_path=Path("data/galaxy_map.json"))
    mcp.run(transport="stdio")
```

## `.gitignore`

Adicionar `data/` ao `.gitignore` — o `galaxy_map.json` é gerado em runtime
e não pertence ao repositório.

## Testes

`tests/core/galaxy/test_query.py`:
- `test_system_query_found` — cache com "sol", query `"system:sol"` → contém POIs e serviços.
- `test_system_query_not_found` — sistema ausente → resposta indica que não foi escaneado ainda.
- `test_system_query_case_insensitive` — `"system:Sol"` e `"system:sol"` retornam o mesmo.
- `test_nearest_fuel_direct_neighbor` — sistema com vizinho imediato com refuel → 1 hop.
- `test_nearest_fuel_two_hops` — vizinhos sem refuel, mas vizinho-de-vizinho tem → 2 hops.
- `test_nearest_fuel_not_found` — nenhum sistema com refuel no raio de 5 hops → aviso claro.
- `test_systems_with_service` — filtra por `"systems_with:shipyard"` → lista correta.
- `test_empire_query` — filtra por `"empire:solarian"` → lista correta.
- `test_map_status` — cache com metadados → retorna `scanned_systems/total_systems`.

`tests/core/galaxy/test_mapper.py`:
- `test_parse_station_response` — payload fake de `/api/stations` → lista de sistemas
  com `has_base=True` e serviços corretos.
- `test_parse_system_response` — payload fake de `/api/map/system/{id}` → dict com
  `pois`, `police_level`, `has_base`.
- `test_write_and_load_cache` — salva, recarrega, compara.

**Testes NÃO cobertos aqui** (precisariam de HTTP real):
- `_load_stations` e `_scan_all_systems_bg` — verificados no manual check.
