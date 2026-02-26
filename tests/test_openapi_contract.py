from __future__ import annotations

from app.main import app

REQUIRED_PATHS: dict[str, set[str]] = {
    "/health/live": {"get"},
    "/health/ready": {"get"},
    "/countries": {"get"},
    "/countries/{country_code}/programs": {"get"},
    "/api/v1/auth/register": {"post"},
    "/api/v1/auth/login": {"post"},
    "/api/v1/auth/refresh": {"post"},
    "/api/v1/auth/me": {"get"},
    "/api/v1/assessments": {"post"},
    "/api/v1/assessments/{assessment_id}/status": {"get"},
    "/api/v1/assessments/{assessment_id}/breakdown": {"get"},
    "/api/v1/roadmaps": {"post"},
    "/api/v1/roadmaps/{roadmap_id}/status": {"get"},
    "/api/v1/roadmaps/{roadmap_id}": {"get"},
    "/api/v1/jobs/{job_id}": {"get"},
    "/api/v1/billing/webhook/stripe": {"post"},
}


def test_openapi_contract_required_paths_and_methods() -> None:
    spec = app.openapi()

    assert spec["openapi"].startswith("3.")
    paths = spec["paths"]
    for path, required_methods in REQUIRED_PATHS.items():
        assert path in paths, f"missing path in OpenAPI contract: {path}"
        available_methods = {method.lower() for method in paths[path].keys()}
        for method in required_methods:
            assert method in available_methods, f"missing method={method} for path={path}"


def test_openapi_contract_required_components() -> None:
    spec = app.openapi()
    schemas = spec["components"]["schemas"]

    required_schemas = {
        "TokenPairResponse",
        "UserResponse",
        "AssessmentQueuedRead",
        "AssessmentStatusRead",
        "AssessmentBreakdownRead",
        "RoadmapQueuedRead",
        "RoadmapStatusRead",
        "RoadmapDetailRead",
        "JobRead",
    }
    assert required_schemas.issubset(set(schemas.keys()))
