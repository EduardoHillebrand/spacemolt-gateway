# Constituição do projeto

Regras que valem para **toda** feature. Se uma spec contradisser isto, a constituição ganha.

---

## 1. Spec primeiro

Nenhuma linha de código antes da spec da feature existir e estar clara.
A ordem é sempre: `spec.md` → `plan.md` → `tasks.md` → código.

---

## 2. Planejar ≠ executar (a regra mais importante)

Toda skill do jogo é dividida em **duas partes separadas**:

- **Planner**: olha o estado e devolve um **plano** (uma lista de passos).
  É uma **função pura**: mesma entrada, mesma saída. Não toca no jogo.
- **Executor**: pega o plano e **roda** passo a passo, chamando o jogo.

Por que separar?

- O planner você testa **sem o jogo**: dá um estado de mentira, confere o plano.
- O executor você testa com um **jogo de mentira** (um fake que só registra chamadas).
- Se misturar tudo numa função só, você não testa nada direito.

Exemplo concreto (mineração):

```
plano = [
  { "op": "mine_until", "condition": "cargo_full" },
  { "op": "travel",     "target": "<base_de_origem>" },
  { "op": "dock" },
  { "op": "sell_all_ore" }
]
```

O planner devolve isso. O executor roda. O executor é quem repete o `mine`
e checa "o cargo encheu?" — uma checagem mecânica e barata.

---

## 3. Determinístico primeiro, LLM só no ambíguo

Decisão mecânica (cargo cheio? combustível chega? qual a base mais perto?) é
**código determinístico**. Não chama LLM pra isso.

A LLM só entra quando a decisão é genuinamente ambígua (ex: "vale a pena arriscar
aquela rota com pirata?"). Esse é o padrão que já economiza API no agente atual.

---

## 4. Modular, mas sem peso de microserviço

Cada skill do jogo é um **módulo isolado** dentro do mesmo processo
(uma pasta em `app/skills/`). Não é um servidor separado.

Ganhamos o bom do microserviço (isolamento, objetivo único, testar sozinho)
sem o ruim (rede entre serviços, mais coisa pra subir, mais ponto de falha).

Regra prática: uma skill **não importa** o código interno de outra skill.
Se duas precisam da mesma coisa, ela sobe pra `app/core/`.

---

## 5. Cada coisa no seu lugar (clean code)

- `game_client.py`: **único** lugar que fala com o MCP cru do SpaceMolt.
  Nenhuma skill chama o SpaceMolt direto. Toda skill recebe o `game_client`.
- `planner.py`: só monta plano. Função pura. Sem efeito colateral.
- `executor.py`: só roda plano. Recebe o `game_client` de fora (injeção de dependência).
- `schema.py`: os tipos (o formato do plano, do resultado). Nada de lógica.

Isso deixa cada arquivo com **um motivo pra mudar**.

---

## 6. Erro fala, não falha calado

Se uma skill não pode rodar (falta laser de mineração, cargo já cheio, não está
num ponto minerável), ela devolve um **resultado claro dizendo o que falta** —
nunca quebra silenciosa nem inventa. A LLM lê isso e decide o que fazer.

---

## 7. Git por passo

Cada passo de `tasks.md` é uma branch `NNN_descricao-curta`. Merge na master no
fim do passo. A branch **nunca é apagada** (fica como histórico do passo).
Detalhes em `.claude/skills/git-flow`.

---

## 8. Idioma

- Código (funções, variáveis, branches, commits): **inglês**.
- Specs, docs, comentários de explicação: **português**.
