# 02. Arquitetura da Solução

## Visão em camadas

1. Interface Web (`frontend/`) consome API REST.
2. API (`app/main.py`) aplica middlewares, autenticação, rate limit e roteamento.
3. Serviços de domínio (`apps/*/services.py`) orquestram regras de negócio.
4. Repositórios (`apps/*/repositories.py`) encapsulam acesso ao banco.
5. Worker assíncrono (`Celery`) executa score, roadmap e ingestão.
6. Persistência em `PostgreSQL` + mensageria/locks simples via `Redis`.

## Componentes e responsabilidades

- `api`: ciclo HTTP síncrono e enfileiramento de tarefas pesadas.
- `worker`: execução de jobs com retry exponencial e dead-letter.
- `beat`: agenda recorrente para ingestão automática.
- `postgres`: dados transacionais, regras, resultados, billing e histórico.
- `redis`: broker/result backend do Celery + rate limiter distribuído.
- `prometheus/grafana`: métricas técnicas e de negócio.

## Padrões adotados

- Arquitetura modular por domínio (`apps/`), com separação `models/schemas/repositories/services/tasks`.
- Processamentos de longa duração via `202 Accepted` + polling por `job_id`.
- Idempotência em operações críticas (assessment, roadmap, webhook Stripe).
- Controle de acesso por JWT + RLS context (quando suportado).
- Fallback resiliente em dependências externas (rate limit fail-open, LLM fallback, gateway retries).

## Segurança de borda

- Middlewares:
  - CORS configurável.
  - `TrustedHostMiddleware`.
  - `HTTPSRedirectMiddleware` opcional.
  - Limite de tamanho de request.
  - Security headers (CSP, X-Frame-Options, HSTS em staging/prod).
- JWT com `access` e `refresh`, validação de tipo e expiração.
- Token interno (`x-internal-token`) para endpoints de ingestão administrativa.

## Escalabilidade

- Separação natural entre API e workers.
- Filas dedicadas:
  - `score_queue`
  - `roadmap_queue`
  - `ingestion_queue`
  - `dead_letter_queue`
- Priorização de job (ex.: Pro com prioridade alta no score).

