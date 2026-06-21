# 0003 — Canal de log via WebSocket · spec.md

## O quê

Um canal de log que transmite os logs do projeto por WebSocket, ao vivo.
Quem quer ver, conecta e assina um nível. Quem não conecta, não recebe nada
(e nada fica guardado).

## Porquê

Durante o desenvolvimento e quando o agente roda sozinho, a gente quer enxergar
o que está acontecendo sem abrir arquivo de log nem parar o programa. Basta
conectar um cliente WebSocket e olhar. E poder filtrar por gravidade.

## Os 3 níveis

Por gravidade, do mais leve ao mais grave: **info** < **warning** < **error**.

## Regra de assinatura (a parte central)

Ao conectar, o cliente escolhe um nível. Ele recebe aquele nível **e todos os
mais graves**:

| Assinou | Recebe |
|---------|--------|
| `error` | só error |
| `warning` | warning + error |
| `info` | info + warning + error (tudo) |

Se o cliente não disser o nível, assume `info` (recebe tudo).

## Comportamento esperado

1. O canal sobe junto com o gateway, numa porta WebSocket própria.
2. Qualquer log do projeto (via `logging` do Python) é empurrado pro canal.
3. Para cada cliente conectado, o canal entrega só os logs do nível que ele assinou
   pra cima.
4. **Sem cliente conectado, nada é entregue e nada é guardado.** O programa não
   muda de comportamento nem fica mais lento por causa do log.
5. Logar **nunca** pode travar ou quebrar o programa principal. Se o canal estiver
   sobrecarregado, ele descarta log antigo — nunca segura a execução.

## O que cada log carrega

- nível (info/warning/error)
- nome do módulo de origem (vem do `getLogger(__name__)`)
- a mensagem
- dados extras (quando houver)
- hora

## Regras

- Não guarda histórico. É ao vivo. Conectou tarde, perdeu o que passou.
- Não loga segredo nenhum (a regra de não logar token vem da skill `dev-logging`).
- Os módulos do projeto **não** falam com este canal direto. Eles só usam
  `logging`; o roteamento é montado num único lugar.

## Fora de escopo (por agora)

- Guardar log em arquivo ou banco.
- Autenticação no WebSocket (é local; se for expor pelo túnel, tratar depois).
- Interface visual. Por enquanto basta um cliente WebSocket simples.

## Pronto quando

- Subo o gateway, conecto um cliente assinando `error` e só vejo erros.
- Conecto outro assinando `info` e vejo os 3 níveis.
- Desconecto todos e o gateway segue rodando igual, sem acumular nada.
