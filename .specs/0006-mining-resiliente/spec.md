# 0006 — Mineração Resiliente · spec.md

## O quê

Evolução da `mining_run` (0002): a skill passa a lidar com as situações reais
que aparecem numa sessão de mineração longa, em vez de assumir um mundo
perfeito (POI nunca esvazia, fuel nunca falta, só existe um tipo de depósito).

Cobre quatro facetas que faltam hoje:

1. **Depleção e realocação** — detectar quando o POI esgotou e mover pra outro
   POI minerável do mesmo sistema, sem parar a run.
2. **Survey de deep core** — quando não há mais POI minerável visível, escanear
   o sistema em busca de depósitos ocultos antes de desistir.
3. **Checagem de fuel** — não iniciar (ou continuar) um ciclo de mineração se
   não houver fuel suficiente pra voltar até a base de venda.
4. **Parada por esgotamento do sistema** — se não há ore, nem POI alternativo,
   nem depósito oculto, a run termina e vende o que já tem, em vez de falhar
   silenciosa ou ficar girando.

## Porquê

A `mining_run` atual (0002) assume que `mine()` sempre funciona e que o único
jeito de parar o laço é o cargo encher. Isso quebra em três casos comuns,
observados no agente anterior que já jogou SpaceMolt antes deste gateway
existir (`SpaceMolt/agent/skills/mining.py`):

- **Asteroides esgotam.** Minerar repetidamente no mesmo POI eventualmente
  retorna "0 unidades" ou um erro de depleção. A skill atual não distingue
  isso de uma falha real — ela já trataria como erro e pararia, mesmo
  havendo outros pontos para minerar no mesmo sistema.
- **Deep core é um depósito diferente.** Existem POIs sem depósito visível
  que só aparecem depois de `survey_system`. Ignorar isso significa desistir
  de minerar num sistema que na verdade tem recurso, só que escondido.
- **Fuel é finito.** Minerar até o cargo encher pode deixar a nave sem fuel
  pra voltar pra base — a skill atual nunca olha pro fuel.

Sem isso, a LLM precisa monitorar manualmente cada ciclo de mineração de novo
— exatamente o trabalho mecânico que o gateway deveria absorver.

## Comportamento esperado

Quando a LLM chama `mining_run`:

1. A skill checa fuel: se não houver o suficiente pra ida-e-volta até
   `home_base`, devolve aviso e não inicia.
2. Minera repetidamente no POI atual.
3. Se uma chamada de minerar indicar **depleção** (quantidade extraída = 0,
   ou mensagem de depleção), conta como uma falha nesse POI:
   - Enquanto o número de falhas consecutivas no POI for baixo, tenta de novo
     (pode ser intermitência, não depleção real).
   - Ao passar do limite, considera o POI esgotado e **realoca** para outro
     POI minerável do mesmo sistema, se existir, e continua minerando lá.
4. Se não houver nenhum outro POI minerável visível no sistema, a skill
   executa `survey_system` para tentar revelar depósitos ocultos (deep core)
   antes de desistir.
   - Se o survey revelar um novo POI minerável, a run continua lá.
   - Se não revelar nada, a run termina por esgotamento do sistema.
5. A run também termina quando: o cargo enche (caso normal, igual à 0002),
   o fuel fica abaixo do mínimo pra voltar à base, ou o sistema se esgota
   (passo 4 sem sucesso).
6. Ao terminar por qualquer um dos motivos acima, a skill volta pra
   `home_base`, atraca e vende o que coletou — igual à 0002.
7. Devolve um resumo dizendo: quanto minerou, quanto vendeu, quanto ganhou,
   quantas realocações/surveys aconteceram, e **por que parou**.

## Pré-condições (se faltar, a skill avisa e não roda)

Mantém as três da 0002 (laser instalado, está num ponto minerável, cargo tem
espaço), e adiciona:

- Fuel suficiente pra ida e volta até `home_base` (estimativa conservadora).

## Regras

- "Depleção" é mecânica: quantidade extraída = 0 ou mensagem reconhecida de
  depleção/vazio. Nunca é decisão da LLM.
- O limite de falhas consecutivas antes de considerar um POI esgotado é fixo
  e pequeno (evita ficar tentando um POI morto, mas tolera uma falha
  isolada).
- Realocação e survey são tentados **nessa ordem**: primeiro POI alternativo
  já visível, só depois survey. Survey custa uma ação de jogo, então só roda
  quando não há alternativa óbvia.
- Cada realocação ou survey conta no resumo final — a LLM precisa saber que
  a run não ficou no mesmo lugar o tempo todo.
- Fuel é checado **antes** de cada novo ciclo de mineração, não só no início
  — uma run longa pode consumir fuel ao realocar entre POIs distantes.
- Vender continua sendo só os itens coletados nesta run (um `sell` por tipo
  de item), igual à 0002.

## Fora de escopo (por agora)

- Minerar em mais de um sistema (jump entre sistemas) — fica para uma futura
  skill de exploração/rota.
- Decidir se vale a pena minerar um recurso específico (preço, raridade) —
  decisão de estratégia da LLM, não desta skill.
- Refino do minério coletado (skill futura de crafting/refino).
- Combate ou fuga caso a nave seja atacada durante a run — fora de escopo,
  a run apenas propaga o erro pra LLM decidir.

## Pronto quando

- Num sistema com dois POIs mineráveis, a run esgota o primeiro, detecta a
  depleção, realoca pro segundo automaticamente, e termina vendendo o total
  coletado dos dois.
- Num sistema sem POI minerável visível mas com depósito oculto, a run
  faz survey, encontra o depósito, e minera nele.
- Num sistema totalmente esgotado (sem POI alternativo e sem depósito
  oculto), a run termina sem erro, vende o que já tinha, e o resumo diz
  "sistema esgotado" como motivo da parada.
- Se o fuel não for suficiente pra voltar à base, a skill avisa e não inicia
  (ou interrompe a run antes de ficar sem fuel no meio do caminho).
