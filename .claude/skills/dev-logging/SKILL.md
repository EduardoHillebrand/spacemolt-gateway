---
name: dev-logging
description: Hábito de logar durante o desenvolvimento em Python neste projeto. Use ao escrever qualquer arquivo .py. Garante log liberal nos níveis info/warning/error, todos roteados para o canal WebSocket de log (feature 0003-dev-log-stream).
---

# Logar quase tudo (durante o desenvolvimento)

Cada módulo Python deste projeto loga liberalmente. Os logs saem por um canal
WebSocket (a feature `0003-dev-log-stream`) e só são entregues a quem está
escutando — então pode logar à vontade, não há custo se ninguém assina.

## Como cada módulo loga

No topo de todo arquivo:

```python
import logging

log = logging.getLogger(__name__)
```

Usar `__name__` faz o nome do módulo aparecer no log automaticamente.
**Não** criar logger próprio nem escrever em socket na mão. Só usar `logging`.
O roteamento pro WebSocket é montado uma vez no `setup` (feature 0003) e vale
pra todo o projeto.

## Os 3 níveis e quando usar cada um

- **info** — o fluxo normal. "Entrei na função", "montei o plano com 4 passos",
  "minerei 1 unidade, cargo em 7/10". É o nível barulhento e tudo bem: é opt-in.
- **warning** — algo estranho mas recuperável. "Cargo já estava cheio, pulando
  mineração", "resposta demorou, tentando de novo".
- **error** — falhou. "Sem laser de mineração", "o SpaceMolt recusou a chamada".

## Logar bastante, nestes pontos

- Ao entrar numa função importante, com os argumentos que importam (em info).
- Antes e depois de uma chamada ao jogo (`game_client`), em info.
- A cada volta de um laço (ex: cada `mine` do `mine_until`), em info.
- Toda pré-condição que falha, em error ou warning, dizendo o que falta.
- Toda decisão "fui por aqui porque...", em info.

## NUNCA logar

- Sessão / token do SpaceMolt, senhas, segredos. O `game_client` segura isso e
  não loga o valor. Se precisar, loga "sessão presente: sim/não", nunca o valor.

## Formato da mensagem

- Mensagem curta em português, no presente. Dados em `extra` quando der:
  ```python
  log.info("montando plano de mineração", extra={"cargo_free": 10, "has_laser": True})
  ```
- Não montar string gigante concatenada. Mensagem + dados separados.

## Por que isso ajuda no agente autônomo

Quando o agente roda sozinho, você abre um cliente WebSocket assinando `info` e
vê em tempo real o que ele está pensando e fazendo. Se só quer ver o que deu
errado, assina `error`. Sem reabrir nada, sem mexer no código.
