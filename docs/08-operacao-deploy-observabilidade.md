# 08. Operação, Deploy e Observabilidade

## Subida local

Pré-requisito: `.env` preenchido.

```bash
docker compose up --build
```

Serviços:

- `api` (FastAPI + migrations no startup)
- `worker` (Celery worker)
- `beat` (agendador Celery)
- `postgres`
- `redis`
- `prometheus`
- `grafana`

## Variáveis de ambiente críticas

- Banco: `DATABASE_URL`, `ALEMBIC_DATABASE_URL`.
- Redis/Celery: `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`.
- Auth: `JWT_SECRET_KEY`, expiração de tokens.
- Billing: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRO_PRICE_ID`.
- LLM: `LLM_PROVIDER`, `OPENAI_API_KEY`, `OPENAI_MODEL`.
- Ingestão: `INGESTION_INTERNAL_TOKEN`, timeouts e limites de quarentena.

## Segurança operacional

Em `staging/prod`:

- Proíbe `JWT_SECRET_KEY` default.
- Exige `INGESTION_INTERNAL_TOKEN` válido.
- Proíbe wildcard em `TRUSTED_HOSTS`.
- Exige `FORCE_HTTPS_REDIRECT=true`.
- Restringe CORS para HTTPS não-localhost.

## Seeds e utilitários

- Seed completo MVP:

```bash
python -m app.cli seed-mvp
```

- Verificação do seed:

```bash
python -m app.cli check-mvp-seed
```

- Seed de fontes de ingestão:

```bash
python scripts/ingestion_cli.py seed-sources
```

- Reprocessamento de fonte:

```bash
python scripts/ingestion_cli.py reprocess-source --source-key uk_gov_immigration --sync
```

## Observabilidade

### Health

- `GET /health/live`
- `GET /health/ready` (valida DB + Redis)
- `GET /health/metrics` (Prometheus)

### Métricas principais

- Tráfego HTTP e latência por rota.
- Duração de score/roadmap.
- Uso de provider LLM e fallback.
- Conversão free -> pro.
- Jobs por fila e status.
- Queries lentas, erros de transação e conexões ativas.

### Logs

- JSON estruturado com `trace_id`, `user_id`, `assessment_id`, `roadmap_id`.
- Header `x-trace-id` propagado na resposta.

