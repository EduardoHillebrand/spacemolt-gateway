# 0010 — Galaxy Map · tasks.md

> Continua a numeração global do projeto. A 0009 terminou em 047. Esta
> feature começa em 048.

Cada passo vira branch `NNN_descricao`, merge na master, branch preservada.

- [ ] **048_galaxy-schema-cache** — Definir o schema do `galaxy_map.json`
      (dict Python: `updated_at`, `stations_loaded`, `total_systems`,
      `scanned_systems`, `systems{}`). Implementar `_load_cache()` e
      `_write_cache()` em `mapper.py` (leitura/escrita atômica via arquivo
      temporário + rename). Testes: `test_write_and_load_cache` (escreve um
      cache fake, relê, compara campo a campo).

- [ ] **049_galaxy-mapper-stations** — Implementar `_parse_station_response`
      e `_load_stations` em `mapper.py`. Usar `httpx.AsyncClient` para a
      chamada a `GET /api/stations`. Adicionar `httpx` ao `pyproject.toml`
      se necessário. Atualizar `.gitignore` com `data/`. Testes unitários:
      `test_parse_station_response` com payload fake (sem chamada HTTP real).

- [ ] **050_galaxy-mapper-scan** — Implementar `_parse_system_response` e
      `_scan_all_systems_bg` em `mapper.py`. O loop varre todos os sistemas
      conhecidos no cache, com delay aleatório 1–3 s entre requests e
      intervalo de 5 min entre passagens completas. Salva a cada 50 sistemas
      varridos. Testes unitários: `test_parse_system_response` com payload
      fake.

- [ ] **051_galaxy-query** — Implementar `query_galaxy(query, cache)` em
      `query.py` como função pura. Cobrir todos os formatos de query: `system`,
      `station`, `nearest_fuel` (BFS, teto 5 hops), `systems_with`, `empire`,
      `map_status`. Testes: os 9 casos de `tests/core/galaxy/test_query.py`
      descritos no plan.md, todos sem chamada HTTP.

- [ ] **052_galaxy-tool-wiring** — Implementar `tool.py` (registra `galaxy_info`
      no FastMCP). Implementar `GalaxyMapper.start()` que registra a tool e
      dispara as tasks de background. Integrar no `server.py`: criar
      `_galaxy_mapper = GalaxyMapper(...)` em `main()` e chamar
      `_galaxy_mapper.start(mcp)` no lifespan. Testes de smoke:
      `galaxy_info` aparece na lista de tools do servidor. Todos os testes
      existentes continuam passando.

- [ ] **053_galaxy-manual-check** — Subir o gateway com `SPACEMOLT_URL` e
      `SPACEMOLT_SESSION_ID` reais. Verificar no devlog que:
      (a) `/api/stations` foi chamado no startup e logou quantas estações,
      (b) o scan de sistemas começou em background,
      (c) `galaxy_info("map_status")` via MCP Inspector mostra progresso,
      (d) `galaxy_info("system:Sol")` retorna dados reais após Sol ser escaneado,
      (e) `galaxy_info("nearest_fuel:<sistema_sem_refuel>")` retorna um vizinho.
      Confirmar que `data/galaxy_map.json` está sendo gerado no disco.

> Lembrete: 048 a 052 dá pra fazer e testar **sem o jogo ligado** (todo o
> código que usa HTTP é separado e testável com payloads fake). Só 053
> precisa de conexão real.

> Nota: esta feature não depende da 0005 (real transport) para funcionar —
> as chamadas HTTP são independentes do MCP transport. Pode ser implementada
> em paralelo com 0005.
