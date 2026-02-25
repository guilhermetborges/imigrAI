from app.core.config.base import BaseConfig


class DevConfig(BaseConfig):
    debug: bool = True
    log_level: str = "DEBUG"
