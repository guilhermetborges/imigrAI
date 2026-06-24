# Napkin Runbook

## Curation Rules
- Re-prioritize on every read.
- Keep recurring, high-value notes only.
- Max 10 items per category.
- Each item includes date + "Do instead".

## Execution & Validation (Highest Priority)
1. **[2026-06-22] Local-first backend**
   Do instead: keep default backend dependencies runnable with SQLite file storage and in-memory queue/cache unless the user explicitly asks for external services.
2. **[2026-06-22] Sonar scans local sources broadly**
   Do instead: keep real `.env` files excluded from Sonar and store only empty placeholders in `.env.example`.
3. **[2026-06-23] Docker SQLite bind mounts can hit host permission labels**
   Do instead: use named Docker volumes for `/app/data` and `/app/.cache` when running the local compose stack.

## Shell & Command Reliability
1. **[2026-06-22] Avoid leaking env secrets**
   Do instead: do not print `.env` values; use examples or mention variable names only.

## Domain Behavior Guardrails
1. **[2026-06-22] Supabase/Redis removed from local path**
   Do instead: use `data/imigrai.db`, `.cache/ingestion`, Celery eager mode, and in-memory rate limit/cache for local execution.

## User Directives
1. **[2026-06-22] Backend CI is lint-only**
   Do instead: do not add backend unit tests or database migrations back to CI unless the user explicitly asks; assume backend DB validation is local.
2. **[2026-06-22] Faculty testing evidence**
   Do instead: document and verify Sonar, unit tests, and manual test steps when changing this project.
