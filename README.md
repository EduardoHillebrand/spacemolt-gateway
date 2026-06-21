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

## Como este projeto é construído

Ele é um exercício de **Spec Driven Development (SDD)**:
a especificação vem antes do código. Tudo está em `.specs/`.

Ordem: `spec.md` (o quê/porquê) → `plan.md` (o como) → `tasks.md` (passos pequenos).
Cada passo de `tasks.md` vira uma branch no Git.

Comece lendo: `.specs/README.md` e `.specs/constitution.md`.

## Stack

- Python 3.11+
- Servidor MCP (FastMCP / SDK MCP de Python)
- Sem nuvem: roda local, igual ao resto do ecossistema.

## Estrutura (quando o código existir)

```
app/
  server.py          # registra as ferramentas e sobe o MCP
  game_client.py     # camada fina que chama o MCP cru do SpaceMolt
  skills/
    mining/
      planner.py     # monta o plano (função pura)
      executor.py    # roda o plano (recebe o game_client)
      schema.py      # tipos do plano e do resultado
  core/
    plan.py          # tipos genéricos de Plano/Passo, reusados por toda skill
tests/
  skills/mining/...
```
