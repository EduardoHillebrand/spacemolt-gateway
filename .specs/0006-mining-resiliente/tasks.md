# 0006 — Mineração Resiliente · tasks.md

> Continua a numeração global do projeto. A última branch registrada nas
> specs anteriores foi 022 (0005-real-transport). Esta feature começa em 023.

Cada passo vira branch `NNN_descricao`, merge na master, branch preservada.

- [ ] **023_mining-schema-resiliente** — `app/skills/mining/schema.py`:
      adicionar `fuel_current`, `fuel_capacity`, `fuel_per_jump_estimate` e
      `other_minable_poi_ids` em `MiningState`; `relocations`, `surveys`,
      `stop_reason` em `MiningResult`; novos `Step.op` (`mine_until_depleted_or_full`,
      `survey_system`). Sem lógica nova, só tipos. Atualizar testes de tipos
      se existirem.
- [ ] **024_mining-planner-fuel-check** — `planner.py`: adicionar checagem de
      fuel insuficiente antes das pré-condições já existentes; trocar o step
      `mine_until` por `mine_until_depleted_or_full` no plano montado.
      Testes: caso de fuel insuficiente → `Plan.failed`; casos existentes
      continuam passando.
- [ ] **025_mining-executor-depletion** — `executor.py`: implementar a
      detecção de depleção (quantidade extraída = 0 ou erro reconhecido) e o
      contador de falhas consecutivas por POI, com o limite antes de
      considerar esgotado. Sem realocação ainda — só para o loop e marca
      `stop_reason="system_depleted"` quando o limite é atingido sem
      alternativa. Testes com `FakeGameClient` simulando depleção.
- [ ] **026_mining-executor-relocate-survey** — `executor.py`: adicionar
      realocação para `other_minable_poi_ids` quando o POI atual esgota, e
      `survey_system()` como tentativa final quando não há POI alternativo.
      Atualizar `relocations`/`surveys` no `MiningResult`. Testes cobrindo os
      três caminhos: realocação bem-sucedida, survey bem-sucedido, ambos sem
      sucesso (esgotamento do sistema).
- [ ] **027_mining-executor-fuel-loop** — `executor.py`: checagem de fuel a
      cada iteração do loop de mineração (não só no início), parando com
      `stop_reason="low_fuel"` antes de ficar sem combustível para o
      retorno. Testes com fuel caindo progressivamente a cada chamada
      simulada.
- [ ] **028_mining-tool-parse-fuel** — `tool.py`: extrair fuel e POIs
      mineráveis do sistema no `_parse_mining_state` (texto e dict);
      incluir `relocations`, `surveys`, `stop_reason` no `_format_result`.
      Testes de parsing com exemplos de texto/dict de `get_status`/`get_system`.
- [ ] **029_mining-resiliente-manual-check** — rodar de verdade contra o
      SpaceMolt num sistema com múltiplos POIs mineráveis (ou um só, pra
      forçar survey). Acompanhar pelo devlog (`info`) a depleção, a
      realocação/survey, e a parada por esgotamento ou fuel baixo. Confirmar
      que o resumo final corresponde ao que aconteceu.

> Lembrete: 023 a 027 dá pra fazer e testar **sem o jogo ligado** (planner
> puro + `FakeGameClient` no executor). Só 029 precisa do SpaceMolt de verdade.
