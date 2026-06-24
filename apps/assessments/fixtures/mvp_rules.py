from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from apps.assessments.engine import (
    ProgramVersionInput,
    RuleConditionInput,
    RuleGroupInput,
    RuleOutcomeInput,
)

MVP_PROGRAM_EFFECTIVE_FROM = "2026-01-01T00:00:00+00:00"
FIELD_KEY_IDIOMAS_NIVEL_EN = "idiomas_nivel.en"

MVP_RULE_FIXTURES = {
    "CA": {
        "country": {"code": "CA", "name": "Canada"},
        "program": {"code": "CA_IRCC_IMMIGRATION", "name": "IRCC Immigration Programs"},
        "program_version": {
            "id": "9a6cff22-dd5a-4f60-bfbb-54b4a8dc0ea1",
            "version": "2026.01",
            "effective_from": MVP_PROGRAM_EFFECTIVE_FROM,
            "effective_to": None,
        },
        "rule_groups": [
            {
                "id": "d3a7be84-20f7-4f05-a0dd-30263c9e3fdf",
                "code": "block_age_above_45",
                "name": "Bloqueio por idade",
                "priority": 10,
                "match_operator": "all",
                "conditions": [
                    {
                        "id": "35d54c31-c9a8-46dc-92d0-5f7daf640a53",
                        "field_key": "idade",
                        "operator": "gt",
                        "value_json": 45,
                        "condition_order": 1,
                        "is_required": True,
                    }
                ],
                "outcomes": [
                    {
                        "id": "6baf7f5f-c85d-4c1a-8ef4-99b2bc7b6003",
                        "score_delta": "-100",
                        "is_blocking": True,
                        "explanation_message": "Idade acima do limite do programa",
                        "outcome_code": "AGE_BLOCK",
                    }
                ],
            },
            {
                "id": "d4198868-f7d2-4749-9f93-b083ce89f8eb",
                "code": "age_ideal",
                "name": "Faixa etaria ideal",
                "priority": 20,
                "match_operator": "all",
                "conditions": [
                    {
                        "id": "f4f3727d-7278-4e60-bc94-d6faf23bf76a",
                        "field_key": "idade",
                        "operator": "between",
                        "value_json": [25, 35],
                        "condition_order": 1,
                        "is_required": True,
                    }
                ],
                "outcomes": [
                    {
                        "id": "0eeb46a2-596f-4d53-b598-c2f69b7ebe43",
                        "score_delta": "25",
                        "is_blocking": False,
                        "explanation_message": "Idade em faixa ideal",
                        "outcome_code": "AGE_BONUS",
                    }
                ],
            },
            {
                "id": "f762693b-0dd3-4787-9a8c-13c33924931f",
                "code": "education_high",
                "name": "Escolaridade avancada",
                "priority": 30,
                "match_operator": "all",
                "conditions": [
                    {
                        "id": "88c95db0-c218-4108-89be-dcd48e5057bd",
                        "field_key": "escolaridade_rank",
                        "operator": "gte",
                        "value_json": 4,
                        "condition_order": 1,
                        "is_required": True,
                    }
                ],
                "outcomes": [
                    {
                        "id": "8a8ee8ba-f950-4f57-9404-8ed78fbb57e7",
                        "score_delta": "20",
                        "is_blocking": False,
                        "explanation_message": "Escolaridade competitiva",
                        "outcome_code": "EDU_BONUS",
                    }
                ],
            },
            {
                "id": "7a7af4ec-fe5a-4db5-bda8-aa01b65ee111",
                "code": "priority_profession",
                "name": "Profissao prioritaria",
                "priority": 40,
                "match_operator": "all",
                "conditions": [
                    {
                        "id": "e7d2b467-42a8-4af7-baa8-52b39720eaac",
                        "field_key": "profissao_codigo",
                        "operator": "in",
                        "value_json": ["21231", "21300", "11101"],
                        "condition_order": 1,
                        "is_required": True,
                    }
                ],
                "outcomes": [
                    {
                        "id": "d7b021bf-a7ac-47f7-9a69-42eddf0b57f2",
                        "score_delta": "20",
                        "is_blocking": False,
                        "explanation_message": "Profissao em lista prioritaria",
                        "outcome_code": "PROF_BONUS",
                    }
                ],
            },
            {
                "id": "38d3009d-25fd-4223-9298-a4eb007d5273",
                "code": "english_high",
                "name": "Ingles forte",
                "priority": 50,
                "match_operator": "all",
                "conditions": [
                    {
                        "id": "7e0f77af-c50e-47d4-9efd-8add78ef8f3d",
                        "field_key": FIELD_KEY_IDIOMAS_NIVEL_EN,
                        "operator": "gte",
                        "value_json": 5,
                        "condition_order": 1,
                        "is_required": True,
                    }
                ],
                "outcomes": [
                    {
                        "id": "e091015f-1f46-4f72-b37b-aeb8ca545391",
                        "score_delta": "20",
                        "is_blocking": False,
                        "explanation_message": "Ingles em nivel competitivo",
                        "outcome_code": "LANG_EN_BONUS",
                    }
                ],
            },
            {
                "id": "73faff26-766c-48f6-aa2a-a35ad188d6cd",
                "code": "french_bonus",
                "name": "Frances adicional",
                "priority": 60,
                "match_operator": "all",
                "conditions": [
                    {
                        "id": "4cfeb9cc-c57e-4d8f-89ad-bd90df567f5d",
                        "field_key": "idiomas_nivel.fr",
                        "operator": "gte",
                        "value_json": 4,
                        "condition_order": 1,
                        "is_required": True,
                    }
                ],
                "outcomes": [
                    {
                        "id": "8240f343-2afd-4767-bf37-310f603fd385",
                        "score_delta": "10",
                        "is_blocking": False,
                        "explanation_message": "Frances adiciona pontos",
                        "outcome_code": "LANG_FR_BONUS",
                    }
                ],
            },
            {
                "id": "f5be625a-0f74-4ac5-a6d4-a0177f6121f2",
                "code": "income_ok",
                "name": "Renda adequada",
                "priority": 70,
                "match_operator": "all",
                "conditions": [
                    {
                        "id": "780fc551-68f5-4f5c-ae6d-0d4341f2a1c9",
                        "field_key": "renda_atual",
                        "operator": "gte",
                        "value_json": 5000,
                        "condition_order": 1,
                        "is_required": True,
                    }
                ],
                "outcomes": [
                    {
                        "id": "722c4f0b-4c96-44d9-b333-b4fc3d15193e",
                        "score_delta": "15",
                        "is_blocking": False,
                        "explanation_message": "Renda atual competitiva",
                        "outcome_code": "INCOME_BONUS",
                    }
                ],
            },
            {
                "id": "7f0e4b7e-5bf2-4215-b05d-3bc177d9dce8",
                "code": "english_gap",
                "name": "Gap de ingles",
                "priority": 80,
                "match_operator": "all",
                "conditions": [
                    {
                        "id": "33275bf0-f4ba-46fb-ae6d-13e0e58f9f26",
                        "field_key": FIELD_KEY_IDIOMAS_NIVEL_EN,
                        "operator": "lt",
                        "value_json": 5,
                        "condition_order": 1,
                        "is_required": True,
                    }
                ],
                "outcomes": [
                    {
                        "id": "8ac4bd7e-8231-4ca6-97f9-b4f5687a5a5e",
                        "score_delta": "-15",
                        "is_blocking": False,
                        "explanation_message": "Gap critico de idioma ingles",
                        "outcome_code": "LANG_EN_GAP",
                    }
                ],
            },
        ],
    },
    "AU": {
        "country": {"code": "AU", "name": "Australia"},
        "program": {"code": "skilled_independent", "name": "Skilled Independent"},
        "program_version": {
            "id": "4cfcd0c1-e078-49c0-8ec8-4cf1fb251d2b",
            "version": "2026.01",
            "effective_from": MVP_PROGRAM_EFFECTIVE_FROM,
            "effective_to": None,
        },
        "rule_groups": [
            {
                "id": "95de1688-6f0a-4f7a-9e97-55d025181c6a",
                "code": "block_medical_issue",
                "name": "Bloqueio por questao medica",
                "priority": 10,
                "match_operator": "all",
                "conditions": [
                    {
                        "id": "b84f55c6-efdf-4bb0-9db1-c55f5784dc8f",
                        "field_key": "tem_restricao_medica",
                        "operator": "eq",
                        "value_json": True,
                        "condition_order": 1,
                        "is_required": True,
                    }
                ],
                "outcomes": [
                    {
                        "id": "7c8515af-c4c9-4d74-b13f-2f14f6a39dd8",
                        "score_delta": "-100",
                        "is_blocking": True,
                        "explanation_message": "Restricao medica impeditiva",
                        "outcome_code": "MEDICAL_BLOCK",
                    }
                ],
            },
            {
                "id": "33662bb0-bf95-4f43-8f26-17a1df00531a",
                "code": "age_bonus",
                "name": "Faixa etaria ideal",
                "priority": 20,
                "match_operator": "all",
                "conditions": [
                    {
                        "id": "15dc188d-3005-43df-b943-54db4f8c6395",
                        "field_key": "idade",
                        "operator": "between",
                        "value_json": [26, 32],
                        "condition_order": 1,
                        "is_required": True,
                    }
                ],
                "outcomes": [
                    {
                        "id": "37f496da-7004-4a29-a47e-af2d6a0f6014",
                        "score_delta": "30",
                        "is_blocking": False,
                        "explanation_message": "Idade em faixa ideal",
                        "outcome_code": "AGE_BONUS",
                    }
                ],
            },
            {
                "id": "8e5e29cf-3bf8-44bf-a6f6-bd978d9062d7",
                "code": "education_bonus",
                "name": "Escolaridade",
                "priority": 30,
                "match_operator": "all",
                "conditions": [
                    {
                        "id": "7b0f8ec8-c3e0-4f16-a55d-ec6275f06c27",
                        "field_key": "escolaridade_rank",
                        "operator": "gte",
                        "value_json": 4,
                        "condition_order": 1,
                        "is_required": True,
                    }
                ],
                "outcomes": [
                    {
                        "id": "ff8adca6-88bf-4b79-8cc3-a6e3a31968ce",
                        "score_delta": "15",
                        "is_blocking": False,
                        "explanation_message": "Formacao academica favorece selecao",
                        "outcome_code": "EDU_BONUS",
                    }
                ],
            },
            {
                "id": "f91ee8f8-ef54-48d0-a5b4-d7c53903842f",
                "code": "occupation_bonus",
                "name": "Profissao elegivel",
                "priority": 40,
                "match_operator": "all",
                "conditions": [
                    {
                        "id": "74b65543-4782-4793-a2bb-3c8df626a667",
                        "field_key": "profissao_codigo",
                        "operator": "in",
                        "value_json": ["261313", "261312", "225113"],
                        "condition_order": 1,
                        "is_required": True,
                    }
                ],
                "outcomes": [
                    {
                        "id": "602f1cb0-6f02-4b7f-a3f2-4a38106cab95",
                        "score_delta": "10",
                        "is_blocking": False,
                        "explanation_message": "Profissao em lista ocupacional",
                        "outcome_code": "PROF_BONUS",
                    }
                ],
            },
            {
                "id": "f534a0ba-6e27-4af4-b7c0-340647611989",
                "code": "income_bonus",
                "name": "Renda favoravel",
                "priority": 50,
                "match_operator": "all",
                "conditions": [
                    {
                        "id": "73e526ec-f3de-4f7f-a555-b3fdcb6f31fd",
                        "field_key": "renda_atual",
                        "operator": "gte",
                        "value_json": 4500,
                        "condition_order": 1,
                        "is_required": True,
                    }
                ],
                "outcomes": [
                    {
                        "id": "835ff81c-95cd-4cec-96b9-a74ab7e97f95",
                        "score_delta": "30",
                        "is_blocking": False,
                        "explanation_message": "Renda fortalece sustentabilidade financeira",
                        "outcome_code": "INCOME_BONUS",
                    }
                ],
            },
            {
                "id": "ea966f40-08ca-4dc1-a811-0a95188d84e1",
                "code": "income_gap",
                "name": "Gap de renda",
                "priority": 60,
                "match_operator": "all",
                "conditions": [
                    {
                        "id": "d710de18-4ae1-4cef-b08f-ad15a2f4efdd",
                        "field_key": "renda_atual",
                        "operator": "lt",
                        "value_json": 4500,
                        "condition_order": 1,
                        "is_required": True,
                    }
                ],
                "outcomes": [
                    {
                        "id": "a3064388-f742-47dc-8c6b-d3b534b5a278",
                        "score_delta": "-15",
                        "is_blocking": False,
                        "explanation_message": "Gap de renda atual",
                        "outcome_code": "INCOME_GAP",
                    }
                ],
            },
        ],
    },
    "PT": {
        "country": {"code": "PT", "name": "Portugal"},
        "program": {"code": "PT_AIMA_VISAS", "name": "AIMA Residence and Visa Rules"},
        "program_version": {
            "id": "54b82206-3858-4125-8ce3-6c440e6dddc8",
            "version": "2026.01",
            "effective_from": MVP_PROGRAM_EFFECTIVE_FROM,
            "effective_to": None,
        },
        "rule_groups": [
            {
                "id": "30807eb3-c84b-4906-82cc-d305ba67d221",
                "code": "minimum_income",
                "name": "Renda minima",
                "priority": 10,
                "match_operator": "all",
                "conditions": [
                    {
                        "id": "9901a2f4-6f85-447d-974f-26f727a62866",
                        "field_key": "renda_atual",
                        "operator": "gte",
                        "value_json": 3000,
                        "condition_order": 1,
                        "is_required": True,
                    }
                ],
                "outcomes": [
                    {
                        "id": "a7b62ea5-4f75-4f2f-b183-1d8f39185553",
                        "score_delta": "35",
                        "is_blocking": False,
                        "explanation_message": "Renda atende referencia do programa",
                        "outcome_code": "INCOME_OK",
                    }
                ],
            },
            {
                "id": "c0173632-662d-44ca-a35c-cbb5e12de128",
                "code": "language_bonus",
                "name": "Idioma portugues",
                "priority": 20,
                "match_operator": "all",
                "conditions": [
                    {
                        "id": "bf4ffa95-03e8-4c1d-a35e-54805fe8d79e",
                        "field_key": "idiomas_nivel.pt",
                        "operator": "gte",
                        "value_json": 3,
                        "condition_order": 1,
                        "is_required": True,
                    }
                ],
                "outcomes": [
                    {
                        "id": "f4007889-cee5-4f4f-975f-c63566abe6cb",
                        "score_delta": "15",
                        "is_blocking": False,
                        "explanation_message": "Idioma portugues facilita integracao",
                        "outcome_code": "PT_LANG_BONUS",
                    }
                ],
            },
            {
                "id": "7642da13-f77a-4dc0-ae00-b68e37f3037d",
                "code": "background_exists",
                "name": "Dados basicos presentes",
                "priority": 30,
                "match_operator": "all",
                "conditions": [
                    {
                        "id": "5ea0d7c7-9cb0-476c-b8dc-f20accfdf734",
                        "field_key": "profissao_codigo",
                        "operator": "exists",
                        "value_json": True,
                        "condition_order": 1,
                        "is_required": True,
                    }
                ],
                "outcomes": [
                    {
                        "id": "34f63cae-f10f-4a5a-b3ec-dbf66f0763d5",
                        "score_delta": "10",
                        "is_blocking": False,
                        "explanation_message": "Historico profissional informado",
                        "outcome_code": "PROFILE_COMPLETENESS",
                    }
                ],
            },
        ],
    },
    "US": {
        "country": {"code": "US", "name": "Estados Unidos"},
        "program": {"code": "US_GENERAL_IMMIGRATION", "name": "USCIS Immigration Pathways"},
        "program_version": {
            "id": "b2e31b89-6d98-492f-a40d-0d0cd86b0869",
            "version": "2026.01",
            "effective_from": MVP_PROGRAM_EFFECTIVE_FROM,
            "effective_to": None,
        },
        "rule_groups": [
            {
                "id": "f5f29bce-d00d-4ed3-b425-09d6e6bf8cb4",
                "code": "professional_experience",
                "name": "Experiencia profissional",
                "priority": 10,
                "match_operator": "all",
                "conditions": [
                    {
                        "id": "2f1ef2db-0f77-4fb8-847a-9e3d0db43f5f",
                        "field_key": "anos_experiencia",
                        "operator": "gte",
                        "value_json": 3,
                        "condition_order": 1,
                        "is_required": True,
                    }
                ],
                "outcomes": [
                    {
                        "id": "fafe8330-ddde-4f27-a025-c4e8fff53443",
                        "score_delta": "20",
                        "is_blocking": False,
                        "explanation_message": "Experiencia profissional competitiva",
                        "outcome_code": "EXPERIENCE_BONUS",
                    }
                ],
            },
            {
                "id": "bf44caaf-c7af-45d5-8183-2f5d6ca9b9af",
                "code": "english_requirement",
                "name": "Ingles minimo",
                "priority": 20,
                "match_operator": "all",
                "conditions": [
                    {
                        "id": "7df77ffe-2f49-42ec-b68f-28af93b26e20",
                        "field_key": FIELD_KEY_IDIOMAS_NIVEL_EN,
                        "operator": "gte",
                        "value_json": 4,
                        "condition_order": 1,
                        "is_required": True,
                    }
                ],
                "outcomes": [
                    {
                        "id": "58d16465-8572-4ecb-abc3-f810464d4f52",
                        "score_delta": "15",
                        "is_blocking": False,
                        "explanation_message": "Nivel de ingles adequado para aplicacao",
                        "outcome_code": "LANGUAGE_BONUS",
                    }
                ],
            },
            {
                "id": "a0f0f1aa-cf66-4df4-88db-96abf9d2ca39",
                "code": "inadmissibility_block",
                "name": "Bloqueio por inadmissibilidade",
                "priority": 30,
                "match_operator": "all",
                "conditions": [
                    {
                        "id": "b97d59f6-83b5-4269-bbce-0e0f1be9d40e",
                        "field_key": "possui_inadmissibilidade",
                        "operator": "eq",
                        "value_json": True,
                        "condition_order": 1,
                        "is_required": True,
                    }
                ],
                "outcomes": [
                    {
                        "id": "7048a266-eb8c-4f15-8bca-26df5e77ac48",
                        "score_delta": "-100",
                        "is_blocking": True,
                        "explanation_message": "Existem criterios impeditivos de admissibilidade",
                        "outcome_code": "INADMISSIBILITY_BLOCK",
                    }
                ],
            },
        ],
    },
    "GB": {
        "country": {"code": "GB", "name": "Reino Unido"},
        "program": {"code": "UK_VISAS_IMMIGRATION", "name": "UK Visas and Immigration"},
        "program_version": {
            "id": "1c7f52bc-6fd4-4cc6-825e-7bca0f974ebf",
            "version": "2026.01",
            "effective_from": MVP_PROGRAM_EFFECTIVE_FROM,
            "effective_to": None,
        },
        "rule_groups": [
            {
                "id": "3c8c8ef1-4f16-440a-a923-3f4d5575d58e",
                "code": "salary_threshold",
                "name": "Faixa salarial",
                "priority": 10,
                "match_operator": "all",
                "conditions": [
                    {
                        "id": "55a660d2-22a3-4ea2-a216-30235e2d95d4",
                        "field_key": "salario_anual",
                        "operator": "gte",
                        "value_json": 38700,
                        "condition_order": 1,
                        "is_required": True,
                    }
                ],
                "outcomes": [
                    {
                        "id": "f5c4735b-84e7-44a8-975c-4d0d7de6f8f9",
                        "score_delta": "25",
                        "is_blocking": False,
                        "explanation_message": "Faixa salarial alinhada ao programa",
                        "outcome_code": "SALARY_BONUS",
                    }
                ],
            },
            {
                "id": "f72411f9-a052-40ca-89d5-49f26895a8e4",
                "code": "english_b1",
                "name": "Ingles nivel B1",
                "priority": 20,
                "match_operator": "all",
                "conditions": [
                    {
                        "id": "3c7ce8f7-c7de-485b-b6c0-a4213f4f0e72",
                        "field_key": FIELD_KEY_IDIOMAS_NIVEL_EN,
                        "operator": "gte",
                        "value_json": 3,
                        "condition_order": 1,
                        "is_required": True,
                    }
                ],
                "outcomes": [
                    {
                        "id": "2044f54b-f9a0-4745-8895-e40f6a43dcfd",
                        "score_delta": "15",
                        "is_blocking": False,
                        "explanation_message": "Comprovacao de ingles em nivel minimo",
                        "outcome_code": "ENGLISH_OK",
                    }
                ],
            },
        ],
    },
    "DE": {
        "country": {"code": "DE", "name": "Alemanha"},
        "program": {"code": "DE_WORK_IMMIGRATION", "name": "Make it in Germany"},
        "program_version": {
            "id": "8cadfce6-57fd-4975-9530-9012cccd5be6",
            "version": "2026.01",
            "effective_from": MVP_PROGRAM_EFFECTIVE_FROM,
            "effective_to": None,
        },
        "rule_groups": [
            {
                "id": "994238af-e40f-4f75-80f3-cd8d24b6b8d3",
                "code": "qualification_recognized",
                "name": "Qualificacao reconhecida",
                "priority": 10,
                "match_operator": "all",
                "conditions": [
                    {
                        "id": "6d61da55-98db-4a1b-a05c-7afc02bdc3ff",
                        "field_key": "qualificacao_reconhecida",
                        "operator": "eq",
                        "value_json": True,
                        "condition_order": 1,
                        "is_required": True,
                    }
                ],
                "outcomes": [
                    {
                        "id": "ac53c10b-1be5-4a9b-afd5-f97d91d9fa4f",
                        "score_delta": "25",
                        "is_blocking": False,
                        "explanation_message": "Qualificacao reconhecida para trabalho qualificado",
                        "outcome_code": "RECOGNITION_BONUS",
                    }
                ],
            },
            {
                "id": "cd1325bd-b222-4288-9e3f-b3f8647d5cd7",
                "code": "german_language",
                "name": "Idioma alemao",
                "priority": 20,
                "match_operator": "all",
                "conditions": [
                    {
                        "id": "634e10dd-94af-4203-bd58-9788182276bc",
                        "field_key": "idiomas_nivel.de",
                        "operator": "gte",
                        "value_json": 3,
                        "condition_order": 1,
                        "is_required": True,
                    }
                ],
                "outcomes": [
                    {
                        "id": "41135f62-64d2-42e6-bec1-9f977936f5f4",
                        "score_delta": "15",
                        "is_blocking": False,
                        "explanation_message": "Nivel de alemao ajuda na elegibilidade",
                        "outcome_code": "GERMAN_BONUS",
                    }
                ],
            },
        ],
    },
}


