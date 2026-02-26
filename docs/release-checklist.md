# Release Checklist (MVP)

## Qualidade de PR
- [ ] Branch protection habilitada na `main` com checks obrigatorios:
  - [ ] `Backend Lint + Tests`
  - [ ] `Frontend Lint + Unit Tests`
  - [ ] `Frontend E2E`
  - [ ] `Docker Build`
- [ ] CI verde no PR (lint, format check, backend, frontend, e2e, docker build).
- [ ] Migracoes Alembic revisadas e backward-compatible.
- [ ] OpenAPI contrato validado (`tests/test_openapi_contract.py`).

## Antes do release
- [ ] Imagens Docker publicadas no GHCR com tag do commit (`${GITHUB_SHA}`).
- [ ] `Staging Migration Validation` concluida com sucesso.
- [ ] Deploy de staging automatico executado na branch principal.
- [ ] Seed inicial de staging executada (`scripts/seed_initial_data.py`).
- [ ] Smoke tests de staging aprovados (`scripts/smoke_test.py`).

## Producao (manual)
- [ ] Execucao manual do workflow `CD` com `target=production`.
- [ ] Aprovacao manual no ambiente `production` (GitHub Environment).
- [ ] `Production Migration Validation` concluida sem erros.
- [ ] Seed inicial de producao executada.
- [ ] Smoke tests de producao aprovados.

## Pos-release
- [ ] Monitorar erros por 30 minutos no dashboard.
- [ ] Verificar latencia p95 e jobs dead-letter.
- [ ] Confirmar que rollback esta preparado (ver `docs/rollback-strategy.md`).
