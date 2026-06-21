# 0003 — Canal de log via WebSocket · plan.md

## Stack

- Módulo `logging` padrão do Python (os módulos só usam ele).
- Biblioteca `websockets` (WebSocket puro em Python, async).
- `asyncio` para o servidor e o fan-out.
- `pytest` para testes.

## Estrutura

```
app/core/devlog/
  __init__.py
  levels.py      # os 3 níveis + a regra "deve entregar?" (função pura)
  bus.py         # fan-out: guarda assinantes e decide quem recebe o quê
  handler.py     # logging.Handler que empurra o record pro bus
  ws_server.py   # servidor WebSocket: aceita conexão, lê o nível, registra assinante
  setup.py       # init_dev_logging(port): liga logging -> handler -> bus -> ws
tests/core/devlog/
  test_levels.py
  test_bus.py
```

## A ideia central: separar a DECISÃO do IO

Mesma filosofia do planner/executor: a parte que **decide** quem recebe é pura e
testável; a parte que **manda pela rede** fica isolada.

- `levels.py` e `bus.py` = decisão pura. Testáveis sem socket nenhum.
- `ws_server.py` = só o IO de rede.

## levels.py (puro)

Reaproveita os números do `logging`: INFO=20, WARNING=30, ERROR=40.

```python
def should_deliver(record_level: int, sub_threshold: int) -> bool:
    return record_level >= sub_threshold
```

Assinar `warning` (threshold 30) entrega record de nível 30 e 40, não 20. Pronto,
é toda a regra de filtro. O resto é encanamento.

## bus.py (fan-out, quase puro)

- Guarda um conjunto de assinantes. Cada assinante é um "destino" abstrato com
  um `threshold` e um jeito de `send(mensagem)`.
- `publish(record)`:
  - se **não há assinante**, retorna na hora (no-op). É o "só pega se tiver escutando".
  - senão, para cada assinante com `should_deliver(record.level, assinante.threshold)`,
    entrega.
- O `bus` não sabe o que é WebSocket. Ele fala com "destinos". Por isso dá pra
  testar com destinos de mentira que só anotam o que receberam.

## handler.py

- Um `logging.Handler` cujo `emit(record)` empacota o record (nível, módulo,
  mensagem, extra, hora) e manda pro `bus`.
- **Não pode bloquear.** Como `logging` pode ser chamado de qualquer thread, o
  handler entrega pro loop async de forma thread-safe (`loop.call_soon_threadsafe`)
  jogando numa fila `asyncio.Queue` **limitada**. Uma task drena a fila e chama
  `bus.publish`. Fila cheia = descarta o mais antigo. Assim log nunca trava o app.

## ws_server.py

- Sobe `websockets.serve` na porta configurada.
- Quando um cliente conecta, lê o nível desejado da query string
  (`ws://host:porta/?level=warning`); sem nível, assume `info`.
- Cria um assinante (com o `threshold` certo) e registra no `bus`.
- Ao desconectar, remove o assinante do `bus`.

## setup.py

```python
def init_dev_logging(port: int) -> None:
    # 1. cria bus
    # 2. adiciona o handler no logger raiz (logging.getLogger())
    # 3. sobe o ws_server apontando pro bus
```

Chamado uma vez quando o gateway sobe. Daí em diante, todo `log.info(...)` do
projeto sai pelo canal sem mais nada.

## Testes (sem rede)

- `test_levels`: a tabela da spec vira teste.
  - assinou error → recebe error, não recebe warning nem info.
  - assinou warning → recebe warning e error, não info.
  - assinou info → recebe os 3.
- `test_bus`:
  - sem assinante, `publish` não faz nada (e não estoura).
  - com 2 destinos de mentira em níveis diferentes, cada um recebe só o que deve.

## Quando construir

Logo depois do esqueleto do gateway (passo 002), **antes** da mineração. Assim a
mineração já nasce instrumentada e você vê o ciclo dela pelo canal.

## Atenção

- Fila limitada + descartar antigo é o que garante "nunca trava o app". Não tirar.
- Sem histórico: conectou depois, perdeu o que passou. É de propósito.
