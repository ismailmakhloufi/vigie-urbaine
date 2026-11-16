from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "urbanbutterfly"

    mongo_uri: str = "mongodb://admin:urbanbutterfly@localhost:27017"
    mongo_db: str = "urban_butterfly"

    api_host: str = "127.0.0.1"
    api_port: int = 8000

    security_mode: str = "demo"  # demo (localhost) ou secure (postes autorisés)
    auth_operator_password: str = ""
    auth_viewer_password: str = ""
    auth_agency_key: str = ""
    auth_cookie_secure: bool = False  # True derrière HTTPS
    auth_allowed_origins: str = ""  # origines HTTPS, séparées par des virgules


@lru_cache
def get_settings() -> Settings:
    return Settings()
