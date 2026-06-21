---
name: new-gateway-skill
description: Receita para adicionar uma nova skill do jogo ao gateway (ex viajar, atracar, comerciar). Use quando o projeto for ganhar uma nova capacidade de alto nível exposta como ferramenta MCP. Garante o padrão planner/executor isolado.
---

# Como adicionar uma nova skill do jogo

Uma "skill do jogo" é um módulo isolado em `app/skills/` que vira uma ferramenta
de alto nível no gateway. Segue sempre o mesmo molde (o de mineração é o exemplo).

## 1. Spec primeiro

Criar `.specs/NNNN-skill-<nome>/` com `spec.md`, `plan.md`, `tasks.md`.
(usar a skill `sdd-workflow`). Sem spec, não começa.

## 2. Molde de pastas

```
app/skills/<nome>/
  __init__.py
  schema.py      # tipos: estado de entrada, Step/Plan, resultado
  planner.py     # build_<nome>_plan(state) -> Plan   (função pura)
  executor.py    # run_<nome>_plan(plan, game_client) -> <Nome>Result
  tool.py        # lê estado, chama planner+executor, registra no gateway
tests/skills/<nome>/
  test_planner.py
  test_executor.py
```

## 3. As 4 peças, sempre iguais

- **schema**: só tipos. Nada de lógica.
- **planner**: função pura. Decide o plano olhando o estado. Trata pré-condições.
- **executor**: roda o plano. Recebe `game_client` de fora. Faz as checagens
  mecânicas (condições de laço) aqui, nunca na LLM.
- **tool**: cola tudo e registra a ferramenta no `registry`. Sem regra de jogo.

## 4. Regras de isolamento

- Uma skill **não importa** outra skill. Código comum sobe pra `app/core/`.
- A skill **não fala** com o SpaceMolt direto. Sempre via `game_client`.
- Pré-condição que falha → resultado claro dizendo o que falta. Sem quebra muda.

## 5. Plano com laço (quando o número de passos é desconhecido)

Se a skill tem "faça X até a condição Y" (como minerar até encher), o plano
descreve a **intenção** com um passo de laço (`op="..._until", condition="..."`).
Quem resolve o laço e checa a condição é o **executor**, com um teto de segurança.

## 6. Testes sem o jogo

- planner: testar com estados de mentira.
- executor: testar com um `FakeGameClient` que registra chamadas e simula o estado mudando.
- Só o "manual-check" final usa o SpaceMolt de verdade.

## 7. Git

Cada peça (schema, planner, executor, tool) costuma ser um passo/branch próprio.
Seguir a skill `git-flow`.
