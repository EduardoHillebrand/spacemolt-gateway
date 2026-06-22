# 0008 — Skill de Trading · tasks.md

> Continua a numeração global do projeto. A 0007 terminou em 036. Esta
> feature começa em 037.

Cada passo vira branch `NNN_descricao`, merge na master, branch preservada.

- [ ] **037_trading-schema** — `app/skills/trading/schema.py`: tipos
      `CargoItem`, `MarketQuote`, `TradingState`, `SellPlan`, `SellOutcome`,
      `SellResult`. Sem lógica.
- [ ] **038_trading-planner** — `planner.py` com `build_sell_plan`. Função
      pura. Testes: modo item específico (existe/não existe), modo "vender
      tudo" (separa fuel cells), não atracado → falha.
- [ ] **039_trading-price-fallback** — `executor.py`: implementar
      `best_sell_price` (função pura auxiliar) com os três ramos
      (best_sell, best_buy, piso mínimo). Testes isolados, sem
      `FakeGameClient`.
- [ ] **040_trading-executor** — `executor.py`: implementar `run_sell_plan`
      — tentar `sell`, no erro "sem comprador" cair para
      `create_sell_order` usando `best_sell_price`, registrar outcome por
      item, nunca interromper o loop por uma falha individual. Testes com
      `FakeGameClient` cobrindo venda direta, fallback para ordem, e item
      que falha sem travar os demais.
- [ ] **041_trading-tool** — `tool.py`: ler cargo e cotações de mercado,
      montar `TradingState`, registrar `sell_cargo` no gateway (com
      `item_id`/`quantity` opcionais), formatar o resumo.
- [ ] **042_trading-manual-check** — rodar de verdade contra o SpaceMolt:
      vender um item com comprador disponível, vender um item sem
      comprador (confirmar criação da ordem), e vender o cargo inteiro
      após uma mineração, confirmando que fuel cells não são tocadas.

> Lembrete: 037 a 040 dá pra fazer e testar **sem o jogo ligado**. Só 042
> precisa do SpaceMolt de verdade.
