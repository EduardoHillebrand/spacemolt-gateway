# 0007 — Skill de Navegação · spec.md

## O quê

Uma skill do jogo chamada `navigate_to`: dado um destino (sistema, ou
sistema + POI), **leva a nave até lá**, decidindo sozinha quantos saltos
fazer, quando reabastecer, e quando atracar/desatracar — em vez de a LLM
chamar `travel`/`jump`/`dock`/`undock`/`refuel` manualmente um por um.

`travel` e `jump` já existem como ferramentas cruas no gateway (proxies da
0004). Esta skill **não substitui** essas ferramentas — ela é uma camada de
alto nível por cima, pra quando o destino é longe ou desconhecido e a LLM
não quer (ou não devia) calcular rota e fuel na mão.

## Porquê

Hoje a LLM que quer ir de um sistema a outro precisa: descobrir a rota,
verificar se tem fuel suficiente, parar pra reabastecer no meio do caminho
se precisar, desatracar antes de viajar, atracar quando chegar. Isso é
decisão **mecânica** — exatamente o tipo de coisa que a constituição diz
pra tirar da LLM (regra 3: determinístico primeiro).

O agente anterior que já jogou SpaceMolt antes deste gateway existir tinha
essa lógica implementada (`SpaceMolt/agent/skills/navigation.py`,
classe `TravelToSkill`) e funcionava chamada repetidamente, um passo por vez,
até o destino ser alcançado. Esta spec adapta essa mesma lógica validada
para o padrão planner/executor deste projeto.

## Comportamento esperado

Quando a LLM chama `navigate_to(destination)`:

1. A skill olha o estado atual (sistema, POI, docado ou não, fuel).
2. Se já está no destino exato (mesmo sistema e mesmo POI, quando um POI foi
   pedido), não faz nada e devolve "já está no destino".
3. Senão, monta um plano de rota:
   - Se o destino é um POI do **sistema atual**, o plano é: desatracar (se
     preciso) → `travel` até o POI.
   - Se o destino é outro **sistema**, calcula a rota completa (sistema a
     sistema) e monta uma sequência de saltos, intercalando paradas de
     reabastecimento sempre que o fuel projetado para um salto ficar abaixo
     do mínimo seguro.
4. Executa o plano passo a passo, salto por salto:
   - Antes de cada salto, confere o fuel. Se estiver baixo e houver uma base
     no sistema atual, desvia pra atracar e reabastecer antes de continuar.
   - Se estiver baixo e **não** houver base no sistema atual, a skill
     interrompe e avisa — não tenta o salto e fica sem fuel no meio do nada.
5. Ao chegar no sistema de destino, se um POI foi pedido, viaja até ele.
6. Devolve um resumo: quantos saltos deu, quantas paradas de reabastecimento
   fez, onde parou, e se chegou ao destino ou foi interrompida (e por quê).

## Pré-condições (se faltar, a skill avisa e não roda)

- O destino existe (sistema ou POI reconhecido pelo jogo).
- Há pelo menos uma rota conhecida até o destino (`find_route` retorna algo).

Se o destino for desconhecido ou não houver rota, a skill devolve isso
claramente — não tenta adivinhar.

## Regras

- "Fuel baixo" é um limiar mecânico fixo (uma margem de segurança acima do
  mínimo pra completar o próximo salto), não uma escolha da LLM a cada vez.
- Reabastecer só acontece atracado. A skill atraca automaticamente quando
  precisa reabastecer, e desatraca de novo antes de continuar a rota.
- A skill nunca tenta um salto que ela mesma calcula que vai deixar a nave
  sem fuel no destino — nesse caso, ela já teria desviado pro reabastecimento
  no passo anterior, ou interrompido se isso não for possível.
- Cada chamada de `navigate_to` tenta completar a rota inteira numa única
  execução (loop interno), não apenas um passo por chamada — diferente do
  agente anterior, que era chamado em loop pela própria LLM a cada tick.
- Se a rota for interrompida (sem fuel e sem base por perto, ou erro do
  jogo num salto), a skill para imediatamente e devolve o estado em que a
  nave ficou — nunca insiste tentando o mesmo salto repetidamente.

## Fora de escopo (por agora)

- Evitar sistemas perigosos (`police_level` baixo, risco de PvP) — decisão
  de estratégia da LLM, não desta skill.
- Navegação durante combate ou fuga.
- Escolher a rota mais barata em fuel entre várias alternativas — usa a rota
  que `find_route` devolver.
- Pathfinding por bearing numérico (Pathfinder Drive) — só rotas por nome de
  sistema/POI conhecido.

## Pronto quando

- Pedido um POI do sistema atual, a skill desatraca (se preciso) e viaja
  direto, sem cálculo de rota multi-sistema.
- Pedido um sistema distante com fuel de sobra, a skill salta sistema a
  sistema até chegar, sem nenhuma parada.
- Pedido um sistema distante com fuel insuficiente no meio do caminho, a
  skill desvia pra reabastecer numa base do trajeto e continua até chegar.
- Pedido um destino sem rota conhecida ou sem base de reabastecimento
  disponível quando necessário, a skill avisa claramente o motivo e não
  deixa a nave largada sem fuel.
