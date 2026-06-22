# 0009 — Skill de Manutenção da Nave · plan.md

## Estrutura

```
app/skills/maintenance/
  __init__.py
  schema.py      # tipos: MaintenanceState, MaintenancePlan, MaintenanceOutcome, MaintenanceResult
  planner.py     # build_maintenance_plan(state, action) -> MaintenancePlan   (função pura)
  executor.py    # run_maintenance_plan(plan, game_client) -> MaintenanceResult
  tool.py        # registra maintain_ship no gateway; cola planner + executor
tests/skills/maintenance/
  test_planner.py
  test_executor.py
```

Esta skill é a mais simples das quatro: não tem laço (`refuel`/`repair` são
chamadas únicas), então o ganho do padrão planner/executor aqui é menor,
mas mantém-se pela consistência e pela regra de detecção de erro específico
descrita na spec.

## Schema (`schema.py`)

```python
@dataclass
class MaintenanceState:
    is_docked: bool
    action: str   # "refuel" | "repair" | "full"

@dataclass
class MaintenancePlan:
    steps: list[str]    # subconjunto de ["refuel", "repair"], na ordem de execução
    ok: bool = True
    failure_reason: str | None = None

@dataclass
class MaintenanceOutcome:
    step: str                  # "refuel" | "repair"
    ok: bool
    detail: str = ""
    no_fuel_at_station: bool = False   # só relevante para "refuel"

@dataclass
class MaintenanceResult:
    ok: bool
    outcomes: list[MaintenanceOutcome] = field(default_factory=list)
    failure_reason: str | None = None
```

## Planner (`build_maintenance_plan`)

Função pura:

- Pré-condição: `is_docked` — senão `MaintenancePlan.failed("precisa estar atracado")`.
- `action == "refuel"` → `steps=["refuel"]`.
- `action == "repair"` → `steps=["repair"]`.
- `action == "full"` → `steps=["refuel", "repair"]`.
- Valor de `action` fora desse conjunto → falha clara (parâmetro inválido).

## Executor (`run_maintenance_plan`)

```
para cada step do plano:
  "refuel":
    tentar refuel()
    sucesso → outcome ok=True
    erro reconhecido como "sem combustível na estação" (código/mensagem,
      lista fixa de marcadores igual ao agente anterior) →
        outcome ok=False, no_fuel_at_station=True, detail=mensagem original
    qualquer outro erro → outcome ok=False, detail=mensagem original
  "repair":
    tentar repair()
    sucesso → outcome ok=True, detail com hull recuperado/custo
    erro → outcome ok=False, detail=mensagem original
  (um step falhar não impede o próximo — independentes, igual à spec)
```

Resultado final (`ok`) é `True` se pelo menos um step não bloqueado por
pré-condição foi tentado — falhas individuais aparecem nos `outcomes`, não
tornam o `MaintenanceResult.ok` falso (a LLM lê os outcomes pra saber o que
deu certo).

## tool.py

- Lê `get_status` (campo de docagem) para montar `MaintenanceState`.
- Recebe `action: str = "full"` como parâmetro.
- Chama planner, depois executor.
- Formata o resumo: para cada outcome, diz o que aconteceu; quando
  `no_fuel_at_station=True`, adiciona a sugestão explícita de usar
  `navigate_to` (0007) para buscar outra estação — sem calcular a rota
  aqui.

## Testes (sem tocar no jogo de verdade)

- `test_planner`: cada valor de `action` monta os `steps` certos; não
  atracado → falha; `action` inválido → falha.
- `test_executor` com `FakeGameClient`:
  - refuel com sucesso → outcome ok.
  - refuel com erro de "sem combustível na estação" (testar pelo menos os
    marcadores principais: código e por mensagem) → `no_fuel_at_station=True`.
  - repair com sucesso → outcome ok com detail.
  - modo `full` com refuel falhando por falta de estoque e repair
    funcionando → os dois outcomes aparecem, independentes.

## Por que isto é bom estudo de SDD

Mesmo numa skill sem laço, vale separar planner/executor: o planner decide
**quais** passos rodar (regra simples, testável sem jogo), o executor lida
com a **interpretação de erro específico** (sem combustível vs erro
genérico) que só faz sentido contra respostas reais do jogo.
