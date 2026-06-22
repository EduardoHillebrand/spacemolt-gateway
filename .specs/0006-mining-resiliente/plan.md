# 0006 — Mineração Resiliente · plan.md

## Dependência pré-existente

`app/core/errors.py` — já existe com `PreconditionError`. Foi criado antes desta
spec (desvio de processo registrado na auditoria). O task 023 deve referenciar e
testar esta classe ao adicionar a checagem de fuel.

## Estrutura

Não cria um módulo novo — **estende** `app/skills/mining/` (0002), porque é
a mesma skill, só mais robusta. Os mesmos quatro arquivos crescem:

```
app/skills/mining/
  schema.py      # + campos de fuel, contadores de falha, lista de POIs alternativos
  planner.py     # build_mining_plan ganha checagem de fuel; plano ganha steps novos
  executor.py    # mine_until ganha depleção/realocação/survey; loop de fuel
  tool.py        # parsing do get_status ganha fuel e lista de POIs do sistema
tests/skills/mining/
  test_planner.py    # + casos de fuel insuficiente
  test_executor.py   # + casos de depleção, realocação, survey, esgotamento
```

## Schema (`schema.py`)

`MiningState` ganha:

```python
fuel_current: int
fuel_capacity: int
fuel_per_jump_estimate: int   # custo conservador de combustível por salto/travel
other_minable_poi_ids: list[str]   # POIs mineráveis já visíveis no sistema, exceto o atual
```

`Plan` ganha um novo tipo de step:

```python
Step(op="mine_until_depleted_or_full")   # substitui o antigo "mine_until"
Step(op="survey_system")                  # tentativa de revelar deep core
```

`MiningResult` ganha:

```python
relocations: int      # quantas vezes mudou de POI por depleção
surveys: int           # quantas vezes rodou survey_system
stop_reason: str       # "cargo_full" | "system_depleted" | "low_fuel"
```

## Planner (`build_mining_plan`)

Pré-condições na mesma ordem da 0002, com uma nova checagem **antes** de
montar o plano:

```
fuel_current < fuel_per_jump_estimate * 2  → Plan.failed("fuel insuficiente para ida e volta")
```

(`* 2` é a margem: ida até a base de venda e uma sobra de segurança — número
exato fica documentado no código, não precisa ser exposto na spec.)

O plano passa a ser:

```python
[
  Step(op="mine_until_depleted_or_full"),
  Step(op="travel", target=state.home_base_poi_id),
  Step(op="dock"),
  Step(op="sell_all_ore"),
]
```

Continua função pura — toda a complexidade de depleção/realocação/survey
vira lógica do **executor**, porque depende de chamadas reais ao jogo a
cada iteração (o planner não sabe de antemão quantos POIs vão depletar).

## Executor (`run_mining_plan`)

`mine_until_depleted_or_full` substitui o `_mine_until_full` atual:

```
loop (até cargo cheio, teto de iterações, ou esgotamento):
  checar fuel restante; se abaixo do mínimo de retorno → parar (stop_reason="low_fuel")
  chamar mine()
  se quantidade extraída > 0 → resetar contador de falha do POI atual, continuar
  se quantidade extraída == 0 (ou erro de depleção):
    incrementar contador de falha do POI atual
    se contador < limite → tentar de novo (próxima iteração do loop)
    se contador >= limite:
      marcar POI atual como esgotado
      se há outro POI minerável conhecido (other_minable_poi_ids) →
        travel até ele, zerar contador, continuar minerando lá (relocations += 1)
      senão →
        chamar survey_system() (surveys += 1)
        se survey revelar POI novo → travel até ele, continuar minerando lá
        senão → parar (stop_reason="system_depleted")
```

Constantes de limite (quantas falhas até considerar esgotado, teto de
iterações, margem de fuel) vivem como constantes do módulo, igual ao
`_MINE_LOOP_MAX` já existente — não é configuração exposta à LLM.

## tool.py

`_parse_mining_state` (texto e dict) ganha extração de:

- `Fuel: X/Y` da linha de status (regex análoga à de `Cargo: X/Y`).
- Lista de POIs mineráveis do sistema, a partir do bloco de conexões/POIs
  que já aparece no `get_status`/`get_system` — se o `get_status` atual não
  trouxer isso, o `tool.py` faz uma chamada extra a `get_system` só quando
  for montar o estado (mantém o resto do fluxo igual).

`_format_result` passa a incluir `relocations`, `surveys` e `stop_reason`
no resumo devolvido à LLM.

## Testes (sem tocar no jogo de verdade)

- `test_planner`: + caso "fuel insuficiente" → `Plan.failed`.
- `test_executor` com `FakeGameClient` configurável para devolver:
  - depleção (quantidade 0) nas N primeiras chamadas de um POI, depois
    funcionando num POI diferente → confere `relocations == 1`.
  - depleção em todos os POIs conhecidos → confere chamada de
    `survey_system` e `surveys == 1`.
  - survey também sem novo POI → confere `stop_reason == "system_depleted"`
    e que a venda do que já foi coletado ainda acontece.
  - fuel caindo abaixo do mínimo no meio do loop → confere
    `stop_reason == "low_fuel"` e parada antes do teto de iterações.

## Por que isto é bom estudo de SDD

A 0002 já separava planner e executor; a 0006 mostra **por que** o executor
existe separado: toda a lógica de depleção/realocação/survey/fuel é decisão
mecânica baseada em respostas reais do jogo, passo a passo — não cabe num
planner que só olha o estado uma vez no início.
