# 0007 — Skill de Navegação · plan.md

## Estrutura

Novo módulo isolado, no mesmo padrão da mineração:

```
app/skills/navigation/
  __init__.py
  schema.py      # tipos: NavState, Hop, Plan, NavResult
  planner.py     # build_navigation_plan(state, destination) -> Plan   (função pura)
  executor.py    # run_navigation_plan(plan, game_client) -> NavResult
  tool.py        # registra navigate_to no gateway; cola planner + executor
tests/skills/navigation/
  test_planner.py
  test_executor.py
```

Não importa nada de `app/skills/mining/` nem é importado por ela — se algo
for compartilhado no futuro (ex: leitura de fuel do status), sobe pra
`app/core/`, igual à regra da constituição.

## Schema (`schema.py`)

```python
@dataclass
class NavState:
    current_system: str
    current_poi: str | None
    is_docked: bool
    fuel_current: int
    fuel_capacity: int
    target_system: str
    target_poi: str | None          # None = só quer chegar no sistema

@dataclass
class Hop:
    op: str                  # "undock" | "travel" | "jump" | "dock" | "refuel"
    target: str | None = None

@dataclass
class Plan:
    hops: list[Hop]
    ok: bool = True
    failure_reason: str | None = None

@dataclass
class NavResult:
    ok: bool
    jumps: int = 0
    refuel_stops: int = 0
    final_system: str = ""
    final_poi: str = ""
    failure_reason: str | None = None
```

## Planner (`build_navigation_plan`)

Função pura: recebe `NavState` + destino já separado em `target_system`/
`target_poi`, devolve um `Plan` com a sequência de hops conhecida **até
onde dá para saber sem chamar o jogo de novo**:

- Já no destino exato → `Plan(hops=[])` (o executor detecta "nada a fazer").
- Destino é POI do sistema atual → `[undock?, travel(poi)]`.
- Destino é outro sistema → o planner **não** resolve a rota completa
  sozinho (isso depende de `find_route`, uma chamada ao jogo) — devolve um
  plano com um único hop simbólico `Hop(op="route_to", target=target_system)`
  que diz ao executor "calcule e siga a rota a partir daqui". Mantém o
  planner puro: ele decide a **estratégia** (POI local vs rota
  multi-sistema), não a rota em si.

Pré-condição verificada aqui: destino vazio/inválido → `Plan.failed(...)`.

## Executor (`run_navigation_plan`)

Quem realmente sabe pilotar a rota multi-sistema:

```
para cada hop do plano:
  "undock"/"dock"/"travel"/"jump" → chamada direta ao game_client
  "route_to":
    loop (até chegar ou ser interrompido):
      perguntar find_route(target_system) ao jogo
      next_hop = primeiro salto da rota retornada
      se fuel projetado para o próximo salto < margem de segurança:
        se há base no sistema atual → dock + refuel (refuel_stops += 1) + undock
        senão → parar, ok=False, failure_reason="sem fuel e sem base para reabastecer"
      else:
        undock (se docado) + jump(next_hop); jumps += 1
      se next_hop == target_system → sair do loop de jump (chegou no sistema)
    se target_poi foi pedido → travel(target_poi) ao chegar
```

Teto de iterações no loop de jump, igual ao `_MINE_LOOP_MAX` da mineração,
para nunca rodar pra sempre se a rota for instável.

## tool.py

- Lê `get_status` (sistema atual, POI, docado, fuel) e monta `NavState`.
- Recebe `destination: str` no formato `"Sistema"` ou `"Sistema/poi_id"`
  (mesmo formato usado pelo agente anterior), faz o split antes de chamar
  o planner.
- Chama planner, depois executor, formata o resumo (`jumps`, `refuel_stops`,
  onde parou, se chegou ou foi interrompida).

## Testes (sem tocar no jogo de verdade)

- `test_planner`: já no destino → plano vazio; POI do sistema atual →
  hops corretos; sistema diferente → plano com `route_to`; destino vazio →
  `Plan.failed`.
- `test_executor` com `FakeGameClient` que simula `find_route` devolvendo
  uma rota fixa e fuel caindo a cada jump:
  - rota direta sem reabastecimento → `jumps` corresponde ao número de
    saltos, `refuel_stops == 0`.
  - fuel baixo no meio da rota com base disponível → `refuel_stops == 1`,
    rota continua e termina.
  - fuel baixo sem base disponível → `ok=False`, para sem completar.

## Por que isto é bom estudo de SDD

O planner decide **o quê** (rota local vs multi-sistema), nunca **como**
executar o loop de jumps — isso é só possível de saber rodando contra o
jogo de verdade, então mora inteiramente no executor, igual ao
`mine_until` da mineração.
