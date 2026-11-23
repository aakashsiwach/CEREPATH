import asyncio
import hmac
import ipaddress
import os
import socket
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, HttpUrl
from playwright.async_api import async_playwright

INTERNAL_TOKEN = os.getenv("BROWSER_INTERNAL_TOKEN", "")
TIMEOUT_SECONDS = max(5, min(int(os.getenv("BROWSER_TIMEOUT_SECONDS", "20")), 30))
NAVIGATION_SEMAPHORE = asyncio.Semaphore(1)
app = FastAPI(title="Aakash AI Read-only Browser", version="0.1.0")


class NavigateInput(BaseModel):
    url: HttpUrl


def require_internal_token(authorization: str | None = Header(default=None)) -> None:
    if not INTERNAL_TOKEN:
        raise HTTPException(status_code=503, detail="Browser internal token is not configured")
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not hmac.compare_digest(token, INTERNAL_TOKEN):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid internal token")


def _resolve_public_host(host: str) -> None:
    lowered = host.lower().rstrip(".")
    if lowered in {"localhost", "metadata.google.internal"} or lowered.endswith((".localhost", ".local", ".internal", ".test")):
        raise ValueError("Local and internal hostnames are not allowed")
    try:
        literal = ipaddress.ip_address(lowered)
        addresses = [literal]
    except ValueError:
        try:
            records = socket.getaddrinfo(lowered, None, type=socket.SOCK_STREAM)
        except socket.gaierror as exc:
            raise ValueError("Could not resolve the destination host") from exc
        addresses = [ipaddress.ip_address(record[4][0]) for record in records]
    if not addresses or any(not address.is_global for address in addresses):
        raise ValueError("Only publicly routable destination addresses are allowed")


def validate_public_url(value: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Only absolute HTTP and HTTPS URLs are allowed")
    if parsed.username or parsed.password:
        raise ValueError("Credentials embedded in URLs are not allowed")
    if parsed.port not in (None, 80, 443):
        raise ValueError("Only standard HTTP/HTTPS ports are allowed")
    _resolve_public_host(parsed.hostname)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "aakash-ai-read-only-browser"}


@app.post("/navigate", dependencies=[Depends(require_internal_token)])
async def navigate(body: NavigateInput) -> dict:
    url = str(body.url)
    try:
        validate_public_url(url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    async with NAVIGATION_SEMAPHORE:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
            try:
                context = await browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    accept_downloads=False,
                    java_script_enabled=True,
                    service_workers="block",
                )
                page = await context.new_page()
                page.set_default_navigation_timeout(TIMEOUT_SECONDS * 1000)
                page.set_default_timeout(TIMEOUT_SECONDS * 1000)

                async def guard_request(route):
                    request = route.request
                    try:
                        if request.method != "GET":
                            await route.abort("blockedbyclient")
                            return
                        validate_public_url(request.url)
                        await route.continue_()
                    except Exception:
                        await route.abort("blockedbyclient")

                await page.route("**/*", guard_request)
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT_SECONDS * 1000)
                except Exception as exc:
                    # A page may partially load even if an optional resource or timeout fails.
                    if not page.url or page.url == "about:blank":
                        raise HTTPException(status_code=422, detail="Navigation failed or destination was blocked") from exc
                title = await page.title()
                screenshot = await page.screenshot(type="jpeg", quality=55, full_page=False)
                import base64
                return {
                    "final_url": page.url,
                    "title": title[:300],
                    "screenshot_b64": base64.b64encode(screenshot).decode("ascii"),
                    "mode": "read_only_get",
                    "warning": "Disposable session. No cookies are retained; non-GET browser requests are blocked.",
                }
            finally:
                await browser.close()
