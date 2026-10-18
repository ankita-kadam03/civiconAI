from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(BACKEND_DIR / ".env"), str(ROOT_DIR / ".env")),
        env_file_encoding="utf-8-sig",
        extra="ignore",
    )

    port: int = 8000
    app_env: str = "development"
    allow_memory_db: bool = Field(default=False, validation_alias=AliasChoices("ALLOW_MEMORY_DB", "DEMO_MODE"))
    fresh_start: bool = False
    resync_service_area: bool = Field(
        default=False,
        validation_alias=AliasChoices("RESYNC_SERVICE_AREA", "RESEED_SERVICE_AREA"),
    )
    time_scale: float = Field(default=1, validation_alias=AliasChoices("TIME_SCALE", "DEMO_TIME_SCALE"))
    seed_bootstrap_users: str = Field(default="", validation_alias=AliasChoices("SEED_BOOTSTRAP_USERS", "DEMO_SEED_CONFIRM"))
    bootstrap_user_password: str = Field(default="", validation_alias=AliasChoices("SEED_BOOTSTRAP_PASSWORD", "DEMO_USER_PASSWORD"))
    expose_password_reset_token: bool = Field(
        default=False,
        validation_alias=AliasChoices("EXPOSE_PASSWORD_RESET_TOKEN", "EXPOSE_RESET_TOKEN_IN_DEV"),
    )
    service_area_name: str = Field(default="", validation_alias=AliasChoices("SERVICE_AREA_NAME", "DEFAULT_REGION_NAME"))
    service_area_code: str = Field(default="primary", validation_alias=AliasChoices("SERVICE_AREA_CODE", "DEFAULT_REGION_CODE"))
    default_map_lat: float | None = Field(default=None, validation_alias=AliasChoices("DEFAULT_MAP_LAT", "DEFAULT_REGION_LAT"))
    default_map_lng: float | None = Field(default=None, validation_alias=AliasChoices("DEFAULT_MAP_LNG", "DEFAULT_REGION_LNG"))
    region_l1_radius_m: float = 3500
    region_l2_radius_m: float = 15000
    region_l3_radius_m: float = 40000
    region_l1_a_lat_offset: float = 0.012
    region_l1_a_lng_offset: float = -0.008
    region_l1_b_lat_offset: float = -0.010
    region_l1_b_lng_offset: float = 0.011
    seed_citizen_1_email: str = Field(default="citizen.one@example.com", validation_alias=AliasChoices("SEED_CITIZEN_1_EMAIL", "SEED_CITIZEN_EMAIL"))
    seed_citizen_2_email: str = "citizen.two@example.com"
    seed_officer_l1_a_email: str = Field(default="l1.wardnorth@example.com", validation_alias=AliasChoices("SEED_OFFICER_L1_A_EMAIL", "SEED_OFFICER_L1_EMAIL"))
    seed_officer_l1_b_email: str = "l1.wardsouth@example.com"
    seed_officer_l2_email: str = "l2.regional@example.com"
    seed_officer_l3_email: str = "l3.municipal@example.com"

    @property
    def seed_citizen_email(self) -> str:
        return self.seed_citizen_1_email

    @property
    def seed_officer_l1_email(self) -> str:
        return self.seed_officer_l1_a_email

    jwt_secret: str = ""
    jwt_access_minutes: int = 20
    jwt_refresh_days: int = 7
    internal_task_secret: str = ""

    google_cloud_project: str = ""
    google_cloud_location: str = "us-central1"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    gcs_bucket: str = ""
    pubsub_topic_events: str = "incident-events"
    push_service_account: str = ""
    internal_oidc_audience: str = ""
    bigquery_dataset: str = ""
    require_gemini: bool = Field(default=True, validation_alias=AliasChoices("REQUIRE_GEMINI", "REQUIRE_VERTEX_AI"))
    require_bigquery: bool = Field(default=True, validation_alias="REQUIRE_BIGQUERY")
    google_server_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("GOOGLE_SERVER_API_KEY", "GOOGLE_WEATHER_SERVER_KEY"),
    )
    google_maps_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("GOOGLE_MAPS_API_KEY", "GOOGLE_WEATHER_API_KEY"),
    )
    firebase_project_id: str = ""
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174"
    database_url: str = Field(default="", description="Legacy; ignored")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def signing_secret(self) -> str:
        if self.jwt_secret:
            return self.jwt_secret
        if self.is_production:
            raise RuntimeError("JWT_SECRET is required in production")
        env = self.app_env.lower()
        if env in ("development", "dev", "local") or self.allow_memory_db:
            return "civicon-local-dev-signing-key-not-for-production"
        raise RuntimeError("JWT_SECRET is required outside local memory mode")

    @property
    def demo_mode(self) -> bool:
        """Legacy alias for allow_memory_db."""
        return self.allow_memory_db

    @property
    def demo_time_scale(self) -> float:
        return self.time_scale

    @property
    def demo_seed_confirm(self) -> str:
        return self.seed_bootstrap_users

    @property
    def demo_user_password(self) -> str:
        return self.bootstrap_user_password

    @property
    def firebase_project_resolved(self) -> str:
        return (self.firebase_project_id or self.google_cloud_project or "").strip()

    @property
    def map_center(self) -> tuple[float, float] | None:
        if self.default_map_lat is not None and self.default_map_lng is not None:
            return (self.default_map_lat, self.default_map_lng)
        return None

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def integration_startup_strict(self) -> bool:
        """When true, missing Gemini or BigQuery prevents API startup."""
        return self.is_production

    @property
    def uses_firestore(self) -> bool:
        return bool(self.firebase_project_resolved) and not self.allow_memory_db

    @property
    def gemini_model_candidates(self) -> list[str]:
        primary = (self.gemini_model or "gemini-2.5-flash").strip()
        # gemini-2.0-* was shut down in June 2026.
        if primary.startswith("gemini-2.0"):
            primary = "gemini-2.5-flash"
        ordered = [primary, "gemini-2.5-flash", "gemini-3.8-flash", "gemini-3.5-flash", "gemini-2.5-flash-lite"]
        seen: list[str] = []
        for name in ordered:
            if name and name not in seen:
                seen.append(name)
        return seen


@lru_cache
def get_settings() -> Settings:
    return Settings()
