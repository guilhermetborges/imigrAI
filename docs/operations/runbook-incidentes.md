# Runbook de Incidentes (imigrAI)

## Escopo
- Backend FastAPI (`api`)
- Workers Celery (`worker`, `beat`)
- PostgreSQL Supabase
- Frontend Next.js

## Sinais de alerta
- `imigrai_service_up` com valor `0`
- `imigrai_http_request_duration_seconds` p95 acima do SLO
- `imigrai_business_llm_provider_requests_total{result="error"}` crescente
- `imigrai_celery_jobs{status="dead_letter"}` aumentando
- `imigrai_db_transaction_errors_total` ou `imigrai_db_slow_queries_total` aumentando

## Procedimento P0 (indisponibilidade)
1. Confirmar impacto no Grafana: disponibilidade por serviço, erro HTTP e filas.
2. Verificar `trace_id` do erro no log JSON e correlacionar com `assessment_id`/`roadmap_id`.
3. Checar saúde:
   - `GET /health/live`
   - `GET /health/ready`
4. Se `worker` indisponível: reiniciar worker/beat e revalidar fila.
5. Se DB com saturação: inspecionar conexões ativas (`imigrai_postgres_active_connections`) e queries lentas.

## Procedimento P1 (falha de provider LLM)
1. Confirmar aumento de `imigrai_business_llm_provider_requests_total{result="error"}`.
2. Validar se circuit breaker entrou em fallback (provider `claude_stub`).
3. Verificar backlog em `roadmap_queue`.
4. Se necessário, reduzir concorrência de roadmaps e abrir incidente no provedor externo.

## Procedimento P1 (abuso/rate-limit)
1. Monitorar respostas `429` nos logs de `http.access`.
2. Revisar IP/usuário ofensivo via `trace_id` e `user_id`.
3. Ajustar temporariamente limites:
   - `AUTH_RATE_LIMIT_*`
   - `CREATION_RATE_LIMIT_*`

## Procedimento P2 (falhas em jobs / dead letter)
1. Verificar volume em `imigrai_celery_jobs{status="dead_letter"}`.
2. Inspecionar payload de `dead_letter_event` nos logs.
3. Classificar:
   - transitório: reenfileirar job
   - definitivo: corrigir payload/regra e reprocessar idempotentemente
4. Para ingestion, validar quarentena da source antes do reprocessamento.

## Query de rastreio por `trace_id`
- Filtrar logs JSON por `trace_id`.
- Correlacionar com:
  - `assessment_id`
  - `roadmap_id`
  - `job_id`
  - status no endpoint `/api/v1/jobs/{job_id}`

## Comunicação
1. Abrir incidente com severidade e horário UTC.
2. Atualizar timeline a cada 15 minutos.
3. Registrar pós-mortem com causa raiz, ação corretiva e ação preventiva.
