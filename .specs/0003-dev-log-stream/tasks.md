# 0003 — Canal de log via WebSocket · tasks.md

Esta feature é construída **logo depois do esqueleto do gateway** (passo 002) e
**antes da mineração**, pra mineração já nascer com log. Por isso ela pega os
passos 007–010, e a mineração foi empurrada pra 011–015.

- [ ] **007_devlog-levels** — `app/core/devlog/levels.py` com `should_deliver`
      e os 3 níveis. Função pura. Testes = a tabela da spec (error/warning/info).
- [ ] **008_devlog-bus** — `bus.py`: guarda assinantes, `publish(record)` entrega
      a quem deve, no-op se ninguém escuta. Testes com destinos de mentira.
- [ ] **009_devlog-ws** — `handler.py` (logging.Handler não-bloqueante, fila
      limitada), `ws_server.py` (lê nível da query string) e `setup.py`
      (`init_dev_logging`). Chamar o setup no `server.py` do gateway.
- [ ] **010_devlog-manual-check** — subir o gateway, conectar 2 clientes (um em
      `error`, um em `info`), gerar logs e confirmar o filtro. Desconectar todos
      e confirmar que o gateway segue normal. Anotar no README como conectar.

> Depois do 010, todo código novo (inclusive a mineração) já usa a skill
> `dev-logging` e aparece no canal automaticamente.

## Cliente de teste rápido (pro passo 010)

Qualquer cliente WebSocket serve. Exemplos:
- `websocat "ws://localhost:<porta>/?level=info"`
- um `<script>` com `new WebSocket("ws://localhost:<porta>/?level=error")` no navegador.
