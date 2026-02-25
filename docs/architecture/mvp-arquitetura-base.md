# MVP Escalavel - Arquitetura Base (Decisoes Fechadas)

Data de consolidacao: 2026-02-24

## Decisoes fechadas

1. Dominio de identidade no MVP: `accounts` (unifica auth + users).
2. Backend de ponta a ponta: **async** (`FastAPI async` + `SQLAlchemy 2 async` + `asyncpg`), sem mistura com stack sync.
3. Regras com vigencia temporal sem sobreposicao no Postgres usando `tstzrange` + `exclusion constraint`.
4. Jobs persistidos em tabela unica com `idempotency_key`, `status`, `attempts`, `last_error`.
5. Contrato de roadmap versionado com `roadmap_schema_version` e validacao rigida (Pydantic strict + JSON Schema).
6. Atualizacao de status no MVP via **polling**; websocket entra depois.
7. `algorithm_version` obrigatorio em todos os resultados calculados.
8. Limites do plano Free entram desde o inicio via dominio `entitlements`.

## Diagrama textual (atualizado)

```text
[Web App]
   -> HTTPS
[API FastAPI async]
   -> domains/accounts
   -> domains/immigration_rules
   -> domains/scoring
   -> domains/roadmap
   -> domains/entitlements
   -> domains/jobs
   -> PostgreSQL

[API] --enqueue--> [Redis] --> [Worker async-friendly]
[Worker] -> score engine deterministico/versionado
[Worker] -> roadmap generator (LLM + gaps concretos do score)
[Worker] -> PostgreSQL (score_result, roadmap_result, jobs)
[Worker] -> S3-compativel (opcional para anexos)

[Web] --polling--> [GET /jobs/{id}] -> status/result
```

## Estrutura de pastas backend (MVP)

```text
apps/api/app/
  core/
    config.py
    db.py
    security.py
    celery_app.py
  domains/
    accounts/
      routers.py
      services.py
      repositories.py
      models.py
      schemas.py
    immigration_rules/
      routers.py
      services.py
      repositories.py
      models.py
      schemas.py
    scoring/
      routers.py
      services.py
      repositories.py
      models.py
      schemas.py
      engine.py
    roadmap/
      routers.py
      services.py
      repositories.py
      models.py
      schemas.py
      llm_client.py
    entitlements/
      routers.py
      services.py
      repositories.py
      models.py
      schemas.py
    jobs/
      routers.py
      services.py
      repositories.py
      models.py
      schemas.py
      tasks.py
```

## DDL de referencia (constraint temporal + jobs)

```sql
CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE TABLE immigration_rule_set (
  id UUID PRIMARY KEY,
  country_code TEXT NOT NULL,
  program_code TEXT NOT NULL,
  rule_key TEXT NOT NULL,
  rule_payload JSONB NOT NULL,
  effective_from TIMESTAMPTZ NOT NULL,
  effective_to TIMESTAMPTZ,
  effective_period TSTZRANGE GENERATED ALWAYS AS (
    tstzrange(effective_from, effective_to, '[)')
  ) STORED,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (effective_to IS NULL OR effective_to > effective_from)
);

ALTER TABLE immigration_rule_set
  ADD CONSTRAINT immigration_rule_set_no_overlap
  EXCLUDE USING gist (
    country_code WITH =,
    program_code WITH =,
    rule_key WITH =,
    effective_period WITH &&
  );

CREATE TYPE job_type AS ENUM ('score_job', 'roadmap_job');
CREATE TYPE job_status AS ENUM ('pending', 'running', 'succeeded', 'failed', 'canceled');

CREATE TABLE job (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL,
  type job_type NOT NULL,
  idempotency_key TEXT NOT NULL,
  status job_status NOT NULL DEFAULT 'pending',
  attempts INT NOT NULL DEFAULT 0,
  max_attempts INT NOT NULL DEFAULT 5,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  result_ref_id UUID,
  last_error TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ,
  UNIQUE (user_id, type, idempotency_key)
);

CREATE TABLE score_result (
  id UUID PRIMARY KEY,
  job_id UUID NOT NULL REFERENCES job(id),
  algorithm_version TEXT NOT NULL,
  ruleset_version_ref UUID NOT NULL,
  input_hash TEXT NOT NULL,
  score_value NUMERIC(5,2) NOT NULL,
  breakdown JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE roadmap_result (
  id UUID PRIMARY KEY,
  job_id UUID NOT NULL REFERENCES job(id),
  algorithm_version TEXT NOT NULL,
  roadmap_schema_version TEXT NOT NULL,
  based_on_score_result_id UUID NOT NULL REFERENCES score_result(id),
  content JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

## Contrato de saida do roadmap (versionado)

Versao inicial: `roadmap_schema_version = "1.0.0"`.

Campos minimos obrigatorios no JSON:

1. `roadmap_schema_version` (string semver).
2. `summary` (string).
3. `items` (array nao vazio).
4. `items[].gap_id` (string; deve existir no score breakdown).
5. `items[].title` (string).
6. `items[].actions` (array nao vazio de strings).
7. `items[].eta_weeks` (inteiro positivo).
8. `items[].priority` (`high|medium|low`).

Regra de validacao:

1. Rejeitar resposta LLM fora do schema.
2. Rejeitar `gap_id` inexistente no score de referencia.
3. Persistir apenas payload validado.

## Polling vs websocket

Decisao de MVP: polling.

1. Endpoint: `GET /v1/jobs/{job_id}`.
2. Cliente consulta a cada `2s`, com backoff ate `10s`.
3. Timeout de UX configuravel por fluxo.
4. Websocket planejado para fase Growth.

## Entitlements desde o inicio

`entitlements` entra no MVP para garantir limites Free sem hardcode.

Estrutura minima:

1. `plan` (free, pro, etc.).
2. `plan_feature_limit` (feature_key, limit_window, limit_value).
3. `user_subscription`.
4. `usage_counter` (feature_key, period_start, period_end, used_value).

Aplicacoes no MVP:

1. Limite de `score_job` no free.
2. Limite/bloqueio de `roadmap_job` no free.
3. Enforcement no backend antes de enfileirar job.

