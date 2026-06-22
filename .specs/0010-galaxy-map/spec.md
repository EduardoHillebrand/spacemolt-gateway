# 0010 — Galaxy Map (Mapeamento da Galáxia) · spec.md

## O quê

Um serviço de background que mapeia **toda a galáxia** do SpaceMolt usando a
API HTTP pública (sem autenticação), persiste os dados em disco, e expõe uma
tool `galaxy_info` para o agente consultar informações de sistemas, estações e
serviços — antes de planejar viagens, encontrar combustível, ou decidir onde
vender.

## Porquê

Hoje o agente enxerga só o que está em volta dele: o sistema atual, as
conexões diretas e o que o `get_status` retorna. Para planejar uma rota longa
ele precisa chamar o `find_route` do jogo repetidamente, sem saber de antemão
se os sistemas no caminho têm combustível, base de reparo ou mercado.

O projeto antigo (`SpaceMolt/agent/agent.py`) resolveu isso com dois fatos
importantes:

1. A API pública `GET https://game.spacemolt.com/api/stations` retorna **todas
   as estações da galáxia em uma única request**, incluindo quais serviços cada
   uma oferece (refuel, repair, shipyard, market). Sem autenticação.
2. A API pública `GET https://game.spacemolt.com/api/map/system/{system_id}`
   retorna os POIs detalhados de um sistema (policia, recursos mineráveis, etc.).
   Sem autenticação.

Combinando essas fontes em background, o gateway acumula um mapa completo que
o agente pode consultar antes de agir — transformando decisões de navegação que
hoje exigem múltiplas chamadas ao jogo em uma simples consulta local.

## Comportamento esperado

### No startup (via lifespan do servidor)

1. O gateway inicia a task de background do mapeamento.
2. O mapper chama `GET /api/stations` imediatamente — **uma request** traz
   todas as estações. Salva quais sistemas têm base e quais serviços oferecem.
3. Em seguida, começa a varrer sistemas um a um via `/api/map/system/{id}`,
   com delay de 1–3 s entre cada request para não sobrecarregar a API pública.
   Uma galáxia típica leva ~15–20 min para ser mapeada completamente.
4. Após varrer tudo, aguarda 5 min e repete (dados mudam com o tempo).

### Via tool `galaxy_info`

O agente chama `galaxy_info(query)` com uma das opções abaixo:

| `query` | Retorna |
|---|---|
| `"system:<nome>"` | POIs, police_level, has_base, serviços, conexões do sistema |
| `"station:<nome_sistema>"` | Serviços da estação nesse sistema (refuel, repair, etc.) |
| `"nearest_fuel:<nome_sistema>"` | Sistema mais próximo (em conexões) com refuel disponível |
| `"systems_with:<serviço>"` | Lista de sistemas que oferecem `refuel`, `repair`, `shipyard` ou `market` |
| `"empire:<nome>"` | Lista de sistemas daquele império |
| `"map_status"` | Quantos sistemas já foram mapeados, quando foi a última atualização |

Se o sistema pedido ainda não foi mapeado (`basic_only` ou ausente), a tool
devolve o que tiver e avisa que os dados podem estar incompletos.

### Persistência

Os dados ficam em `data/galaxy_map.json` dentro do diretório de trabalho do
gateway. O arquivo é atualizado incrementalmente a cada sistema escaneado. O
gateway relê o arquivo existente no startup — dados da sessão anterior
continuam válidos e não são varridos novamente desnecessariamente.

## Regras

- As chamadas HTTP são **sem autenticação** — a API pública do SpaceMolt não
  exige session_id para os endpoints de mapa e estações.
- O mapper nunca bloqueia o gateway — roda como `asyncio.Task`, completamente
  em background. Falhas em requests individuais são registradas no log e
  ignoradas (a próxima passagem tentará de novo).
- O delay entre requests (1–3 s aleatório) evita parecer um crawler agressivo
  e respeita o rate limit da API pública.
- A tool `galaxy_info` responde do cache em disco — **nunca faz chamada HTTP
  no caminho crítico** de uma ação do agente. A latência da tool é
  essencialmente zero.
- Se `data/galaxy_map.json` não existir (primeira execução), o gateway sobe
  normalmente — a tool informa que o mapa ainda está sendo construído.
- O serviço HTTP do mapper é **independente do MCP transport** — funciona
  tanto com `StubTransport` quanto com o transport real (0005). Não depende
  de session_id.

## Fora de escopo (por agora)

- Pathfinding (cálculo de rota ótima entre sistemas) — o `find_route` do jogo
  já faz isso via MCP. O galaxy map fornece o *contexto* (quais sistemas têm
  o quê), não a rota.
- Dados de mercado por sistema — preços mudam por minuto, cache seria inútil.
- Autenticação na API HTTP — os endpoints usados são todos públicos.
- Múltiplas galáxias ou servidores alternativos do SpaceMolt.

## Pronto quando

- Gateway sobe → em até 30 s, `galaxy_info("map_status")` mostra que estações
  foram carregadas (mesmo antes da varredura completa).
- `galaxy_info("system:Sol")` retorna POIs e serviços do sistema Sol
  (após a varredura chegar a esse sistema).
- `galaxy_info("nearest_fuel:alpha_centauri")` retorna o sistema mais próximo
  com refuel disponível, sem chamar o jogo.
- `galaxy_info("systems_with:shipyard")` lista todos os sistemas com estaleiro.
- Após ~20 min, `map_status` mostra que todos os sistemas foram varridos.
- Reiniciar o gateway não apaga o mapa — a sessão anterior é aproveitada.
