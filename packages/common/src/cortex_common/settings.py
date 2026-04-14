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
    force_path_style: bool = Field(default=True, alias="CORTEX_S3_FORCE_PATH_STYLE")
    auto_create_bucket: bool = Field(default=True, alias="CORTEX_S3_AUTO_CREATE_BUCKET")
    upload_url_ttl_seconds: int = Field(default=3600, alias="CORTEX_S3_UPLOAD_URL_TTL_SECONDS")
    download_max_ttl_seconds: int = Field(
        default=86400,
        alias="CORTEX_S3_DOWNLOAD_MAX_TTL_SECONDS",
    )
    multipart_threshold_bytes: int = Field(
        default=16_777_216,
        alias="CORTEX_S3_MULTIPART_THRESHOLD_BYTES",
    )
    default_part_size_bytes: int = Field(
        default=8_388_608,
        alias="CORTEX_S3_DEFAULT_PART_SIZE_BYTES",
    )


class QueueSettings(_BaseEnvSettings):
    url: str = Field(default="redis://127.0.0.1:6379/0", alias="CORTEX_QUEUE_URL")


class AuthSettings(_BaseEnvSettings):
    mode: str = Field(default="dev", alias="CORTEX_AUTH_MODE")
    oidc_issuer: str = Field(default="https://auth.cortex.local", alias="CORTEX_OIDC_ISSUER")
    oidc_audience: str = Field(default="cortex-api", alias="CORTEX_OIDC_AUDIENCE")
    jwt_algorithm: str = Field(default="HS256", alias="CORTEX_AUTH_JWT_ALGORITHM")
    jwt_shared_secret: str = Field(
        default="cortex-dev-shared-secret",
        alias="CORTEX_AUTH_JWT_SHARED_SECRET",
    )
    jwks_url: str | None = Field(default=None, alias="CORTEX_AUTH_JWKS_URL")
    introspection_url: str | None = Field(default=None, alias="CORTEX_AUTH_INTROSPECTION_URL")
    introspection_client_id: str | None = Field(
        default=None,
        alias="CORTEX_AUTH_INTROSPECTION_CLIENT_ID",
    )
    introspection_client_secret: str | None = Field(
        default=None,
        alias="CORTEX_AUTH_INTROSPECTION_CLIENT_SECRET",
    )
    clock_skew_seconds: int = Field(default=30, alias="CORTEX_AUTH_CLOCK_SKEW_SECONDS")
    auto_provision_principals: bool = Field(
        default=True,
        alias="CORTEX_AUTH_AUTO_PROVISION_PRINCIPALS",
    )


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
