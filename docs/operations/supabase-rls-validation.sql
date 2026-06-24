-- Smoke test de isolamento multi-tenant com RLS.
-- Execute em ambiente de staging com duas contas (user_a, user_b).

-- 1) Simular contexto do user A
SELECT set_config('app.current_user_id', '00000000-0000-0000-0000-0000000000aa', true);
SELECT set_config('app.current_user_role', 'member', true);

-- Deve retornar somente dados do user A
SELECT id, user_id FROM assessments LIMIT 20;
SELECT id, user_id FROM roadmaps LIMIT 20;

-- 2) Simular contexto do user B
SELECT set_config('app.current_user_id', '00000000-0000-0000-0000-0000000000bb', true);
SELECT set_config('app.current_user_role', 'member', true);

-- Deve retornar somente dados do user B
SELECT id, user_id FROM assessments LIMIT 20;
SELECT id, user_id FROM roadmaps LIMIT 20;

-- 3) Admin pode visualizar todos
SELECT set_config('app.current_user_role', 'admin', true);
SELECT count(*) FROM assessments;
SELECT count(*) FROM roadmaps;

-- 4) Verificar policies existentes
SELECT schemaname, tablename, policyname, permissive, roles, cmd
FROM pg_policies
WHERE schemaname = 'public'
AND tablename IN (
  'assessments',
  'assessment_results',
  'assessment_result_items',
  'roadmaps',
  'roadmap_steps',
  'jobs',
  'subscriptions',
  'entitlements',
  'usage_counters',
  'user_profile_snapshots'
)
ORDER BY tablename ASC, policyname ASC;
