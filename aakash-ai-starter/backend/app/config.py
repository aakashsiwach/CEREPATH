import os


def required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Required environment variable {name} is not set")
    return value


DATABASE_URL = required_env("DATABASE_URL")
AAKASH_ADMIN_TOKEN = required_env("AAKASH_ADMIN_TOKEN")
BROWSER_INTERNAL_TOKEN = required_env("BROWSER_INTERNAL_TOKEN")
BROWSER_AGENT_URL = os.getenv("BROWSER_AGENT_URL", "http://browser-agent:8001").rstrip("/")
APP_ENV = os.getenv("APP_ENV", "local")
