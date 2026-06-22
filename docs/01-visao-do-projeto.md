# 01. Visão do Projeto

## Objetivo

O `imigrAI` é um SaaS de apoio à decisão para imigração com três pilares:

1. Diagnóstico de aderência por país (`profile-match`) para topo de funil.
2. Score de elegibilidade por programa de imigração (`assessments`).
3. Plano de ação com etapas priorizadas (`roadmaps`, disponível no plano Pro).

## Proposta de valor

- Transformar regras de imigração em avaliação estruturada.
- Traduzir gaps críticos em próximos passos acionáveis.
- Operar com atualização contínua de fontes oficiais via pipeline de ingestão.

## Stack principal

- Backend: `FastAPI`, `SQLAlchemy async`, `Alembic`, `Celery`, `Redis`, `PostgreSQL`.
- Frontend: `Next.js 14`, `React Query`, `React Hook Form`, `Zod`, `Tailwind`.
- Billing: integração com `Stripe` (checkout + webhooks idempotentes).
- Observabilidade: `Prometheus` + `Grafana` + logs estruturados JSON.

## Módulos de domínio (backend)

- `accounts`: cadastro, login, tokens JWT e papéis de usuário.
- `billing`: planos, assinatura, entitlements e quota.
- `immigration_rules`: países, programas, versões e regras dinâmicas.
- `assessments`: execução do motor de score e breakdown.
- `roadmaps`: geração assíncrona de plano com LLM resiliente.
- `ingestion`: coleta e publicação de atualizações regulatórias.
- `common`: jobs assíncronos e status de processamento.
- `profile_match`: ranking inicial de países para usuários guest/logados.

## Produto atual (MVP evolutivo)

- `Free`: até 3 assessments/mês, sem roadmap IA.
- `Pro`: assessments ilimitados, roadmap habilitado, prioridade de fila.
- Catálogo MVP de 15 países com seeds e validações automatizadas.

