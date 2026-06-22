from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.http_security import RequestBodySizeLimitMiddleware, SecurityHeadersMiddleware
from app.core.metrics import mark_service_down, mark_service_up
from app.core.observability import RequestLoggingMiddleware, configure_logging
from app.db.engine import engine

settings = get_settings()
configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.init_local_database and settings.database_url.startswith("sqlite"):
        from app.db.base import Base

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    mark_service_up("api")
    yield
    mark_service_down("api")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
)

if settings.force_https_redirect:
    app.add_middleware(HTTPSRedirectMiddleware)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)
app.add_middleware(RequestBodySizeLimitMiddleware, max_body_bytes=settings.max_request_body_bytes)
app.add_middleware(SecurityHeadersMiddleware, settings=settings)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

app.include_router(api_router)
