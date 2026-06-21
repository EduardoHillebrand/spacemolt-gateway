# Como funciona o `.specs/`

Aqui mora a especificação do sistema. **A spec vem antes do código.**

## O fluxo de 3 documentos (por feature)

Cada feature tem sua pasta `NNNN-nome/` com até 3 arquivos, nesta ordem:

| Arquivo | Responde | Pode falar de tecnologia? |
|---------|----------|---------------------------|
| `spec.md` | O **quê** e o **porquê** | Não. Só comportamento e regras. |
| `plan.md` | O **como** | Sim. Stack, arquitetura, arquivos. |
| `tasks.md` | Os **passos** | Lista pequena e checável. Cada item vira uma branch. |

Por que separar? Porque dá pra revisar o "o quê" sem se perder em detalhe técnico,
e dá pra trocar o "como" sem reescrever o "o quê".

## A constituição

`constitution.md` são as regras que valem pra **todas** as features (clean code,
git, planejar≠executar). Não é uma feature, é a base. Leia antes de tudo.

## Numeração

- Features: `0001-`, `0002-`, ... na ordem em que entram.
- A constituição não tem número (é fundação, não feature).

## Como uma task vira uma branch

Cada item de `tasks.md` é um passo pequeno. O passo vira uma branch:

```
NNN_descricao-curta      ex: 003_mining-planner
```

O `NNN` é um contador **global** do projeto (001, 002, 003...), pra história
do Git ficar linear e fácil de ler. Detalhes em `.claude/skills/git-flow`.

## Ordem de leitura recomendada

1. `constitution.md`
2. `0001-gateway-core/` (spec → plan → tasks)
3. `0003-dev-log-stream/` (canal de log — construído antes da mineração)
4. `0002-skill-mining/` (spec → plan → tasks)

> Repare: a numeração da pasta é a ordem em que a feature foi **criada**, não
> necessariamente a ordem em que é **construída**. O log (0003) nasceu depois mas
> é construído antes da mineração (0002). Quem manda na ordem de build são os
> números das branches em `tasks.md` (007–010 do log vêm antes de 011–015 da mineração).
