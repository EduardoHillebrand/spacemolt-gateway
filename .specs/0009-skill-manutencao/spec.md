# 0009 — Skill de Manutenção da Nave · spec.md

## O quê

Uma skill do jogo chamada `maintain_ship`: cuida da saúde da nave —
**reabastecer combustível** e **reparar o casco** — e, quando a estação
atual não tem o que é preciso, diz exatamente o que falta em vez de só
devolver um erro genérico.

Cobre dois cuidados, sempre feitos atracado:

- **Reabastecer**: enche o tanque de combustível.
- **Reparar**: recupera o casco (hull) danificado.

## Porquê

`refuel` e `repair` (proxies crus, já expostos pelo gateway) só funcionam
atracado, e podem falhar por um motivo específico e comum: **a estação
atual não tem combustível em estoque**. Hoje isso vira um erro cru que a
LLM precisa interpretar.

O agente anterior que já jogou SpaceMolt antes deste gateway existir tinha
essa lógica (`SpaceMolt/agent/skills/maintenance.py`, classes `RefuelSkill`
e `RepairSkill`): detectar especificamente o erro de "sem combustível nesta
estação" e sugerir um sistema próximo que tenha combustível. Esta spec
adapta esse comportamento, mas delega a parte de "ir até lá" para a skill
de navegação (0007 — `navigate_to`) em vez de duplicar lógica de rota
dentro desta skill, seguindo a regra de "cada coisa no seu lugar" da
constituição.

## Comportamento esperado

### Reabastecer (`maintain_ship(action="refuel")`)

1. Confere se está atracado. Se não estiver, avisa e não tenta.
2. Tenta reabastecer.
3. Se a estação **não tem combustível em estoque**, a skill reconhece esse
   erro especificamente (não é "atracado errado", nem "sem dinheiro") e
   devolve isso de forma clara, sugerindo que a LLM use `navigate_to` para
   ir a outra estação — sem tentar calcular a rota ela mesma.
4. Qualquer outro erro de reabastecimento é devolvido como está, sem
   tentar reinterpretar.

### Reparar (`maintain_ship(action="repair")`)

1. Confere se está atracado. Se não estiver, avisa e não tenta.
2. Tenta reparar o casco.
3. Devolve o resultado: quanto de hull foi recuperado e o custo em créditos.

### Cuidar de tudo de uma vez (`maintain_ship(action="full")`)

1. Reabastece primeiro, depois repara — só continua para o reparo se o
   reabastecimento não tiver sido bloqueado por falta de estar atracado
   (um reabastecimento que falhe por falta de estoque não impede a
   tentativa de reparo, já que são problemas independentes).
2. Devolve um resumo combinado das duas ações.

## Pré-condições (se faltar, a skill avisa e não roda)

- A nave está atracada numa estação (reabastecer e reparar exigem isso).

## Regras

- "Sem combustível nesta estação" é reconhecido de forma mecânica
  (código/mensagem de erro do jogo), não por inferência da LLM.
- Esta skill **não** calcula rota nem viaja — quando a estação não tem
  combustível, ela só informa o fato. Ir até outro lugar é trabalho da
  skill de navegação (0007).
- Reabastecer e reparar são independentes: a falha de um não esconde o
  resultado do outro no modo `full`.
- Reparo é sempre na estação atual (paga em créditos) — reparo em campo
  com kit, ou reparo de módulo específico, ficam fora desta skill (ver
  Fora de escopo).

## Fora de escopo (por agora)

- Reparo em campo (`repair` com kit de reparo, fora de estação) — fica
  para uma skill futura, se o jogo exigir isso fora de combate.
- Reparo de módulo individual (`repair_module`, desgaste de equipamento) —
  fica para uma skill futura, junto da gestão de módulos/fitting.
- Calcular ou executar a rota até outra estação com combustível — isso é
  da skill de navegação (0007), esta skill só informa a necessidade.
- Seguro de nave (`buy_insurance`) — é uma decisão financeira/estratégica
  da LLM, não manutenção mecânica.

## Pronto quando

- Atracado, com combustível disponível na estação, `maintain_ship(action="refuel")`
  reabastece e devolve quanto foi reabastecido.
- Atracado, sem combustível disponível na estação, a skill devolve uma
  mensagem clara dizendo que esta estação não tem combustível — distinta
  de qualquer outro tipo de erro.
- Atracado, com casco danificado, `maintain_ship(action="repair")` repara e
  devolve quanto de hull foi recuperado e o custo.
- Sem estar atracado, qualquer ação desta skill avisa que precisa atracar
  primeiro e não tenta nada no jogo.
