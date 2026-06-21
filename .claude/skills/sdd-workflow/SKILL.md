---
name: sdd-workflow
description: Fluxo Spec Driven Development deste projeto. Use sempre que for criar uma feature nova, uma skill nova do jogo, ou antes de escrever qualquer código. Garante a ordem spec -> plan -> tasks -> código.
---

# Fluxo SDD

Seguir esta ordem para qualquer feature ou skill nova. Nunca pular etapa.

## Ordem obrigatória

1. **spec.md** — descrever o quê e o porquê. Só comportamento e regras.
   Proibido falar de tecnologia (linguagem, biblioteca, arquivo) aqui.
2. **plan.md** — descrever o como. Stack, arquitetura, arquivos, decisões.
3. **tasks.md** — quebrar em passos pequenos. Cada passo deve caber numa branch
   e ser checável ("pronto quando...").
4. **Código** — só agora. E seguindo o plan.

## Onde ficam

Em `.specs/NNNN-nome-da-feature/`. Numerar na ordem de entrada (0001, 0002...).

## Antes de codar uma feature

1. Ler `.specs/constitution.md`.
2. Ler os 3 documentos da feature.
3. Conferir que cada task tem critério de "pronto quando".

## Como escrever uma boa spec

- Frases curtas. Comportamento observável.
- Listar pré-condições e o que acontece se falharem.
- Ter uma seção "Fora de escopo" pra travar o crescimento da feature.
- Ter "Pronto quando" com critérios verificáveis.

## Como escrever um bom plan

- Mostrar a árvore de arquivos da feature.
- Marcar o que é função pura e o que tem efeito colateral.
- Dizer como testar **sem** depender de serviço externo.

## Regra de parada

Se a spec não estiver clara, parar e perguntar. Não preencher buraco com suposição.
