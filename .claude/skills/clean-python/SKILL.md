---
name: clean-python
description: Padrões de clean code em Python para este projeto. Use ao escrever ou revisar qualquer arquivo .py. Cobre separação por objetivo, funções puras, injeção de dependência e testes sem serviço externo.
---

# Clean code (Python) deste projeto

## Um arquivo, um motivo pra mudar

- `schema.py` — só tipos (dataclasses). Sem lógica.
- `planner.py` — só monta plano. Função pura. Sem efeito colateral.
- `executor.py` — só roda plano. Recebe dependências de fora.
- `tool.py` — só cola as peças e registra no gateway. Sem regra de negócio.
- `game_client.py` — único lugar que fala com o SpaceMolt.

Se um arquivo começa a fazer duas coisas, separar.

## Função pura quando der

Função pura = mesma entrada, mesma saída, sem mexer em nada de fora.
O planner é puro de propósito: dá pra testar dando um estado de mentira.

```python
def build_mining_plan(state: MiningState) -> Plan:
    # só lê 'state' e devolve um Plan. Não chama o jogo. Não grava nada.
    ...
```

## Injeção de dependência

Quem tem efeito colateral **recebe** a dependência, não a cria por dentro:

```python
# bom: dá pra passar um fake no teste
def run_mining_plan(plan: Plan, game_client) -> MiningResult: ...

# ruim: amarra no cliente real, impossível testar sem o jogo
def run_mining_plan(plan: Plan) -> MiningResult:
    client = RealGameClient()  # não faça isso
```

## Nomes

- Inglês. Verbo pra função (`build_plan`, `run_plan`), substantivo pra dado (`MiningState`).
- Nada de abreviação obscura. `cargo_free` é melhor que `cf`.

## Erros que falam

Pré-condição que falha devolve motivo claro ou levanta erro específico
(`PreconditionError("missing mining laser")`). Nunca `return None` mudo.

## Testes

- Teste unitário **não** toca em serviço externo. Usa fake.
- Um teste por comportamento da spec ("pronto quando" vira teste).
- Nome do teste descreve o caso: `test_planner_sem_laser_devolve_motivo`.

## Tamanho

Função que passa de ~20 linhas ou tem muitos `if` aninhados: quebrar em funções
menores com nome. Cada uma faz uma coisa.
