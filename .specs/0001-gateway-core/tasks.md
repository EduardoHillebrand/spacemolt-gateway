# 0001 — Núcleo do Gateway · tasks.md

Cada passo vira uma branch `NNN_descricao`. Merge na master no fim de cada um.
A branch não é apagada.

- [ ] **001_init-repo** — `git init`, `.gitignore` de Python, `README`, `CLAUDE.md`,
      pasta `.specs/` e `.claude/skills/` commitados. Primeiro commit na master.
- [ ] **002_project-skeleton** — criar `app/`, `tests/`, `pyproject.toml`,
      ambiente virtual, `pytest` rodando (mesmo sem teste de verdade ainda).
- [ ] **003_game-client** — `app/game_client.py` com `call(tool, **args)` e a
      sessão isolada. Teste com cliente MCP de mentira.
- [ ] **004_mcp-server** — `app/server.py` sobe um MCP vazio. Teste de fumaça:
      o servidor lista zero ou as ferramentas registradas.
- [ ] **005_raw-proxy** — `app/registry.py` registra 2–3 ferramentas cruas
      (ex: `get_state`, `get_location`, `mine`) repassando pro `game_client`.
      Marcadas como "baixo nível".
- [ ] **006_manual-check** — rodar o gateway, conectar e confirmar que uma
      chamada crua passa e volta certa. Anotar no `README` como subir.

> Cada passo: branch → código + teste → teste passando → merge na master.
> Só começa o próximo passo depois do merge do anterior.
