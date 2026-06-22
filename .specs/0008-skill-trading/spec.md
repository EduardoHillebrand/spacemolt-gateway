# 0008 — Skill de Trading · spec.md

## O quê

Uma skill do jogo chamada `sell_cargo`: vende itens do cargo na estação
atual e, **quando não há comprador no mercado**, cria automaticamente uma
ordem de venda com um preço justo — em vez de simplesmente falhar e deixar
a LLM decidir o que fazer toda vez.

Cobre dois modos de uso:

- Vender **um item específico** do cargo (`item_id` + quantidade).
- Vender **todo o cargo vendável** de uma vez, preservando itens que nunca
  devem ser vendidos automaticamente (fuel cells).

## Porquê

`sell` (proxy cru, já exposto pelo gateway) só funciona quando existe alguém
comprando aquele item no momento. Quando não há comprador, a venda falha —
e hoje isso vira um erro que a LLM precisa interpretar e resolver na mão,
toda vez: olhar o mercado, calcular um preço razoável, chamar
`create_sell_order`.

Essa é uma decisão **mecânica**: o preço de uma ordem de fallback não exige
julgamento de negócio, é "um pouco melhor que o melhor preço existente no
mercado". O agente anterior que já jogou SpaceMolt antes deste gateway
existir tinha exatamente essa lógica (`SpaceMolt/agent/skills/trading.py`,
classes `SellItemSkill` e `SellAllSkill`) e funcionava bem. Esta spec adapta
essa lógica validada para o padrão planner/executor deste projeto.

Isso também substitui a venda "ingênua" usada hoje dentro da `mining_run`
(0002/0006), que apenas chama `sell` e não trata a ausência de comprador —
uma vez que esta skill existir, a mineração pode delegar a venda pra ela.

## Comportamento esperado

### Vender um item (`sell_cargo(item_id, quantity)`)

1. Tenta vender o item direto no mercado (preço de mercado).
2. Se a venda foi recusada por falta de comprador, calcula um preço de
   fallback e cria uma ordem de venda com esse preço, em vez de devolver erro.
3. Devolve o resultado: vendido direto, ou ordem criada (e com qual preço).

### Vender tudo (`sell_cargo()` sem item_id)

1. Olha o cargo atual e separa o que pode ser vendido do que deve ser
   mantido (fuel cells — combustível nunca é vendido automaticamente).
2. Para cada item vendável, repete o comportamento do modo "vender um item":
   tenta vender direto, cria ordem de fallback se não houver comprador.
3. Devolve um resumo: o que foi vendido direto, o que virou ordem (e a
   que preço), o que falhou (e por quê), e o que foi mantido (fuel cells).
4. Um item falhar não interrompe os demais — a skill processa o cargo
   inteiro e relata cada resultado individualmente.

## Cálculo do preço de fallback

Quando é preciso criar uma ordem de venda (sem comprador), o preço é
calculado a partir do livro de ofertas da estação:

- Se existe uma oferta de venda no mercado, usa um valor **um pouco abaixo**
  dela (fica na frente da fila, mais fácil de vender rápido).
- Senão, se existe uma oferta de compra, usa um valor **um pouco acima**
  dela.
- Se não há nenhuma referência de preço no mercado, usa um preço mínimo
  conservador (a skill não tenta adivinhar valor de mercado sem dado nenhum).

Esse cálculo é mecânico — a LLM pode sempre sobrepor o preço explicitamente
se quiser vender mais caro/barato, mas o fallback automático nunca exige
isso.

## Pré-condições (se faltar, a skill avisa e não roda)

- A nave está atracada numa estação com mercado (vender exige estar docado).
- Há cargo correspondente ao item pedido (no modo item específico).

## Regras

- Fuel cells (`fuel_cell`, `premium_fuel_cell`, `military_fuel_cell` e
  variantes) **nunca** são vendidos automaticamente no modo "vender tudo".
  Só são vendidos se pedidos explicitamente pelo `item_id` no modo item
  específico.
- "Sem comprador" é detectado de forma mecânica (mensagem/código de erro do
  jogo), não por inferência da LLM.
- Cada item no modo "vender tudo" é tratado de forma independente — falha
  num item não aborta a venda dos outros.
- O preço de fallback é sempre calculado a partir de dados reais do mercado
  no momento da venda, nunca de um valor fixo arbitrário (exceto o piso
  mínimo de segurança, usado só quando não há nenhuma referência).

## Fora de escopo (por agora)

- Comprar itens (`buy`) — fica para uma futura extensão desta mesma skill
  ou uma skill separada de compras.
- Arbitragem entre estações (comparar preço daqui com outra estação,
  decidir se vale viajar pra vender mais caro) — decisão de estratégia da
  LLM, não desta skill.
- Gerenciar ordens já abertas (cancelar, repor preço) — fica para uma
  skill futura de gestão de ordens.
- Trade direto com outro jogador (`trade_offer`/`trade_accept`) — é uma
  interação social, não mecânica de mercado.

## Pronto quando

- Com cargo vendável e comprador disponível no mercado, `sell_cargo` vende
  direto e devolve quanto recebeu.
- Com cargo vendável e **sem** comprador, `sell_cargo` cria uma ordem de
  venda automaticamente, com preço calculado a partir do mercado, e o
  resumo deixa claro que foi ordem (não venda direta).
- Chamado sem `item_id`, vende todo o cargo vendável, mantém as fuel cells,
  e o resumo lista o resultado de cada item.
- Sem estar atracado, a skill avisa que precisa estar numa estação e não
  tenta vender nada.
