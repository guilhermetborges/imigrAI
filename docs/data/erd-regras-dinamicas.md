# ERD - Regras de Imigracao Dinamicas e Versionadas

## Objetivo
Modelar regras de imigracao como dados versionados no tempo, sem `if/else` hardcoded no codigo.

## Diagrama textual

```text
Country (1) --- (N) ImmigrationProgram (1) --- (N) ProgramVersion
ProgramVersion (1) --- (N) RuleGroup (1) --- (N) RuleCondition
RuleGroup (1) --- (N) RuleOutcome
ProgramVersion (1) --- (N) SourceDocument (1) --- (N) SourceExtraction

User (1) --- (N) UserProfileSnapshot (1) --- (N) Assessment
ImmigrationProgram (1) --- (N) Assessment
Assessment (1) --- (1) AssessmentResult
ProgramVersion (1) --- (N) AssessmentResult
AssessmentResult (1) --- (N) AssessmentResultItem
AssessmentResultItem (N) --- (1) RuleGroup
AssessmentResultItem (N) --- (1) RuleCondition
AssessmentResultItem (N) --- (1) RuleOutcome

User (1) --- (N) Roadmap (1) --- (N) RoadmapStep
AssessmentResult (1) --- (N) Roadmap

Plan (1) --- (N) Subscription
User (1) --- (N) Subscription
User (1) --- (N) Entitlement
Plan (1) --- (N) Entitlement
Subscription (1) --- (N) Entitlement
```

## Entidades e responsabilidade

- `Country`: catalogo de paises suportados.
- `ImmigrationProgram`: programa de imigracao por pais.
- `ProgramVersion`: versao temporal de regras (`draft`, `active`, `archived`) com `effective_from`/`effective_to`.
- `RuleGroup`: agrupamento logico de condicoes.
- `RuleCondition`: predicado generico com `operator` + `value_json`.
- `RuleOutcome`: efeito da regra (pontuacao positiva/negativa, bloqueio e mensagem explicavel).
- `SourceDocument`: fonte normativa/documental associada a uma versao.
- `SourceExtraction`: extracao estruturada da fonte.
- `UserProfileSnapshot`: snapshot imutavel do perfil para auditoria historica.
- `Assessment`: requisicao de avaliacao de elegibilidade.
- `AssessmentResult`: resultado final, com `rules_version_hash` e `algorithm_version`.
- `AssessmentResultItem`: trilha de auditoria por regra aplicada.
- `Roadmap`: plano gerado para o usuario com `roadmap_schema_version`.
- `RoadmapStep`: passos ordenados do roadmap.
- `Plan`, `Subscription`, `Entitlement`: billing + limites de uso/freemium.

## Regras de integridade criticas

1. Todas as regras (`RuleGroup`, `RuleCondition`, `RuleOutcome`) referenciam `ProgramVersion`.
2. `ProgramVersion` tem `version`, `effective_from`, `effective_to`, `status`.
3. Nao pode existir sobreposicao de vigencia para versoes `active` do mesmo programa:
   - `tstzrange(effective_from, effective_to, '[)')`
   - `EXCLUDE USING gist (program_id WITH =, effective_period WITH &&) WHERE status = 'active'`
4. `UserProfileSnapshot` e imutavel via trigger `BEFORE UPDATE`.
5. `AssessmentResult.rules_version_hash` e obrigatorio para auditoria reprodutivel.

## Auditoria: "qual regra gerou este score?"

Join de referencia:

```sql
SELECT
  ari.id AS result_item_id,
  ar.id AS assessment_result_id,
  ar.rules_version_hash,
  rg.code AS rule_group_code,
  rc.field_key,
  rc.operator,
  rc.value_json,
  ro.score_delta,
  ro.is_blocking,
  ro.explanation_message
FROM assessment_result_items ari
JOIN assessment_results ar ON ar.id = ari.assessment_result_id
LEFT JOIN rule_groups rg ON rg.id = ari.rule_group_id
LEFT JOIN rule_conditions rc ON rc.id = ari.rule_condition_id
LEFT JOIN rule_outcomes ro ON ro.id = ari.rule_outcome_id
WHERE ar.id = :assessment_result_id;
```

Esse fluxo permite reconstruir de forma transparente a origem de cada item do score.
