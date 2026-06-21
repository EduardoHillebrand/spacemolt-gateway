# 0002 — Skill de Mineração · tasks.md

> Ordem de construção: esta feature é feita **depois** do canal de log (0003),
> então a mineração já nasce instrumentada (usa a skill `dev-logging`).
> Por isso os passos começam em 011 (007–010 são do canal de log).

Cada passo vira branch `NNN_descricao`, merge na master, branch preservada.

- [ ] **011_mining-schema** — `app/skills/mining/schema.py`: tipos `MiningState`,
      `Step`, `Plan`, `MiningResult`. Sem lógica. (Pode ter teste mínimo de tipos.)
- [ ] **012_mining-planner** — `planner.py` com `build_mining_plan`. Função pura.
      Testes: caminho feliz + pré-condições que faltam. Já com `log.info` nos pontos-chave.
- [ ] **013_mining-executor** — `executor.py` com `run_mining_plan` e o
      `FakeGameClient` nos testes simulando o cargo enchendo. Teto de iterações.
      Logar cada volta do `mine_until` em info.
- [ ] **014_mining-tool** — `tool.py`: lê estado, chama planner+executor, registra
      `mining_run` no gateway. Sem lógica de mineração aqui.
- [ ] **015_mining-manual-check** — rodar de verdade contra o SpaceMolt num ponto
      minerável. Conectar no canal de log assinando `info` e acompanhar o ciclo ao vivo.

> Lembrete: 011 e 012 dá pra fazer e testar **sem o jogo ligado**.
> Só o 015 precisa do SpaceMolt de verdade. Esse é o ganho de separar plano de execução.
