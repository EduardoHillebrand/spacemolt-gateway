# 0008 — Skill de Trading · plan.md

## Estrutura

```
app/skills/trading/
  __init__.py
  schema.py      # tipos: CargoItem, MarketSnapshot, SellPlan, SellOutcome, SellResult
  planner.py     # build_sell_plan(state) -> SellPlan   (função pura)
  executor.py    # run_sell_plan(plan, game_client) -> SellResult
  tool.py        # registra sell_cargo no gateway; cola planner + executor
tests/skills/trading/
  test_planner.py
  test_executor.py
```

## Schema (`schema.py`)

```python
@dataclass
class CargoItem:
    item_id: str
    quantity: int

@dataclass
class MarketQuote:
    item_id: str
    best_sell: int | None   # melhor oferta de venda existente no mercado
    best_buy: int | None    # melhor oferta de compra existente no mercado

@dataclass
class TradingState:
    is_docked: bool
    cargo: list[CargoItem]
    market: list[MarketQuote]
    requested_item_id: str | None   # None = modo "vender tudo"
    requested_quantity: int | None

@dataclass
class SellPlan:
    items: list[CargoItem]    # itens a processar (já filtrados: sem fuel cells no modo "tudo")
    kept: list[CargoItem]     # itens mantidos (fuel cells), só para o resumo
    ok: bool = True
    failure_reason: str | None = None

@dataclass
class SellOutcome:
    item_id: str
    quantity: int
    mode: str          # "sold_direct" | "order_created" | "failed"
    credits: float = 0.0
    order_price: int | None = None
    error: str | None = None

@dataclass
class SellResult:
    ok: bool
    outcomes: list[SellOutcome] = field(default_factory=list)
    kept: list[CargoItem] = field(default_factory=list)
    failure_reason: str | None = None
```

## Lista de itens protegidos (fuel cells)

Vive como constante do módulo (`_KEEP_ITEM_IDS`), igual ao
`FUEL_CELL_CATALOG` do agente anterior — não precisa vir de configuração
externa, é uma regra fixa do jogo (combustível nunca é vendido sozinho).

## Planner (`build_sell_plan`)

Função pura:

- Pré-condição: `is_docked` — senão `SellPlan.failed("precisa estar atracado")`.
- Modo item específico: confere se o item existe no cargo em quantidade
  suficiente; monta `items=[CargoItem(item_id, quantity)]`.
- Modo "vender tudo": separa `cargo` em `items` (vendável) e `kept`
  (fuel cells), na ordem em que aparecem no cargo.
- Não decide preço nem chama o mercado — isso é do executor, porque depende
  da cotação **no momento da venda**, item por item.

## Executor (`run_sell_plan`)

```
para cada item em plan.items:
  tentar sell(item_id, quantity)
  se sucesso → outcome "sold_direct", credits = total_earned
  se "sem comprador" (mecânico, por código/mensagem) →
    price = best_sell_price(market_quote_do_item)
    tentar create_sell_order(item_id, quantity, price)
    se sucesso → outcome "order_created", order_price = price
    se falha → outcome "failed", error = mensagem
  se qualquer outro erro → outcome "failed", error = mensagem
  (erro num item não interrompe o loop — segue pro próximo)
```

`best_sell_price(quote)`:

```
se quote.best_sell existe e > 1: quote.best_sell - 1
senão se quote.best_buy existe e > 2: quote.best_buy + 1
senão: piso mínimo fixo (constante do módulo)
```

Função pura auxiliar — testável isolada, sem chamar o jogo.

## tool.py

- Lê `get_status`/`get_cargo` (cargo) e `view_market` (cotações dos itens
  relevantes) para montar `TradingState`.
- Recebe `item_id: str | None` e `quantity: int | None`.
- Chama planner, depois executor, formata o resumo: vendidos diretos,
  ordens criadas (com preço), falhas, e itens mantidos.

## Testes (sem tocar no jogo de verdade)

- `test_planner`: modo item específico (existe / não existe no cargo),
  modo "tudo" (separa fuel cells corretamente), não atracado → falha.
- `test_best_sell_price`: os três ramos (best_sell, best_buy, piso mínimo).
- `test_executor` com `FakeGameClient`:
  - item vende direto → outcome `sold_direct`.
  - item sem comprador → outcome `order_created` com o preço calculado.
  - um item falha e outro vende → ambos aparecem no resultado, loop não
    interrompe.

## Por que isto é bom estudo de SDD

O cálculo de preço de fallback é uma função pura isolada dentro do
executor (não precisa de I/O) — é um bom exemplo de extrair lógica
determinística mesmo dentro da camada que fala com o jogo, sem forçá-la
para dentro do planner só porque "planner é onde fica a lógica pura".
