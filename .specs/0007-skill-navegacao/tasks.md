# 0007 — Skill de Navegação · tasks.md

> Continua a numeração global do projeto. A 0006 terminou em 029. Esta
> feature começa em 030.

Cada passo vira branch `NNN_descricao`, merge na master, branch preservada.

- [ ] **030_navigation-schema** — `app/skills/navigation/schema.py`: tipos
      `NavState`, `Hop`, `Plan`, `NavResult`. Sem lógica.
- [ ] **031_navigation-planner** — `planner.py` com `build_navigation_plan`.
      Função pura. Testes: já no destino, POI do sistema atual, sistema
      diferente (`route_to`), destino inválido.
- [ ] **032_navigation-executor-local** — `executor.py`: implementar os hops
      diretos (`undock`, `travel`, `dock`, `jump`) e o caso "já no destino".
      Ainda sem o loop de `route_to`. Testes com `FakeGameClient`.
- [ ] **033_navigation-executor-route** — `executor.py`: implementar o loop
      de `route_to` — chamar `find_route`, saltar sistema a sistema, checar
      fuel a cada salto, teto de iterações. Testes cobrindo rota direta sem
      reabastecimento.
- [ ] **034_navigation-executor-refuel-stop** — `executor.py`: desviar para
      reabastecer (dock + refuel + undock) quando o fuel projetado ficar
      abaixo da margem de segurança, e interromper com erro claro quando não
      há base disponível para isso. Testes cobrindo os dois casos.
- [ ] **035_navigation-tool** — `tool.py`: parse de `get_status` para
      `NavState`, parse do parâmetro `destination` (`"Sistema"` ou
      `"Sistema/poi_id"`), registro de `navigate_to` no gateway, formatação
      do resumo.
- [ ] **036_navigation-manual-check** — rodar de verdade contra o SpaceMolt:
      um caso de POI no sistema atual, um caso de salto multi-sistema sem
      reabastecimento, e um caso (se possível simular) com fuel baixo
      forçando parada para reabastecer. Acompanhar pelo devlog.

> Lembrete: 030 a 034 dá pra fazer e testar **sem o jogo ligado**. Só 036
> precisa do SpaceMolt de verdade.
