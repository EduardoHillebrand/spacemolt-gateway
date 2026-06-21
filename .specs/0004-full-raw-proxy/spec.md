# 0004 — Proxy dinâmico de todos os tools do SpaceMolt · spec.md

## O quê

O gateway descobre automaticamente todos os tools do SpaceMolt no boot e
registra uma versão proxy de cada um. A LLM só vê o gateway — o SpaceMolt
fica invisível.

## Porquê

Hoje o gateway expõe 3 tools fixos (`get_status`, `mine`, `travel`).
O SpaceMolt tem ~18. Isso cria dois problemas:

1. **Fuga do gateway**: se o SpaceMolt estiver configurado diretamente no
   Claude Desktop, a LLM pode chamá-lo sem passar pelo gateway — sem log,
   sem controle, sem skills de alto nível.
2. **Manutenção manual**: toda vez que o SpaceMolt adicionar um tool novo,
   alguém precisa lembrar de atualizar o `registry.py`.

A solução: o gateway vira a **única porta de entrada**. Ele introspecciona
o SpaceMolt no boot, cria proxies para tudo automaticamente e injeta o
`session_id` em toda chamada.

## Comportamento esperado

Ao subir:

1. O gateway chama `list_tools()` no transport do SpaceMolt.
2. Para cada tool descoberto, registra um proxy no servidor MCP:
   - Mesmo nome que o tool original.
   - Mesma lista de parâmetros (exceto `session_id`, que é injetado).
   - Description original prefixada com `[PROXY] `.
3. Os proxies antigos hardcoded (`get_status`, `mine`, `travel`) são
   **removidos** — o proxy dinâmico os substitui.

Durante uma chamada:

1. A LLM chama `mine(action="mine")` no gateway.
2. O gateway loga: `proxy.mine: action=mine`.
3. Injeta `session_id`, repassa ao SpaceMolt.
4. Loga a resposta (nível INFO, resumido).
5. Devolve o resultado para a LLM.

## Regras

- `session_id` nunca aparece nos parâmetros que a LLM vê — é sempre injetado.
- Skills de alto nível têm prioridade: se um tool proxy e uma skill cobrem
  o mesmo objetivo, a description do proxy avisa (`[PROXY] Prefira a skill X`).
- Se `list_tools()` falhar no boot, o gateway sobe assim mesmo em modo stub
  (com os tools fixos antigos como fallback) e loga o erro.
- O `StubTransport` devolve uma lista hardcoded de tools para testes.

## Fora de escopo

- Validar ou transformar parâmetros além do que o SpaceMolt já faz.
- Cachear respostas.
- Filtrar quais tools do SpaceMolt ficam visíveis.

## Pronto quando

- `python -m app.server` → a LLM vê todos os ~18 tools do SpaceMolt
  (sem precisar de conexão direta com o SpaceMolt).
- Toda chamada a qualquer tool proxy aparece no devlog (canal WebSocket).
- Adicionar um tool novo no SpaceMolt → reaparece no gateway no próximo boot,
  sem tocar em código.
