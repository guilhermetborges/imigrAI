# Rollback Strategy (MVP)

## Objetivo
Retornar para uma versao estavel em menos de 15 minutos com baixo risco de perda de dados.

## Gatilhos de rollback
- Erro sistemico de autenticacao ou autorizacao.
- Regressao critica em onboarding, score, upgrade ou roadmap.
- Spike sustentado de erro 5xx/latencia apos deploy.
- Falha em migracao que impacta leitura/escrita principal.

## Procedimento rapido (<= 15 min)
1. Pausar rollout no ambiente afetado.
2. Reapontar deploy para a imagem anterior estavel:
   - backend: `ghcr.io/<org>/<repo>/imigrai-api:<previous_sha>`
   - frontend: `ghcr.io/<org>/<repo>/imigrai-frontend:<previous_sha>`
3. Executar smoke tests basicos (`/health/live`, `/health/ready`, `/openapi.json`).
4. Validar fluxo critico:
   - login
   - onboarding -> score
   - roadmap (se aplicavel)

## Rollback de banco (quando necessario)
1. Se migracao for additive e app antiga tolerar schema novo:
   - manter schema atual e apenas rollback de aplicacao.
2. Se migracao quebrar compatibilidade:
   - restaurar backup/PITR no Supabase para o timestamp pre-release.
   - reexecutar deploy da versao anterior.
3. Validar `alembic current` e conectividade da aplicacao.

## Comandos uteis
```bash
python scripts/smoke_test.py --base-url <api_url> --run-auth-flow --email-prefix rollback-smoke
python -m alembic current
```

## Evidencias obrigatorias
- SHA da versao anterior aplicada.
- Horario de inicio/fim do rollback.
- Resultado de smoke tests e metricas apos rollback.
- Plano de correcao antes de novo deploy.
