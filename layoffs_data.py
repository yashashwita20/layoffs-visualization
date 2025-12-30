import os
import json
import urllib.parse
import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, List, Optional, Tuple

import requests
from playwright.async_api import async_playwright


DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
)


@dataclass(frozen=True)
class Target:
    view_id: str
    share_id: str


def _requests_headers(user_agent: str) -> dict:

    return {"user-agent": user_agent, 
            "accept": "*/*",
            'x-airtable-accept-msgpack': 'true',
            'x-airtable-application-id': 'app1PaujS9zxVGUZ4',
            'x-airtable-inter-service-client': 'webClient',
            'x-airtable-page-load-id': 'pglfkMix40FCtovav',
            'x-early-prefetch': 'true',
            'x-requested-with': 'XMLHttpRequest',
            'x-time-zone': 'America/Chicago',
            'x-user-locale': 'en',
           }


def _parse_access_policy_expiry(read_url: str) -> Optional[datetime]:
    parsed = urllib.parse.urlparse(read_url)
    qs = urllib.parse.parse_qs(parsed.query)
    ap = qs.get("accessPolicy")
    if not ap:
        return None
    try:
        policy = json.loads(ap[0])
        exp = policy.get("expires")
        if not exp:
            return None
        return datetime.fromisoformat(exp.replace("Z", "+00:00"))
    except Exception:
        return None


def _extract_view_and_share(read_url: str) -> Tuple[Optional[str], Optional[str]]:
    parsed = urllib.parse.urlparse(read_url)

    # /v0.3/view/<VIEW_ID>/readSharedViewData
    parts = parsed.path.split("/")
    view_id = None
    try:
        i = parts.index("view")
        view_id = parts[i + 1]
    except Exception:
        pass

    qs = urllib.parse.parse_qs(parsed.query)
    share_id = None
    if "accessPolicy" in qs and qs["accessPolicy"]:
        try:
            policy = json.loads(qs["accessPolicy"][0])
            share_id = policy.get("shareId")
        except Exception:
            pass

    return view_id, share_id


def _is_preferred_variant(u: str) -> bool:
    # Prefer nested response format and avoid msgpack toggle variant
    return ("shouldUseNestedResponseFormat%22%3Atrue" in u) and ("allowMsgpackOfResult" not in u)


# +
async def discover_all_and_pick_readsharedviewdata_url_async(
    page_url: str,
    target: Target,
    user_agent: str = DEFAULT_UA,
    timeout_ms: int = 120_000,
    settle_ms: int = 12_000,
    log: Optional[Callable[[str], None]] = None,
) -> Tuple[str, List[str], List[str]]:
    """
    Returns (picked_url, all_unique_urls, matching_urls).
    """
    found: List[str] = []
    seen = set()
    matches: List[str] = []

    def _log(msg: str):
        if log:
            log(msg)

    async with async_playwright() as p:
        #browser = await p.chromium.launch(headless=True)
        browser = await p.chromium.launch(
                        headless=True,
                        executable_path="/usr/bin/chromium",
                        args=["--no-sandbox", "--disable-dev-shm-usage"],
                    )
        context = await browser.new_context(user_agent=user_agent)

        # Speed: block heavy assets
        async def route_handler(route):
            if route.request.resource_type in {"image", "media", "font", "stylesheet"}:
                await route.abort()
            else:
                await route.continue_()

        await context.route("**/*", route_handler)

        page = await context.new_page()

        async def on_request(req):
            u = req.url
            if "airtable.com/v0.3/view/" in u and "readSharedViewData?" in u:
                if u in seen:
                    return
                seen.add(u)
                found.append(u)

                view_id, share_id = _extract_view_and_share(u)
                expiry = _parse_access_policy_expiry(u)

                is_target = (view_id == target.view_id) and (share_id == target.share_id)
                if is_target:
                    matches.append(u)

#                 _log(
#                     f"Found readSharedViewData{' (TARGET)' if is_target else ''}\n"
#                     f"  viewId={view_id} shareId={share_id}\n"
#                     f"  expires={expiry}\n"
#                     f"  url={u}"
#                 )

        page.on("request", on_request)

        await page.goto(page_url, wait_until="domcontentloaded", timeout=timeout_ms)
        await page.wait_for_timeout(settle_ms)

        await context.close()
        await browser.close()

    if not found:
        raise RuntimeError(
            "No readSharedViewData requests captured. The page may have changed, "
            "loaded too slowly, or blocked headless."
        )

    if not matches:
        raise RuntimeError(
            f"Captured {len(found)} readSharedViewData URLs but none matched "
            f"view_id={target.view_id} share_id={target.share_id}."
        )

    matches.sort(key=lambda u: (0 if _is_preferred_variant(u) else 1, len(u)))
    picked = matches[0]
    return picked, found, matches


# -

def discover_picked_url(
    page_url: str,
    target: Target,
    user_agent: str = DEFAULT_UA,
    timeout_ms: int = 120_000,
    settle_ms: int = 12_000,
    log: Optional[Callable[[str], None]] = None,
) -> Tuple[str, List[str], List[str]]:
    """
    Sync wrapper for Streamlit / normal scripts.
    NOTE: In Jupyter, call the async function with `await` instead.
    """
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            raise RuntimeError(
                "discover_picked_url() was called inside a running event loop (Jupyter). "
                "Use: await discover_all_and_pick_readsharedviewdata_url_async(...)"
            )
    except RuntimeError:
        # no running loop => ok
        pass

    return asyncio.run(
        discover_all_and_pick_readsharedviewdata_url_async(
            page_url=page_url,
            target=target,
            user_agent=user_agent,
            timeout_ms=timeout_ms,
            settle_ms=settle_ms,
            log=log,
        )
    )


def fetch_json(read_url: str, user_agent: str = DEFAULT_UA, timeout: int = 90) -> dict:
    r = requests.get(read_url, headers=_requests_headers(user_agent), timeout=timeout)
    r.raise_for_status()
    return r.json()


def _maybe_load_dotenv():
    """
    For local dev only. Streamlit Cloud won't have python-dotenv unless you add it.
    Safe no-op if not installed.
    """
    try:
        from dotenv import load_dotenv  # type: ignore
        load_dotenv()
    except Exception:
        pass


def load_target() -> Target:

    _maybe_load_dotenv()

    # Streamlit secrets
    try:
        import streamlit as st
        view_id = str(st.secrets.get("AIRTABLE_VIEW_ID", "")).strip()
        share_id = str(st.secrets.get("AIRTABLE_SHARE_ID", "")).strip()
        if view_id and share_id:
            return Target(view_id=view_id, share_id=share_id)
    except Exception:
        pass

    # Env vars
    view_id = os.getenv("AIRTABLE_VIEW_ID", "").strip()
    share_id = os.getenv("AIRTABLE_SHARE_ID", "").strip()
    if not view_id or not share_id:
        raise RuntimeError("Missing AIRTABLE_VIEW_ID and/or AIRTABLE_SHARE_ID in env or Streamlit secrets.")
    return Target(view_id=view_id, share_id=share_id)


def load_page_url(default: str = "https://layoffs.fyi") -> str:
    _maybe_load_dotenv()

    try:
        import streamlit as st
        v = str(st.secrets.get("PAGE_URL", "")).strip()
        if v:
            return v
    except Exception:
        pass

    v = os.getenv("PAGE_URL", "").strip()
    return v if v else default
