# imigrai backend bootstrap

Bootstrap do backend FastAPI para o SaaS de imigracao.

## Stack

- Python 3.12+
- FastAPI
- SQLAlchemy 2 (async)
- Alembic
- PostgreSQL
- Redis
- Celery + Celery Beat
- uv
- Docker Compose

## Estrutura principal

- `app/api`: roteadores HTTP (health + v1)
- `app/core`: config, seguranca, observabilidade
- `app/db`: base, sessao e migracoes
- `apps/*`: dominios modulares

## Subir local com Docker

```bash
docker compose up --build
```

Endpoints:

- `GET /health/live`
- `GET /health/ready`
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `GET /api/v1/auth/me`
- `POST /api/v1/billing/checkout-session`
- `POST /api/v1/billing/webhook/stripe`
- `GET /api/v1/entitlements/me`
- `POST /api/v1/assessments` (async -> `202`)
- `GET /api/v1/assessments/{assessment_id}/status`
- `GET /api/v1/assessments/{assessment_id}/breakdown`
- `POST /api/v1/roadmaps` (Pro entitlement, async -> `202`)
- `GET /api/v1/roadmaps/{roadmap_id}/status`
- `GET /api/v1/roadmaps/{roadmap_id}`
- `GET /api/v1/jobs/{job_id}` (polling)
- `GET /openapi.json`
- `GET /docs`
- `GET /redoc`

## Migrações

```bash
alembic upgrade head
```

## Seed de Regras MVP

Fixtures iniciais para 3 paises (`CA`, `AU`, `PT`):

```bash
python scripts/seed_mvp_rules.py
```

## Score Formula

- `docs/score/formula-score.md`

## Freemium MVP

- Free: `3 assessments/mes`, sem roadmap IA.
- Pro: assessments ilimitados, roadmap IA liberado, prioridade de processamento.
- Stripe webhook suportado:
  - `checkout.session.completed`
  - `invoice.paid`
  - `customer.subscription.updated`
  - `customer.subscription.deleted`

## Qualidade

```bash
uv pip install -e .[dev]
ruff check .
black --check .
pytest
pre-commit install
```