def build_program_version_input(country_code: str) -> ProgramVersionInput:
    fixture = MVP_RULE_FIXTURES[country_code]
    version = fixture["program_version"]
    return ProgramVersionInput(
        id=UUID(version["id"]),
        version=version["version"],
        effective_from=datetime.fromisoformat(version["effective_from"]).astimezone(UTC),
        effective_to=(
            datetime.fromisoformat(version["effective_to"]).astimezone(UTC)
            if version["effective_to"]
            else None
        ),
    )


def build_rule_group_inputs(country_code: str) -> list[RuleGroupInput]:
    fixture = MVP_RULE_FIXTURES[country_code]
    groups: list[RuleGroupInput] = []

    for group in fixture["rule_groups"]:
        conditions = tuple(
            RuleConditionInput(
                id=UUID(condition["id"]),
                field_key=condition["field_key"],
                operator=condition["operator"],
                value_json=condition["value_json"],
                condition_order=int(condition["condition_order"]),
                is_required=bool(condition["is_required"]),
            )
            for condition in group["conditions"]
        )

        outcomes = tuple(
            RuleOutcomeInput(
                id=UUID(outcome["id"]),
                score_delta=Decimal(outcome["score_delta"]),
                is_blocking=bool(outcome["is_blocking"]),
                explanation_message=outcome["explanation_message"],
                outcome_code=outcome["outcome_code"],
            )
            for outcome in group["outcomes"]
        )

        groups.append(
            RuleGroupInput(
                id=UUID(group["id"]),
                code=group["code"],
                name=group["name"],
                priority=int(group["priority"]),
                match_operator=group["match_operator"],
                conditions=conditions,
                outcomes=outcomes,
            )
        )

    return groups
