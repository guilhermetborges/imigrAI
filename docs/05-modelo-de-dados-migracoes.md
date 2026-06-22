# 05. Modelo de Dados e Migrações

## Núcleos de dados

### Identidade e acesso

- `users` (email único, `role`, `is_active`).

### Regras de imigração

- `countries`
- `immigration_programs`
- `program_versions` (com status e período de vigência)
- `rule_groups`
- `rule_conditions`
- `rule_outcomes`

### Avaliação e resultado

- `user_profile_snapshots`
- `assessments`
- `assessment_results`
- `assessment_result_items`

### Roadmaps

- `roadmaps`
- `roadmap_steps`

### Assíncrono

- `jobs` (tipo, status, tentativas, erro, duração, trace)

### Billing/Freemium

- `plans`
- `subscriptions`
- `entitlements`
- `usage_counters`
- `billing_events`

### Ingestão

- `source_registry`
- `ingestion_run`
- `ingestion_run_item`
- `bronze_document`
- `silver_section`
- `source_documents`
- `source_extractions`

### Topo de funil

- `profile_match_submissions`

## Enumerações relevantes

- `assessment_status`: `pending`, `running`, `completed`, `failed`, `canceled`.
- `roadmap_status`: `pending`, `completed`, `failed`, `draft`, `published`, `archived`.
- `job_status`: `pending`, `running`, `completed`, `failed`, `dead_letter`.
- `subscription_status`: `trialing`, `active`, `past_due`, `canceled`, `expired`.
- `ingestion_run_item_status`: `pending`, `running`, `skipped`, `completed`, `failed`, `manual_review`, `quarantined`.

## Linha de evolução (Alembic)

- `20260224_0001`: criação de `users`.
- `20260224_0002`: fundação de regras dinâmicas + avaliação + billing base.
- `20260225_0003`: jobs assíncronos e melhorias de roadmap.
- `20260225_0004`: freemium/Stripe (eventos, subscription metadata, planos).
- `20260225_0005`: automação de ingestão e estruturas bronze/silver.
- `20260225_0006`: segurança por papéis e RLS multi-tenant.
- `20260225_0007`: suporte a catálogo MVP de países (prioridade e diáspora).
- `20260225_0008`: submissões de `profile-match`.

## Integridade e idempotência

- Constraints únicas para evitar duplicidade por chave de negócio:
  - assessment por (`user_id`, `idempotency_key`)
  - job por (`job_type`, `idempotency_key`)
  - program version por (`program_id`, `version`)
  - usage counter por janela de uso.
- Webhooks Stripe idempotentes por (`provider`, `provider_event_id`).

