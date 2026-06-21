---
name: git-flow
description: Disciplina de Git deste projeto. Use sempre que iniciar um passo, fazer commit, criar branch ou fazer merge. Garante uma branch por passo, merge na master e branch preservada.
---

# Git por passo

Cada passo de um `tasks.md` é uma branch. A branch nunca é apagada.

## Nome da branch

```
NNN_descricao-curta
```

- `NNN` = contador **global** do projeto, com 3 dígitos: 001, 002, 003...
  Continua entre features (a feature 0002 pode começar no passo 007).
- `descricao-curta` = inglês, minúsculo, com hífen. Ex: `mining-planner`.

Exemplos: `001_init-repo`, `005_raw-proxy`, `008_mining-planner`.

## Ciclo de um passo

```bash
git checkout master
git pull
git checkout -b 008_mining-planner      # cria a branch do passo

# ... escrever código + teste ...
# ... rodar os testes até passar ...

git add -A
git commit -m "feat(mining): planner que monta o plano de mineração"

git checkout master
git merge --no-ff 008_mining-planner    # merge preservando o ponto de junção
git push

# NÃO apagar a branch. Ela fica como histórico daquele passo.
```

## Por que `--no-ff`

Mantém um commit de merge visível, então dá pra ver na história exatamente
onde cada passo entrou. A branch fica fácil de encontrar depois.

## Regras

- Um passo por branch. Não juntar dois passos numa branch só.
- Só começar o próximo passo depois do merge do anterior na master.
- Nunca apagar branch de passo (`git branch -d` está proibido aqui).
- Commit em inglês, no formato `tipo(escopo): descrição` (feat, fix, test, docs, refactor).

## Primeiro passo do projeto

`001_init-repo`: `git init`, `.gitignore` de Python, e o primeiro commit já com
`.specs/`, `.claude/`, `CLAUDE.md` e `README.md`.
