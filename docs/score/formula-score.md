# Formula de Score Deterministica (MVP)

## Objetivo
Calcular o **Score de Chance de Sucesso** de forma auditavel, reprodutivel e sem hardcode por pais.

## Entradas minimas obrigatorias

1. `idade`
2. `escolaridade`
3. `profissao` (com `profissao_codigo` padronizado quando aplicavel)
4. `idiomas`
5. `renda_atual`

## Pipeline da engine

1. Normalizacao de perfil
2. Passo 1: validacoes bloqueantes
3. Passo 2: pontuacao acumulada (somente regras nao bloqueantes)
4. Normalizacao do score bruto para escala `0-100`
5. Classificacao em faixa

## Avaliacao de regras

Cada `RuleGroup` possui:

- `conditions` com `operator` + `value_json`
- `match_operator` (`all`/`any`)
- `outcomes` com `score_delta`, `is_blocking`, `explanation_message`

A aplicacao da regra e 100% baseada nos dados em banco.

## Operadores suportados

- `eq`, `ne`, `gt`, `gte`, `lt`, `lte`, `between`, `in`, `not_in`, `exists`

## Formula de normalizacao

Seja:

- `raw_score`: soma de `score_delta` aplicados (nao bloqueantes)
- `min_possible`: soma de todos os deltas negativos possiveis
- `max_possible`: soma de todos os deltas positivos possiveis

Formula:

```text
normalized_score = ((raw_score - min_possible) / (max_possible - min_possible)) * 100
```

Com clamp para `[0, 100]` e arredondamento para 2 casas.

## Faixas

- `baixo`: score `< 40`
- `medio`: score `>= 40` e `< 70`
- `alto`: score `>= 70`

## Reprodutibilidade

A engine persiste:

- `algorithm_version`
- `rules_version_hash`
- `program_version_id`
- breakdown detalhado por item

`rules_version_hash` e gerado via SHA-256 do payload canonico da versao do programa + regras.

## Explicabilidade

Cada item do breakdown inclui:

- `rule_group_id` e `rule_group_code`
- `rule_outcome_id`
- `score_delta`
- `is_blocking`
- `condition_checks` (campo, operador, valor esperado, valor observado, match)

Com isso, a pergunta **"qual regra gerou este score?"** e respondida de forma objetiva.
