# 0009 — Skill de Manutenção da Nave · tasks.md

> Continua a numeração global do projeto. A 0008 terminou em 042. Esta
> feature começa em 043.

Cada passo vira branch `NNN_descricao`, merge na master, branch preservada.

- [ ] **043_maintenance-schema** — `app/skills/maintenance/schema.py`: tipos
      `MaintenanceState`, `MaintenancePlan`, `MaintenanceOutcome`,
      `MaintenanceResult`. Sem lógica.
- [ ] **044_maintenance-planner** — `planner.py` com `build_maintenance_plan`.
      Função pura. Testes: `action` = refuel/repair/full montam os steps
      certos; não atracado → falha; `action` inválido → falha.
- [ ] **045_maintenance-executor** — `executor.py` com `run_maintenance_plan`:
      refuel e repair como chamadas únicas, detecção do erro "sem
      combustível na estação" (marcadores fixos de código/mensagem,
      adaptados do agente anterior), steps independentes. Testes com
      `FakeGameClient` cobrindo sucesso, erro de sem-combustível, e modo
      `full` com um step falhando e outro funcionando.
- [ ] **046_maintenance-tool** — `tool.py`: ler estado de docagem, registrar
      `maintain_ship` no gateway (`action` default `"full"`), formatar o
      resumo incluindo a sugestão de `navigate_to` quando
      `no_fuel_at_station=True`.
- [ ] **047_maintenance-manual-check** — rodar de verdade contra o
      SpaceMolt: reabastecer numa estação com combustível, reparar com
      casco danificado, e (se possível) reproduzir/forçar o caso de
      estação sem combustível para confirmar a mensagem de sugestão.

> Lembrete: 043 a 045 dá pra fazer e testar **sem o jogo ligado**. Só 047
> precisa do SpaceMolt de verdade.
