# CLAUDE.md — Regras que valem sempre

Este projeto é um **gateway MCP em Python** que fica na frente do SpaceMolt.
A LLM (você, Claude Code, ou o agente autônomo em runtime) **só fala com este gateway**.
O gateway faz duas coisas:

1. **Repassa** as ferramentas cruas do SpaceMolt (mine, travel, dock, sell...).
2. **Expõe ferramentas novas de alto nível** — as "skills do jogo" (ex: mineração completa).

## Antes de escrever qualquer código

1. Leia a spec da feature em `.specs/<numero>-<nome>/`.
2. Se a spec não existe, ela é escrita **antes** do código. Sem spec, sem código.
3. Siga `.specs/constitution.md`.

## 6 regras de ouro

1. **Spec primeiro.** Nada de código sem spec.
2. **Planejar ≠ executar.** Toda skill separa "montar o plano" de "rodar o plano".
3. **Determinístico primeiro.** Decisão mecânica vira código. LLM só entra em coisa ambígua de verdade.
4. **Cada coisa no seu lugar.** Uma pasta por objetivo. Função pura sempre que der.
5. **Git por passo.** Cada passo = uma branch `NNN_descricao-curta`. Merge na master no fim. **Nunca apaga a branch.**
6. **Código em inglês, conversa em português.** Nomes de função/variável/branch em inglês. Docs e specs em português.

## Mapa do projeto

- `.specs/` — o que construir e como (spec → plan → tasks)
- `.claude/skills/` — procedimentos que **você (Claude Code)** usa pra desenvolver
- `app/` — o código do gateway (criado seguindo as specs)

## Atenção: a palavra "skill" tem 2 sentidos aqui

- **skill de desenvolvimento** = arquivo em `.claude/skills/`. Ensina **você** a construir.
- **skill do jogo** = um módulo em `app/skills/` (ex: `mining`). Uma capacidade que o gateway expõe pra LLM.

Não misture os dois. Quando este projeto fala "vamos criar uma nova skill",
quase sempre é uma **skill do jogo** (um novo módulo em `app/skills/`).
