import os

OWNER_USER_ID = "00000000-0000-4000-8000-000000000001"


def required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Required environment variable {name} is not set")
    return value


DATABASE_URL = required_env("DATABASE_URL")
CEREPATH_OWNER_TOKEN = required_env("CEREPATH_OWNER_TOKEN")
BROWSER_INTERNAL_TOKEN = required_env("BROWSER_INTERNAL_TOKEN")
BROWSER_AGENT_URL = os.getenv("BROWSER_AGENT_URL", "http://browser-agent:8001").rstrip("/")
APP_ENV = os.getenv("APP_ENV", "local").strip().lower()
SESSION_TTL_HOURS = max(1, min(int(os.getenv("CEREPATH_SESSION_TTL_HOURS", "12")), 168))
SESSION_COOKIE_NAME = "cerepath_session"
RUN_DB_MIGRATIONS = os.getenv("RUN_DB_MIGRATIONS", "false").lower() in {"1", "true", "yes"}
REMOTE_PROVIDER_MEMORY_SHARING = (
    os.getenv("REMOTE_PROVIDER_MEMORY_SHARING", "false").strip().lower()
    in {"1", "true", "yes", "on"}
)
