# Requisitos MVP Fixados

Data: 2026-02-24
Status: ativo

## Requisitos solicitados

1. Unificar `auth + users` no dominio `accounts` no MVP.
2. Backend padrao unico: `FastAPI async + SQLAlchemy async + asyncpg` (nao misturar com sync).
3. Constraint temporal de regras no Postgres com `tstzrange` + `EXCLUDE USING gist` para impedir sobreposicao de vigencia.
4. Tabela de jobs com suporte a `score_job` e `roadmap_job`, contendo `idempotency_key`, `status`, `attempts` e `last_error`.
5. Contrato de saida de roadmap versionado com `roadmap_schema_version` e validacao rigida de schema.
6. MVP com polling para status de jobs; websocket somente em fase posterior.
7. `algorithm_version` obrigatorio em todo resultado processado.
8. Dominio `entitlements` com limites Free desde o inicio (nao adiar para fase posterior).

## Observacoes de implementacao

1. Nao hardcode de regras migratorias no codigo.
2. Toda regra com vigencia temporal (`effective_from`, `effective_to`).
3. Score deve ser deterministicamente reproduzivel.
4. Roadmap deve referenciar gaps concretos do score.

## Extensoes assicronas (Prompt 06)

1. Processamento assicrono separado em `score_queue` e `roadmap_queue` via Celery.
2. `POST /assessments` e `POST /roadmaps` devem retornar `202` rapidamente e processar no worker.
3. Polling de status no MVP (`/jobs/{job_id}`, `/assessments/{id}/status`, `/roadmaps/{id}/status`).
4. Roadmap por LLM apenas para usuarios com entitlement Pro ativo (`feature_key=roadmap.pro`).
5. Contrato de roadmap com schema versionado e validacao rigida (`roadmap_schema_version`).
6. Falhas em LLM nao podem derrubar API principal; retries com backoff e estado `dead_letter`.

## Freemium e Billing (Prompt 07)

1. Modelo Freemium:
   - Free: ate 3 assessments por mes, sem roadmap IA.
   - Pro: assessments ilimitados, roadmap IA liberado, prioridade de processamento.
2. Entidades de billing obrigatorias: `Plan`, `Subscription`, `Entitlement`, `UsageCounter`, `BillingEvent`.
3. Endpoints:
   - `POST /api/v1/billing/checkout-session`
   - `POST /api/v1/billing/webhook/stripe`
   - `GET /api/v1/entitlements/me`
4. Seguranca:
   - assinatura Stripe validada no webhook;
   - plano sempre resolvido no backend;
   - idempotencia por `provider_event_id`.
5. Webhooks suportados:
   - `checkout.session.completed`
   - `invoice.paid`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
