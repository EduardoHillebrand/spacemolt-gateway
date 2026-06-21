# 0002 — Skill de Mineração · spec.md

## O quê

Uma skill do jogo chamada `mining_run`: **minera até o cargo encher, volta pra
base e vende o minério**. A LLM chama uma ferramenta só e o gateway faz tudo.

## Porquê

É uma tarefa repetitiva e mecânica. Não faz sentido a LLM ficar chamando `mine`
trinta vezes e checando o cargo a cada vez. Isso é trabalho de código determinístico.

É também o melhor exemplo pra estudar SDD, porque tem um detalhe que a viagem
simples não tem: **"minerar até encher" é um laço de tamanho desconhecido**.
Não dá pra saber quantas chamadas de `mine` vão ser. Isso obriga a separar bem
o plano (que descreve a intenção) da execução (que roda o laço de verdade).

## Comportamento esperado

Quando a LLM chama `mining_run`:

1. A skill olha o estado atual.
2. Monta um plano:
   - minerar repetidamente **até o cargo encher**;
   - viajar de volta pra base de origem;
   - atracar;
   - vender todo o minério.
3. Executa o plano passo a passo.
4. Devolve um resumo: quanto minerou, quanto vendeu, quanto ganhou, onde parou.

## Pré-condições (se faltar, a skill avisa e não roda)

- Ter laser de mineração instalado.
- Estar num ponto que dá pra minerar.
- Ter espaço no cargo.

Se faltar qualquer uma, a skill devolve um resultado claro dizendo **o que falta**.
Ela não tenta adivinhar nem corrigir sozinha (isso é decisão da LLM).

## Regras

- O "cargo encheu?" é uma checagem mecânica do executor, não da LLM.
- A base de origem é a base de onde a nave saiu (ou a mais próxima com compra de minério).
- Vender = vender só o minério, não o cargo inteiro.

## Fora de escopo (por agora)

- Escolher **qual** asteroide minerar (assume que já está num ponto bom).
- Ir até o asteroide (isso é da futura skill de viagem).
- Decidir se vale a pena minerar (decisão de estratégia, não desta skill).

## Pronto quando

- Com cargo vazio num ponto minerável, `mining_run` enche, volta, vende e
  devolve um resumo coerente.
- Sem laser, devolve "falta laser de mineração" e não faz nada.
