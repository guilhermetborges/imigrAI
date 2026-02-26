from app.core.config.base import BaseConfig


class ProdConfig(BaseConfig):
    debug: bool = False
    log_level: str = "INFO"
    force_https_redirect: bool = True
