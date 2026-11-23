"""Create a local .env with fresh random secrets. Does not contact any service."""
from pathlib import Path
import secrets

ROOT = Path(__file__).resolve().parents[1]
example = ROOT / ".env.example"
target = ROOT / ".env"

if target.exists():
    raise SystemExit(".env already exists. Refusing to overwrite existing local secrets.")

content = example.read_text(encoding="utf-8")
replacements = {
    "CHANGE_ME_USE_A_LONG_RANDOM_PASSWORD": secrets.token_urlsafe(36),
    "CHANGE_ME_USE_AT_LEAST_32_RANDOM_BYTES": secrets.token_urlsafe(48),
    "CHANGE_ME_USE_A_DIFFERENT_LONG_RANDOM_TOKEN": secrets.token_urlsafe(48),
}
for old, new in replacements.items():
    content = content.replace(old, new)
target.write_text(content, encoding="utf-8")
try:
    target.chmod(0o600)
except OSError:
    pass
print("Created .env with independent random secrets. Keep it private; it is git-ignored.")
