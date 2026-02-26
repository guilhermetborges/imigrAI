# Observabilidade Local (Prometheus + Grafana)

## Subir stack
```bash
docker compose up -d api worker beat redis postgres prometheus grafana
```

## Endpoints
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3001` (`admin` / `admin`)
- Métricas API: `http://localhost:8000/health/metrics`

## Dashboard
- Dashboard provisionado automaticamente:
  - `imigrAI Observability`
  - arquivo: `ops/grafana/dashboards/imigrai-observability.json`

## Métricas obrigatórias cobertas
- Negócio:
  - `imigrai_business_score_duration_seconds`
  - `imigrai_business_roadmap_duration_seconds`
  - `imigrai_business_llm_provider_requests_total`
  - `imigrai_business_free_to_pro_conversions_total`
- Técnicas:
  - `imigrai_celery_jobs`
  - `imigrai_http_request_duration_seconds`
  - `imigrai_service_up`
  - `imigrai_postgres_active_connections`
  - `imigrai_db_slow_queries_total`
  - `imigrai_db_transaction_errors_total`
