# Migracao e Validacao Supabase (Staging e Producao)

## Workflow automatizado
Arquivo versionado: `.github/workflows/cd.yml`

## Staging (automatico na `main`)
1. Job `Staging Migration Validation`:
   - executa `python scripts/run_migrations_safe.py`
   - aplica `alembic upgrade head`
   - valida `alembic current == alembic heads`
2. Job `Deploy Staging`:
   - dispara webhook de deploy para staging
3. Job `Seed + Smoke Staging`:
   - executa `python scripts/seed_initial_data.py`
   - executa `python scripts/smoke_test.py --base-url <staging_api_url> --run-auth-flow`

## Producao (manual com aprovacao)
1. Executar workflow `CD` manualmente com `target=production`.
2. Aprovacao no ambiente GitHub `production`.
3. Job `Production Migration Validation`:
   - aplica migracoes no projeto Supabase de producao
   - valida revisao atual vs head
4. Job `Deploy Production (Manual Approval)`:
   - dispara webhook de deploy para producao
5. Job `Seed + Smoke Production`:
   - roda seed idempotente e smoke tests.

## Segredos esperados no GitHub
- Staging:
  - `STAGING_DATABASE_URL`
  - `STAGING_ALEMBIC_DATABASE_URL`
  - `STAGING_DEPLOY_WEBHOOK_URL`
  - `STAGING_DEPLOY_WEBHOOK_TOKEN` (opcional)
  - `STAGING_API_BASE_URL`
  - `STAGING_REDIS_URL`
  - `STAGING_REDIS_RESULT_BACKEND`
  - `STAGING_JWT_SECRET_KEY`
  - `STAGING_INGESTION_INTERNAL_TOKEN`
- Producao:
  - `PRODUCTION_DATABASE_URL`
  - `PRODUCTION_ALEMBIC_DATABASE_URL`
  - `PRODUCTION_DEPLOY_WEBHOOK_URL`
  - `PRODUCTION_DEPLOY_WEBHOOK_TOKEN` (opcional)
  - `PRODUCTION_API_BASE_URL`
  - `PRODUCTION_REDIS_URL`
  - `PRODUCTION_REDIS_RESULT_BACKEND`
  - `PRODUCTION_JWT_SECRET_KEY`
  - `PRODUCTION_INGESTION_INTERNAL_TOKEN`
