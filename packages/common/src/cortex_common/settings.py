"""Runtime settings models."""

from functools import lru_cache

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class _BaseEnvSettings(BaseSettings):
    """Base settings class with consistent env behavior."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class AppSettings(_BaseEnvSettings):
    environment: str = Field(default="local", alias="CORTEX_ENV")
    host: str = Field(default="127.0.0.1", alias="CORTEX_HOST")
    port: int = Field(default=8080, alias="CORTEX_PORT")


class DatabaseSettings(_BaseEnvSettings):
    dsn: str = Field(default="sqlite+aiosqlite:///./.data/cortex.db", alias="CORTEX_DB_DSN")


class S3Settings(_BaseEnvSettings):
    endpoint: str = Field(default="http://127.0.0.1:9000", alias="CORTEX_S3_ENDPOINT")
    region: str = Field(default="us-east-1", alias="CORTEX_S3_REGION")
    bucket: str = Field(default="cortex-local", alias="CORTEX_S3_BUCKET")
    access_key: str = Field(default="minioadmin", alias="CORTEX_S3_ACCESS_KEY")
    secret_key: str = Field(default="minioadmin", alias="CORTEX_S3_SECRET_KEY")


class QueueSettings(_BaseEnvSettings):
    url: str = Field(default="redis://127.0.0.1:6379/0", alias="CORTEX_QUEUE_URL")


class AuthSettings(_BaseEnvSettings):
    mode: str = Field(default="dev", alias="CORTEX_AUTH_MODE")
    oidc_issuer: str = Field(default="https://auth.cortex.local", alias="CORTEX_OIDC_ISSUER")
    oidc_audience: str = Field(default="cortex-api", alias="CORTEX_OIDC_AUDIENCE")


class ParseSettings(_BaseEnvSettings):
    default_profile: str = Field(default="auto_default", alias="CORTEX_PARSE_DEFAULT_PROFILE")


class CogneeSettings(_BaseEnvSettings):
    enabled: bool = Field(default=False, alias="CORTEX_COGNEE_ENABLED")


class TelemetrySettings(_BaseEnvSettings):
    enabled: bool = Field(default=True, alias="CORTEX_OTEL_ENABLED")
    exporter_otlp_endpoint: str = Field(
        default="http://127.0.0.1:4318",
        alias="CORTEX_OTEL_EXPORTER_OTLP_ENDPOINT",
    )
    deployment_env: str = Field(default="local", alias="CORTEX_DEPLOYMENT_ENV")
    region: str = Field(default="local", alias="CORTEX_REGION")
    cluster: str = Field(default="devbox", alias="CORTEX_CLUSTER")


class CortexSettings(BaseModel):
    app: AppSettings
    database: DatabaseSettings
    s3: S3Settings
    queue: QueueSettings
    auth: AuthSettings
    parse: ParseSettings
    cognee: CogneeSettings
    telemetry: TelemetrySettings


@lru_cache(maxsize=1)
def load_settings() -> CortexSettings:
    """Load and cache the full Cortex settings tree."""
    return CortexSettings(
        app=AppSettings(),
        database=DatabaseSettings(),
        s3=S3Settings(),
        queue=QueueSettings(),
        auth=AuthSettings(),
        parse=ParseSettings(),
        cognee=CogneeSettings(),
        telemetry=TelemetrySettings(),
    )
