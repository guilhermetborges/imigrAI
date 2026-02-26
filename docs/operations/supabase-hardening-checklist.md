# Checklist de Hardening Supabase

## Chaves e segredo
- [ ] `SUPABASE_SERVICE_ROLE_KEY` somente em backend/workers (nunca `NEXT_PUBLIC_*`).
- [ ] Frontend usa apenas `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
- [ ] Rotação trimestral de `JWT_SECRET_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `STRIPE_*`.
- [ ] Segredos carregados por secret manager/variáveis de ambiente; nada em código.

## Multi-tenant e RLS
- [ ] RLS habilitado e forçado nas tabelas multi-tenant (`FORCE ROW LEVEL SECURITY`).
- [ ] Policies por ownership (`user_id = app_current_user_id()`) e override admin.
- [ ] Funções `app_current_user_id()` e `app_current_user_role()` instaladas.
- [ ] Backend define `set_config('app.current_user_id', ...)` por request autenticada.
- [ ] Validar que usuário A não lê dados de usuário B.

## Permissões e acesso
- [ ] Papel `member` por padrão; `admin` apenas para operações administrativas.
- [ ] Endpoints críticos protegidos por JWT + ownership.
- [ ] Endpoints de auth/criação com rate limit ativo.
- [ ] Webhook Stripe validando assinatura (`Stripe-Signature` + webhook secret).

## Banco e confiabilidade
- [ ] Backups automáticos habilitados no Supabase (PITR, quando disponível).
- [ ] Teste de restore executado mensalmente.
- [ ] Alertas para conexões ativas, query lenta e erro de transação.
- [ ] Índices revisados em colunas de `user_id`, `trace_id`, `status`.

## Observabilidade e auditoria
- [ ] Logs JSON com `trace_id`, `user_id`, `assessment_id`, `roadmap_id`.
- [ ] Métricas de negócio: score, roadmap, erro LLM, conversão free->pro.
- [ ] Métricas técnicas: fila Celery, p95 endpoints, disponibilidade, Postgres ativo.
- [ ] Retenção de logs e trilha de auditoria conforme política interna.

## Validação final
- [ ] Falha no provider LLM não derruba o serviço (fallback ativo).
- [ ] RLS validado por script SQL de smoke test.
- [ ] Runbook de incidentes revisado e acessível para on-call.
