# 04. Frontend (Next.js App Router)

## Visão geral

Frontend em `frontend/` com foco em jornada orientada a estado assíncrono (polling com backoff) e controle de acesso por sessão JWT.

## Rotas

- Públicas:
  - `/` (landing + profile match)
  - `/login`
  - `/register`
  - `/pricing`
- Privadas:
  - `/dashboard`
  - `/onboarding`
  - `/results/[assessmentId]`
  - `/roadmaps/[roadmapId]`
  - `/settings/subscription`

## Autenticação

- `AuthProvider` mantém `status` e `user`.
- Tokens em `localStorage` (`access`, `refresh`) + cookie de apoio `imigrai_access_token`.
- Axios interceptor faz refresh automático em `401` (exceto rotas de auth).
- `AuthGuard` protege páginas privadas no cliente.
- `middleware.ts` protege também no edge por presença de cookie.

## Integração com API

`frontend/src/lib/api/endpoints.ts` encapsula chamadas:

- `authApi`, `assessmentsApi`, `roadmapsApi`, `billingApi`, `jobsApi`, `profileMatchApi`.
- Normalização de payloads para tolerar variações de contrato.
- Fallback para planos no frontend quando `/plans` não existe/retorna `404`.

## Hooks de domínio

- `useCreateAssessment`, `useAssessmentStatus`, `useAssessmentBreakdown`, `useAssessmentHistory`.
- `useCreateRoadmap`, `useRoadmapStatus`, `useRoadmapDetail`.
- `useSubscription` (entitlements, checkout, flags de acesso).
- Polling progressivo com timeout para processos assíncronos.

## Jornada principal

1. Usuário loga/cadastra.
2. Preenche onboarding e cria assessment.
3. Acompanha status até `completed`.
4. Visualiza breakdown e gaps críticos.
5. Se Pro, gera roadmap; se Free, recebe CTA de upgrade.

## Environment frontend

Obrigatório:

- `NEXT_PUBLIC_API_BASE_URL` (URL base da API, padrão local `http://localhost:8000/api/v1`).

Validação impede exposição de chaves sensíveis em `NEXT_PUBLIC_*`.

