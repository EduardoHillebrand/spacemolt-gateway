# 0001 — Núcleo do Gateway · spec.md

## O quê

Um servidor MCP em Python que funciona como **porta de entrada única** para o
SpaceMolt. A LLM se conecta só nele.

## Porquê

Hoje a LLM fala direto com o MCP do SpaceMolt e precisa orquestrar tudo na mão.
Queremos um lugar nosso onde dá pra (a) repassar as ferramentas cruas e
(b) adicionar ferramentas novas de alto nível (skills) sem a LLM perceber a diferença.

## Comportamento esperado

1. O gateway sobe como um servidor MCP e fica esperando conexão.
2. Ele oferece à LLM duas categorias de ferramenta:
   - **Cruas (proxy):** repassam 1:1 para o SpaceMolt. Marcadas como "baixo nível".
   - **Skills:** ferramentas novas, de alto nível, que o projeto vai criando.
3. Quando a LLM chama uma ferramenta crua, o gateway encaminha pro SpaceMolt e
   devolve a resposta sem mexer.
4. Existe **um único ponto** que fala com o SpaceMolt (o `game_client`). Nada
   no projeto fala com o jogo por fora dele.

## Regras

- Toda credencial/sessão do SpaceMolt fica no `game_client`, nunca espalhada.
- Ferramenta crua é marcada como "baixo nível — prefira a skill quando existir".
- O gateway não tem lógica de jogo nenhuma. Lógica mora nas skills.

## Fora de escopo (por agora)

- Esconder as ferramentas cruas (vamos expor as duas no começo).
- Qualquer skill específica (mineração entra na feature 0002).
- Autenticação avançada, cache, métricas.

## Pronto quando

- A LLM consegue conectar no gateway e enxergar as ferramentas cruas.
- Uma chamada crua (ex: `get_state`) passa pelo gateway e volta certa.
