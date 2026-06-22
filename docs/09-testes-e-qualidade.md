# 09. Testes e Qualidade

## Estratégia atual

A suíte cobre contrato, regras de negócio, tarefas assíncronas, integração com Postgres e comportamento de billing freemium.

## Blocos de teste

- `tests/test_auth.py`: fluxo register/login/me/refresh.
- `tests/test_health.py`: liveness/readiness.
- `tests/test_score_engine.py`: motor de score, operadores e determinismo.
- `tests/test_async_tasks.py`: sucesso/retry/dead-letter de tasks.
- `tests/test_billing_freemium.py`: upgrade/downgrade/cancelamento/quota mensal.
- `tests/test_ingestion_parsers.py`: detecção de sinais em parsers.
- `tests/test_mvp_catalog_seed_data.py`: consistência de catálogo MVP.
- `tests/test_openapi_contract.py`: paths e schemas obrigatórios.
- `tests/integration/test_api_postgres_integration.py`: fluxo auth com Postgres real.

## Comandos de qualidade

Backend:

```bash
uv pip install -e .[dev]
ruff check .
black --check .
pytest
```

Frontend:

```bash
cd frontend
npm install
npm run lint
npm run typecheck
npm run test
npm run test:e2e
```

## Riscos ainda existentes

- Endpoint `/plans` não está implementado no backend; frontend usa fallback local.
- Comportamento de LLM depende de credenciais e rede (há fallback stub, mas com menor precisão).
- Ingestão depende de disponibilidade externa (robots, sites oficiais, formato de conteúdo).

