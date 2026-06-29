# 0005-B — Transport sob demanda · tasks.md

## Passo 033 — `033_ondemand-transport`

### Mudanças em produção

- [ ] `app/transports/streamable_http.py`
  - `__init__`: remover `self._session` e `self._exit_stack`
  - `connect()`: virar no-op com log.debug
  - `disconnect()`: virar no-op
  - `call_tool()`: abrir `AsyncExitStack` local, criar sessão, chamar, fechar
  - `list_tools()`: idem

### Testes

- [ ] `tests/transports/test_streamable_http.py`
  - Adaptar fixtures para mockar `streamablehttp_client` e `ClientSession`
    em vez de injetar `session` diretamente
  - Todos os testes existentes devem passar

### Pronto quando

- `pytest` verde
- Gateway rodando sem nenhuma chamada → nenhuma mensagem de reconexão no log
