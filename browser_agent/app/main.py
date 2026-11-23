"""Disposable, read-only browser service.

All outbound browser traffic must use the HTTPS CONNECT egress proxy. The
proxy validates DNS answers and pins its TCP connection to a public IP.
"""
import asyncio
import base64
import hmac
import ipaddress
import os
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, HttpUrl
from playwright.async_api import async_playwright

INTERNAL_TOKEN = os.getenv("BROWSER_INTERNAL_TOKEN", "")
PROXY_SERVER = "http://egress-proxy:3128"
TIMEOUT_SECONDS = max(5, min(int(os.getenv("BROWSER_TIMEOUT_SECONDS", "20")), 30))
NAVIGATION_SEMAPHORE = asyncio.Semaphore(1)
app = FastAPI(title="Cerepath Read-only Browser", version="0.2.0")


class NavigateInput(BaseModel):
    url: HttpUrl


def require_internal_token(authorization: str | None = Header(default=None)) -> None:
    if not INTERNAL_TOKEN:
        raise HTTPException(status_code=503, detail="Browser internal token is not configured")
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not hmac.compare_digest(token, INTERNAL_TOKEN):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid internal token")


def validate_public_url(value: str) -> None:
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("Only absolute HTTPS URLs are allowed")
    if parsed.username or parsed.password:
        raise ValueError("Credentials embedded in URLs are not allowed")
    if parsed.port not in (None, 443):
        raise ValueError("Only HTTPS port 443 is allowed")
    host = parsed.hostname.rstrip(".").lower()
    if host in {"localhost", "metadata.google.internal"} or host.endswith((".localhost", ".local", ".internal", ".test")):
        raise ValueError("Local and internal hostnames are not allowed")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return
    if not address.is_global:
        raise ValueError("Only publicly routable destinations are allowed")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "cerepath-read-only-browser", "mode": "https_get_only"}


@app.post("/navigate", dependencies=[Depends(require_internal_token)])
async def navigate(body: NavigateInput) -> dict:
    url = str(body.url)
    try:
        validate_public_url(url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    async with NAVIGATION_SEMAPHORE:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                args=["--disable-quic"],
                proxy={"server": PROXY_SERVER},
            )
            try:
                context = await browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    accept_downloads=False,
                    java_script_enabled=True,
                    service_workers="block",
                    ignore_https_errors=False,
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
                    if not page.url or page.url == "about:blank":
                        raise HTTPException(status_code=422, detail="Navigation failed or destination was blocked") from exc

                title = (await page.title())[:300]
                screenshot = await page.screenshot(type="jpeg", quality=55, full_page=False)
                return {
                    "final_url": page.url,
                    "title": title,
                    "screenshot_b64": base64.b64encode(screenshot).decode("ascii"),
                    "mode": "read_only_https_get",
                    "warning": (
                        "Disposable session. Only HTTPS port 443 is reachable through the pinned-IP egress proxy. "
                        "Browser routing aborts non-GET requests. No cookies are retained."
                    ),
                }
            finally:
                await browser.close()
