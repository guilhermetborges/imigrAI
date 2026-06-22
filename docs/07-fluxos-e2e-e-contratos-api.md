# 07. Fluxos E2E e Contratos de API

## Fluxo A: Cadastro -> Score

1. `POST /api/v1/auth/register`
2. `POST /api/v1/assessments` (`202`, retorna `assessment_id` e `job_id`)
3. Polling em `GET /api/v1/assessments/{assessment_id}/status`
4. Resultado em `GET /api/v1/assessments/{assessment_id}/breakdown`

## Fluxo B: Score -> Roadmap Pro

1. Usuário com entitlement `roadmap.pro`.
2. `POST /api/v1/roadmaps` (`202`, retorna `roadmap_id` e `job_id`)
3. Polling em `GET /api/v1/roadmaps/{roadmap_id}/status`
4. Leitura final em `GET /api/v1/roadmaps/{roadmap_id}`

## Fluxo C: Upgrade via Stripe

1. `POST /api/v1/billing/checkout-session`
2. Front redireciona para `checkout_url`.
3. Stripe envia webhook para `POST /api/v1/billing/webhook/stripe`
4. Entitlements atualizados.
5. Front confirma em `GET /api/v1/entitlements/me`

## Fluxo D: Profile Match guest -> claim

1. `POST /api/v1/profile-match/submit` com `guest_session_id`.
2. Se `requires_login=true`, frontend guarda submissão pendente.
3. Após autenticação: `POST /api/v1/profile-match/claim`.
4. Resultado disponível em `GET /api/v1/profile-match/{submission_id}/results`.

## Fluxo E: Ingestão manual de fonte

1. `POST /api/v1/ingestion/reprocess-source` (token interno).
2. Processamento sync ou async (`ingestion_queue`).
3. Consulta de run em `GET /api/v1/ingestion/runs/{run_id}`.

## Contratos essenciais

- Endpoints assíncronos retornam `202` e identificador de job.
- Status padronizados em enums de domínio (`pending`, `running`, `completed`, `failed`, etc.).
- OpenAPI validado em testes para rotas críticas de assessment/roadmap.

## Erros esperados (exemplos)

- `401`: autenticação ausente/inválida.
- `403`: entitlement insuficiente ou quota excedida.
- `404`: recurso não encontrado/sem permissão contextual.
- `409`: conflito de estado (ex.: assessment não concluído para roadmap).
- `429`: rate limit por escopo.

