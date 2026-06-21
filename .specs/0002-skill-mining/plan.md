# 0002 — Skill de Mineração · plan.md

## Estrutura (o padrão "microserviço leve" de uma skill)

```
app/skills/mining/
  __init__.py
  schema.py      # tipos: MiningState, Plan, Step, MiningResult
  planner.py     # build_mining_plan(state) -> Plan   (função pura)
  executor.py    # run_mining_plan(plan, game_client) -> MiningResult
  tool.py        # registra mining_run no gateway; cola planner + executor
tests/skills/mining/
  test_planner.py
  test_executor.py
```

Isso espelha a constituição: planner puro de um lado, executor do outro,
schema só com tipos, e um `tool.py` fininho que liga tudo no gateway.

## O plano (formato)

Um plano é uma lista de passos. Os passos desta skill:

```python
[
  Step(op="mine_until", condition="cargo_full"),
  Step(op="travel",     target=home_base_id),
  Step(op="dock"),
  Step(op="sell_all_ore"),
]
```

Repare no `mine_until`: é um passo de **laço**. O plano não diz quantas vezes
minerar — diz "minere até a condição". Quem resolve o laço é o executor.

## O planner (função pura)

```
build_mining_plan(state: MiningState) -> Plan
```

- Recebe um retrato do estado (tem laser? cargo livre? base de origem? está num
  ponto minerável?).
- Se uma pré-condição falha, devolve um plano **vazio com motivo** (ou levanta
  `PreconditionError`) — a decisão de formato fica no `schema.py`.
- Não chama o jogo. Não tem efeito colateral. Fácil de testar.

## O executor

```
run_mining_plan(plan: Plan, game_client) -> MiningResult
```

- Recebe o `game_client` de fora (injeção de dependência → testável com fake).
- Anda no plano:
  - `mine_until`: repete `game_client.call("mine")` e depois de cada chamada
    checa se o cargo encheu (checagem determinística). Pára quando encher.
  - `travel`/`dock`/`sell_all_ore`: uma chamada cada.
- Junta os números e devolve `MiningResult` (minerado, vendido, ganho, parada).
- Guarda de segurança: um teto de iterações no `mine_until` pra nunca rodar pra
  sempre se algo der errado.

## tool.py (a cola)

- Lê o estado via `game_client`, monta o `MiningState`.
- Chama o planner, depois o executor.
- Registra `mining_run` no `registry` do gateway.
- Não tem lógica de mineração nenhuma — só orquestra.

## Testes (sem tocar no jogo de verdade)

- `test_planner`: dá estados de mentira, confere o plano.
  - cargo vazio + laser → plano completo na ordem certa.
  - sem laser → plano vazio com motivo "falta laser".
  - cargo já cheio → plano sem `mine_until` (vai direto vender) ou motivo, conforme a spec.
- `test_executor`: usa um `FakeGameClient` que simula o cargo enchendo a cada
  `mine`. Confere que o laço pára na hora certa e que `sell_all_ore` foi chamado.

## Por que isto é bom estudo de SDD

Você escreveu a spec sem falar de Python. O plan trouxe a tecnologia. As tasks
quebram em passos de uma branch cada. E o código sai quase "ditado" pelo plan —
que é o ponto do método.
