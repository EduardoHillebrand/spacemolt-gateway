# 0001 — Núcleo do Gateway · plan.md

## Stack

- Python 3.11+
- SDK MCP de Python (FastMCP) para subir o servidor.
- Cliente MCP para falar com o SpaceMolt a partir do `game_client`.
- `pytest` para testes.

## Arquitetura

```
app/
  server.py          # cria o servidor MCP, registra ferramentas, sobe
  game_client.py     # ÚNICO ponto que fala com o MCP do SpaceMolt
  registry.py        # junta ferramentas cruas + skills num só lugar
  core/
    __init__.py
    errors.py        # erros do gateway (ex: PreconditionError)
tests/
  test_game_client.py
  test_server_smoke.py
```

## Decisões

- **`game_client` é injetável.** Quem precisa dele recebe de fora. Isso permite
  trocar pelo fake nos testes (nada de chamada real ao jogo nos testes unitários).
- **`registry`** é onde as skills se "plugam". Adicionar skill nova = registrar
  ali, sem mexer no `server.py`.
- **Ferramentas cruas** ganham um prefixo/descrição que avisa "baixo nível".
- O `server.py` não tem regra de negócio. Só monta e sobe.

## Como repassar uma ferramenta crua

O `game_client` tem um método genérico `call(tool_name, **args)` que encaminha
pro SpaceMolt. Cada ferramenta crua exposta é um wrapper fininho em volta dele.

## Riscos / atenção

- Sessão do SpaceMolt: decidir onde guardar (variável de ambiente / arquivo local).
  Fica isolado no `game_client` pra não vazar pro resto.
- Não criar lógica de jogo aqui. Se aparecer, é sinal de que devia ser uma skill.

## Testes

- `test_game_client`: com um cliente MCP de mentira, confere que `call` monta a
  chamada certa e devolve a resposta certa.
- `test_server_smoke`: o servidor sobe e lista as ferramentas esperadas.
