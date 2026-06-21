# 0004 — Proxy dinâmico · tasks.md

- [ ] **016_proxy-schema** — Criar `ToolSchema` e `ParamSchema` em
      `app/core/proxy.py`. Adicionar `list_tools()` no `StubTransport` e no
      `GameClient`. Testes unitários para os tipos e para o stub.

- [ ] **017_proxy-register** — Implementar `setup_proxy` e `_make_proxy` em
      `app/core/proxy.py`. Registrar proxies dinâmicos no FastMCP.
      Testes: tools aparecem após `setup_proxy`, `session_id` é injetado,
      log INFO é emitido, falha em `list_tools` não derruba o gateway.

- [ ] **018_proxy-wiring** — Chamar `setup_proxy` no lifespan de `server.py`.
      Remover os 3 tools hardcoded de `registry.py`. Atualizar `test_registry.py`
      e `test_server_smoke.py` se necessário. Todos os testes passando.

- [ ] **019_proxy-manual-check** — Subir o gateway com session real, confirmar
      que todos os tools do SpaceMolt aparecem na lista, fazer uma chamada
      e verificar no devlog. Atualizar README.
