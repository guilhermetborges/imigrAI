# 06. Regras de Negócio

## 1) Autenticação e autorização

- Registro cria usuário com papel:
  - `admin` se email está em `ADMIN_EMAILS`.
  - `member` caso contrário.
- Login exige credenciais válidas.
- Rotas privadas exigem JWT `access` válido.
- Token `refresh` gera novo par de tokens.

## 2) Freemium e billing

### Baseline de acesso

- Ao primeiro acesso, usuário recebe entitlements do plano Free automaticamente.

### Regras de plano

- Free:
  - entitlement de `assessments.monthly` com limite mensal configurável (default 3).
- Pro:
  - assessments ilimitados;
  - `roadmap.pro` habilitado;
  - features adicionais (`history.extended`, `countries.comparison`, `processing.priority`).

### Quota de assessment

- Consumo ocorre na criação de assessment novo (não idempotente repetido).
- Se limite mensal atingido, API responde `403`.

### Stripe webhook

Eventos tratados:

- `checkout.session.completed`
- `invoice.paid`
- `customer.subscription.updated`
- `customer.subscription.deleted`

Comportamentos:

- replay idempotente não reprocesa efeitos.
- upgrade ativa entitlements Pro.
- cancelamento/expiração retorna usuário ao baseline Free.

## 3) Assessments (score)

### Criação

- Requer usuário autenticado.
- `profile_json` obrigatório e com limite de tamanho.
- Idempotência por `idempotency_key` + usuário.
- Cria snapshot versionado do perfil.
- Enfileira `score_job` com prioridade:
  - Pro: prioridade alta.
  - Free: prioridade normal.

### Processamento

- Seleciona `program_version` ativa na data da solicitação.
- Executa `ScoreEngine` com regras do programa.
- Persistência inclui:
  - score final,
  - elegibilidade,
  - hash de versão das regras,
  - breakdown auditável por item.

### Faixas de score

- `< 40`: `baixo`
- `40 <= score < 70`: `medio`
- `>= 70`: `alto`

### Bloqueios

- Outcomes com `is_blocking=True` zeram score final e marcam ineligível.

## 4) Roadmaps

### Pré-condições

- Assessment deve estar `completed`.
- Usuário deve possuir entitlement `roadmap.pro`.

### Geração

- Cria `roadmap` pendente + `roadmap_job`.
- Provider LLM primário (OpenAI) com fallback resiliente.
- Circuit breaker para falhas consecutivas no primário.
- Contrato validado por schema (`roadmap.v1`) e ordem de etapas sem duplicidade.

### Resultado

- Persiste objetivo/sumário, passos ordenados, prazo, dependências e risco.
- Em erro definitivo, roadmap é marcado como `failed`.

## 5) Profile Match

- Aceita envio sem login (`guest_session_id`).
- Ranking de 15 países por algoritmo heurístico ponderado.
- Se usuário guest, retorno vem sem resultado completo (`requires_login=true`).
- Após login, usuário pode “claim” da submissão pelo par (`submission_id`, `guest_session_id`).

## 6) Ingestão

### Pipeline

1. Fetch da fonte (com política de robots opcional).
2. Armazenamento bruto (`bronze_document`).
3. Extração determinística de seções + regras.
4. Fallback LLM quando confiança abaixo do threshold.
5. Diff semântico com versão anterior.
6. Publicação de nova versão de programa quando mudança relevante e `allow_publish`.

### Quarentena

- Fonte acumula falhas consecutivas.
- Ao atingir limite configurado, entra em `quarantine_until`.
- Itens de run podem ser marcados como `quarantined`.

### Publicação segura

- Se `manual_review_required` ou baixa confiança, não publica automaticamente.
- Ainda assim registra `source_document` e `source_extraction` para auditoria.

## 7) Jobs e retries

- Erro transitório: retry exponencial.
- Erro definitivo (ex.: `ValueError`, `IntegrityError`, schema inválido): dead-letter.
- Status disponível por endpoint `/api/v1/jobs/{job_id}`.

