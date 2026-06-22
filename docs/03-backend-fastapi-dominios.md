# 03. Backend (FastAPI + Domínios)

## Entrypoint

- `app/main.py` inicializa FastAPI, logging estruturado e middlewares.
- `app/api/router.py` agrega:
  - `/health/*`
  - `/countries*` (catálogo público)
  - `/api/v1/*` (domínios autenticados e internos)

## Endpoints principais (v1)

### Autenticação

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `GET /api/v1/auth/me`

### Assessments (score)

- `POST /api/v1/assessments` -> `202` (assíncrono)
- `GET /api/v1/assessments/{assessment_id}/status`
- `GET /api/v1/assessments/{assessment_id}/breakdown`

### Roadmaps

- `POST /api/v1/roadmaps` -> `202` (assíncrono, exige entitlement Pro)
- `GET /api/v1/roadmaps/{roadmap_id}/status`
- `GET /api/v1/roadmaps/{roadmap_id}`

### Jobs

- `GET /api/v1/jobs/{job_id}` (polling de status)

### Billing e entitlements

- `POST /api/v1/billing/checkout-session`
- `POST /api/v1/billing/webhook/stripe`
- `GET /api/v1/entitlements/me`

### Regras dinâmicas (CRUD)

- `POST/GET/PATCH` de países, programas, versões, grupos, condições e outcomes.
- `POST /program-versions/{id}/activate` com opção `force` para arquivar conflitos.

### Ingestão (interno)

- `POST /api/v1/ingestion/source-registry/seed`
- `GET /api/v1/ingestion/source-registry`
- `POST /api/v1/ingestion/reprocess-source`
- `GET /api/v1/ingestion/runs/{run_id}`

### Profile Match

- `POST /api/v1/profile-match/submit`
- `POST /api/v1/profile-match/claim`
- `GET /api/v1/profile-match/{submission_id}/results`

## Catálogo público

- `GET /countries`
- `GET /countries/{country_code}/programs`

Retorna países/programas ativos e fontes de referência do programa.

## Serviços de domínio

- `AuthService`: cadastro/login, hash de senha e emissão de tokens.
- `AssessmentsService`: idempotência, consumo de quota, snapshot de perfil, enfileiramento e persistência de resultado.
- `RoadmapsService`: pré-condições (assessment concluído + entitlement), geração com provider LLM e validação de contrato.
- `BillingService`: baseline de acesso, checkout Stripe, webhook idempotente, sincronização de assinatura e entitlements.
- `IngestionPipelineService`: fetch, extração, diff, publicação e quarentena de fontes.
- `ProfileMatchService`: ranking por país com algoritmo heurístico (`country-fit-v1`).

## Jobs assíncronos (Celery)

- `apps.assessments.tasks.process_assessment_task`
- `apps.roadmaps.tasks.generate_roadmap_task`
- `apps.ingestion.tasks.ingest_source_task`
- `apps.ingestion.tasks.dispatch_scheduled_ingestion` (via beat)

Padrão de falha:

- Erro transitório -> retry exponencial.
- Erro definitivo ou estouro de retries -> marca `dead_letter` e emite evento.

