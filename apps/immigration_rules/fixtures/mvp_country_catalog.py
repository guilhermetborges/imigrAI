from __future__ import annotations

from typing import TypedDict

MVP_PROGRAM_VERSION = "2026.01"
MVP_PROGRAM_EFFECTIVE_FROM = "2026-01-01T00:00:00+00:00"
BRASILEIROS_EXTERIOR_URL = (
    "https://www.gov.br/mre/pt-br/assuntos/portal-consular/BrasileirosnoExterior2023.pdf"
)


class CatalogSource(TypedDict):
    source_key: str
    source_type: str
    source_url: str
    robots_url: str | None
    terms_url: str | None
    schedule_cron: str | None
    document_title: str


class CatalogProgram(TypedDict):
    code: str
    name: str
    description: str
    version: str
    sources: list[CatalogSource]


class CatalogCountry(TypedDict):
    code: str
    name: str
    priority_rank: int
    diaspora_population_estimate: int
    prioritization_source_url: str
    programs: list[CatalogProgram]


MVP_COUNTRY_CATALOG: list[CatalogCountry] = [
    {
        "code": "US",
        "name": "Estados Unidos",
        "priority_rank": 1,
        "diaspora_population_estimate": 2085000,
        "prioritization_source_url": BRASILEIROS_EXTERIOR_URL,
        "programs": [
            {
                "code": "US_GENERAL_IMMIGRATION",
                "name": "USCIS Immigration Pathways",
                "description": "Regras oficiais de residencia, trabalho e ajuste de status.",
                "version": MVP_PROGRAM_VERSION,
                "sources": [
                    {
                        "source_key": "us_uscis_main",
                        "source_type": "html",
                        "source_url": "https://www.uscis.gov/",
                        "robots_url": "https://www.uscis.gov/robots.txt",
                        "terms_url": "https://www.uscis.gov/about-us/website-policies",
                        "schedule_cron": "0 */12 * * *",
                        "document_title": "USCIS - Official Immigration Portal",
                    }
                ],
            },
            {
                "code": "US_VISAS",
                "name": "US Department of State Visas",
                "description": "Regras oficiais de vistos de nao-imigrante e imigrante.",
                "version": MVP_PROGRAM_VERSION,
                "sources": [
                    {
                        "source_key": "us_travel_state_visas",
                        "source_type": "html",
                        "source_url": "https://travel.state.gov/content/travel/en/us-visas.html",
                        "robots_url": "https://travel.state.gov/robots.txt",
                        "terms_url": None,
                        "schedule_cron": "15 */12 * * *",
                        "document_title": "US Travel State - Visa Information",
                    }
                ],
            },
        ],
    },
    {
        "code": "PT",
        "name": "Portugal",
        "priority_rank": 2,
        "diaspora_population_estimate": 513000,
        "prioritization_source_url": BRASILEIROS_EXTERIOR_URL,
        "programs": [
            {
                "code": "PT_AIMA_VISAS",
                "name": "AIMA Residence and Visa Rules",
                "description": "Informacoes oficiais de residencia e vistos em Portugal.",
                "version": MVP_PROGRAM_VERSION,
                "sources": [
                    {
                        "source_key": "pt_aima",
                        "source_type": "html",
                        "source_url": "https://aima.gov.pt/",
                        "robots_url": "https://aima.gov.pt/robots.txt",
                        "terms_url": None,
                        "schedule_cron": "0 2 * * *",
                        "document_title": "AIMA - Portal Oficial",
                    }
                ],
            }
        ],
    },
    {
        "code": "PY",
        "name": "Paraguai",
        "priority_rank": 3,
        "diaspora_population_estimate": 263200,
        "prioritization_source_url": BRASILEIROS_EXTERIOR_URL,
        "programs": [
            {
                "code": "PY_MIGRACIONES",
                "name": "Direccion Nacional de Migraciones",
                "description": "Normas oficiais de residencia e migracao no Paraguai.",
                "version": MVP_PROGRAM_VERSION,
                "sources": [
                    {
                        "source_key": "py_migraciones",
                        "source_type": "html",
                        "source_url": "https://www.migraciones.gov.py/",
                        "robots_url": "https://www.migraciones.gov.py/robots.txt",
                        "terms_url": None,
                        "schedule_cron": "20 2 * * *",
                        "document_title": "Migraciones Paraguay - Portal Oficial",
                    }
                ],
            }
        ],
    },
    {
        "code": "GB",
        "name": "Reino Unido",
        "priority_rank": 4,
        "diaspora_population_estimate": 230000,
        "prioritization_source_url": BRASILEIROS_EXTERIOR_URL,
        "programs": [
            {
                "code": "UK_VISAS_IMMIGRATION",
                "name": "UK Visas and Immigration",
                "description": "Regras oficiais de vistos e residencia no Reino Unido.",
                "version": MVP_PROGRAM_VERSION,
                "sources": [
                    {
                        "source_key": "uk_gov_immigration",
                        "source_type": "html",
                        "source_url": "https://www.gov.uk/browse/visas-immigration",
                        "robots_url": "https://www.gov.uk/robots.txt",
                        "terms_url": "https://www.gov.uk/help/terms-conditions",
                        "schedule_cron": "35 2 * * *",
                        "document_title": "GOV.UK - Visas and Immigration",
                    }
                ],
            }
        ],
    },
    {
        "code": "JP",
        "name": "Japao",
        "priority_rank": 5,
        "diaspora_population_estimate": 210471,
        "prioritization_source_url": BRASILEIROS_EXTERIOR_URL,
        "programs": [
            {
                "code": "JP_VISA_RULES",
                "name": "MOFA Visa Information",
                "description": (
                    "Portal oficial do Ministerio de Relacoes Exteriores do Japao para vistos."
                ),
                "version": MVP_PROGRAM_VERSION,
                "sources": [
                    {
                        "source_key": "jp_mofa_visa",
                        "source_type": "html",
                        "source_url": "https://www.mofa.go.jp/j_info/visit/visa/index.html",
                        "robots_url": "https://www.mofa.go.jp/robots.txt",
                        "terms_url": None,
                        "schedule_cron": "50 2 * * *",
                        "document_title": "MOFA Japan - Visa",
                    }
                ],
            },
            {
                "code": "JP_IMMIGRATION_ISA",
                "name": "Immigration Services Agency",
                "description": "Orientacoes oficiais da Immigration Services Agency.",
                "version": MVP_PROGRAM_VERSION,
                "sources": [
                    {
                        "source_key": "jp_isa_reference",
                        "source_type": "html",
                        "source_url": "https://www.isa.go.jp/en/",
                        "robots_url": "https://www.isa.go.jp/robots.txt",
                        "terms_url": None,
                        "schedule_cron": "10 3 * * *",
                        "document_title": "Immigration Services Agency - Official Site",
                    }
                ],
            },
        ],
    },
    {
        "code": "DE",
        "name": "Alemanha",
        "priority_rank": 6,
        "diaspora_population_estimate": 170400,
        "prioritization_source_url": BRASILEIROS_EXTERIOR_URL,
        "programs": [
            {
                "code": "DE_WORK_IMMIGRATION",
                "name": "Make it in Germany",
                "description": "Portal oficial para migracao de trabalho qualificado na Alemanha.",
                "version": MVP_PROGRAM_VERSION,
                "sources": [
                    {
                        "source_key": "de_make_it_in_germany",
                        "source_type": "html",
                        "source_url": "https://www.make-it-in-germany.com/en/",
                        "robots_url": "https://www.make-it-in-germany.com/robots.txt",
                        "terms_url": None,
                        "schedule_cron": "25 3 * * *",
                        "document_title": "Make it in Germany - Official Portal",
                    }
                ],
            },
            {
                "code": "DE_BAMF_IMMIGRATION",
                "name": "BAMF Immigration Rules",
                "description": "Normas e orientacoes oficiais do BAMF.",
                "version": MVP_PROGRAM_VERSION,
                "sources": [
                    {
                        "source_key": "de_bamf",
                        "source_type": "html",
                        "source_url": "https://www.bamf.de/EN/",
                        "robots_url": "https://www.bamf.de/robots.txt",
                        "terms_url": None,
                        "schedule_cron": "40 3 * * *",
                        "document_title": "BAMF - Official Immigration Information",
                    }
                ],
            },
        ],
    },
    {
        "code": "ES",
        "name": "Espanha",
        "priority_rank": 7,
        "diaspora_population_estimate": 161944,
        "prioritization_source_url": BRASILEIROS_EXTERIOR_URL,
        "programs": [
            {
                "code": "ES_MIGRACIONES",
                "name": "Ministerio de Inclusion y Migraciones",
                "description": "Regras oficiais de autorizacao de residencia e migracao.",
                "version": MVP_PROGRAM_VERSION,
                "sources": [
                    {
                        "source_key": "es_inclusion_migraciones",
                        "source_type": "html",
                        "source_url": "https://www.inclusion.gob.es/en/",
                        "robots_url": "https://www.inclusion.gob.es/robots.txt",
                        "terms_url": None,
                        "schedule_cron": "55 3 * * *",
                        "document_title": "Ministerio de Inclusion y Migraciones",
                    }
                ],
            }
        ],
    },
    {
        "code": "IT",
        "name": "Italia",
        "priority_rank": 8,
        "diaspora_population_estimate": 159000,
        "prioritization_source_url": BRASILEIROS_EXTERIOR_URL,
        "programs": [
            {
                "code": "IT_VISTI_INGRESSO",
                "name": "Esteri Visti e Ingresso",
                "description": "Regras oficiais para ingresso e vistos na Italia.",
                "version": MVP_PROGRAM_VERSION,
                "sources": [
                    {
                        "source_key": "it_esteri_visti",
                        "source_type": "html",
                        "source_url": "https://www.esteri.it/en/servizi-consolari-e-visti/ingressosoggiornoinitalia/",
                        "robots_url": "https://www.esteri.it/robots.txt",
                        "terms_url": None,
                        "schedule_cron": "10 4 * * *",
                        "document_title": "Ministero degli Affari Esteri - Visti",
                    }
                ],
            }
        ],
    },
    {
        "code": "CA",
        "name": "Canada",
        "priority_rank": 9,
        "diaspora_population_estimate": 143500,
        "prioritization_source_url": BRASILEIROS_EXTERIOR_URL,
        "programs": [
            {
                "code": "CA_IRCC_IMMIGRATION",
                "name": "IRCC Immigration Programs",
                "description": "Regras oficiais de imigracao e cidadania do Canada.",
                "version": MVP_PROGRAM_VERSION,
                "sources": [
                    {
                        "source_key": "ca_ircc",
                        "source_type": "html",
                        "source_url": "https://www.canada.ca/en/services/immigration-citizenship.html",
                        "robots_url": "https://www.canada.ca/robots.txt",
                        "terms_url": None,
                        "schedule_cron": "25 4 * * *",
                        "document_title": "IRCC - Immigration and Citizenship",
                    }
                ],
            }
        ],
    },
    {
        "code": "AR",
        "name": "Argentina",
        "priority_rank": 10,
        "diaspora_population_estimate": 101502,
        "prioritization_source_url": BRASILEIROS_EXTERIOR_URL,
        "programs": [
            {
                "code": "AR_MIGRACIONES",
                "name": "Direccion Nacional de Migraciones",
                "description": "Normativa oficial de residencia e migracao na Argentina.",
                "version": MVP_PROGRAM_VERSION,
                "sources": [
                    {
                        "source_key": "ar_migraciones",
                        "source_type": "html",
                        "source_url": "https://www.argentina.gob.ar/interior/migraciones",
                        "robots_url": "https://www.argentina.gob.ar/robots.txt",
                        "terms_url": None,
                        "schedule_cron": "40 4 * * *",
                        "document_title": "Migraciones Argentina - Portal Oficial",
                    }
                ],
            }
        ],
    },
    {
        "code": "FR",
        "name": "Franca",
        "priority_rank": 11,
        "diaspora_population_estimate": 95000,
        "prioritization_source_url": BRASILEIROS_EXTERIOR_URL,
        "programs": [
            {
                "code": "FR_FRANCE_VISAS",
                "name": "France-Visas",
                "description": "Portal oficial para solicitacao e regras de vistos na Franca.",
                "version": MVP_PROGRAM_VERSION,
                "sources": [
                    {
                        "source_key": "fr_france_visas",
                        "source_type": "html",
                        "source_url": "https://france-visas.gouv.fr/",
                        "robots_url": "https://france-visas.gouv.fr/robots.txt",
                        "terms_url": None,
                        "schedule_cron": "55 4 * * *",
                        "document_title": "France-Visas - Official Portal",
                    }
                ],
            }
        ],
    },
    {
        "code": "IE",
        "name": "Irlanda",
        "priority_rank": 12,
        "diaspora_population_estimate": 80000,
        "prioritization_source_url": BRASILEIROS_EXTERIOR_URL,
        "programs": [
            {
                "code": "IE_ISD_IMMIGRATION",
                "name": "Immigration Service Delivery",
                "description": "Informacoes oficiais de residencia e imigracao da Irlanda.",
                "version": MVP_PROGRAM_VERSION,
                "sources": [
                    {
                        "source_key": "ie_immigration_service_delivery",
                        "source_type": "html",
                        "source_url": "https://www.irishimmigration.ie/",
                        "robots_url": "https://www.irishimmigration.ie/robots.txt",
                        "terms_url": None,
                        "schedule_cron": "10 5 * * *",
                        "document_title": "Immigration Service Delivery - Official Site",
                    }
                ],
            }
        ],
    },
    {
        "code": "NL",
        "name": "Paises Baixos",
        "priority_rank": 13,
        "diaspora_population_estimate": 80000,
        "prioritization_source_url": BRASILEIROS_EXTERIOR_URL,
        "programs": [
            {
                "code": "NL_IND_IMMIGRATION",
                "name": "IND Immigration Rules",
                "description": "Regras oficiais de residencia e migracao nos Paises Baixos.",
                "version": MVP_PROGRAM_VERSION,
                "sources": [
                    {
                        "source_key": "nl_ind",
                        "source_type": "html",
                        "source_url": "https://ind.nl/en",
                        "robots_url": "https://ind.nl/robots.txt",
                        "terms_url": None,
                        "schedule_cron": "25 5 * * *",
                        "document_title": "IND - Official Immigration Portal",
                    }
                ],
            }
        ],
    },
    {
        "code": "CH",
        "name": "Suica",
        "priority_rank": 14,
        "diaspora_population_estimate": 64000,
        "prioritization_source_url": BRASILEIROS_EXTERIOR_URL,
        "programs": [
            {
                "code": "CH_SEM_ENTRY",
                "name": "SEM Entry and Residence",
                "description": "Regras oficiais de entrada e permanencia na Suica.",
                "version": MVP_PROGRAM_VERSION,
                "sources": [
                    {
                        "source_key": "ch_sem",
                        "source_type": "html",
                        "source_url": "https://www.sem.admin.ch/sem/en/home/themen/einreise.html",
                        "robots_url": "https://www.sem.admin.ch/robots.txt",
                        "terms_url": None,
                        "schedule_cron": "40 5 * * *",
                        "document_title": "SEM - Entry Requirements",
                    }
                ],
            }
        ],
    },
    {
        "code": "BE",
        "name": "Belgica",
        "priority_rank": 15,
        "diaspora_population_estimate": 50000,
        "prioritization_source_url": BRASILEIROS_EXTERIOR_URL,
        "programs": [
            {
                "code": "BE_DOFI_IMMIGRATION",
                "name": "DOFI Immigration Office",
                "description": "Informacoes oficiais do Office des Etrangers da Belgica.",
                "version": MVP_PROGRAM_VERSION,
                "sources": [
                    {
                        "source_key": "be_dofi",
                        "source_type": "html",
                        "source_url": "https://dofi.ibz.be/en",
                        "robots_url": "https://dofi.ibz.be/robots.txt",
                        "terms_url": None,
                        "schedule_cron": "55 5 * * *",
                        "document_title": "DOFI - Immigration Office",
                    }
                ],
            }
        ],
    },
]

# Coverage of score-rule fixtures seeded for MVP scoring tests.
MVP_RULE_FIXTURE_COUNTRY_CODES = frozenset({"US", "PT", "CA", "GB", "DE"})


def rule_coverage_status(country_code: str) -> str:
    if country_code.upper() in MVP_RULE_FIXTURE_COUNTRY_CODES:
        return "seeded_example"
    return "pending"


def expected_country_count() -> int:
    return len(MVP_COUNTRY_CATALOG)


def expected_program_count() -> int:
    return sum(len(country["programs"]) for country in MVP_COUNTRY_CATALOG)


def expected_source_count() -> int:
    return sum(
        len(program["sources"])
        for country in MVP_COUNTRY_CATALOG
        for program in country["programs"]
    )
