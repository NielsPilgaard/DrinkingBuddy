"""Magic-link host (app.<DOMAIN>): OS link-verification files + browser fallback.

Traefik routes only /verify and /.well-known/* on app.<DOMAIN> here (see
docker-compose.prod.yml). When the app is installed, iOS/Android open
/verify?token=... straight in the app after verifying the files below; this
router's /verify page only renders when they don't (app missing, unverified
link, desktop mail client).
"""

import html
import json
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse

from app.config import settings

router = APIRouter(include_in_schema=False)


@router.get("/.well-known/apple-app-site-association")
async def apple_app_site_association() -> dict:
    if not settings.apple_team_id:
        raise HTTPException(status_code=404)
    return {
        "applinks": {
            "details": [
                {
                    "appIDs": [f"{settings.apple_team_id}.{settings.app_bundle_id}"],
                    "components": [{"/": "/verify"}],
                }
            ]
        }
    }


@router.get("/.well-known/assetlinks.json")
async def android_asset_links() -> list[dict]:
    fingerprints = [
        f.strip() for f in settings.android_sha256_cert_fingerprints.split(",") if f.strip()
    ]
    if not fingerprints:
        raise HTTPException(status_code=404)
    return [
        {
            "relation": ["delegate_permission/common.handle_all_urls"],
            "target": {
                "namespace": "android_app",
                "package_name": settings.app_bundle_id,
                "sha256_cert_fingerprints": fingerprints,
            },
        }
    ]


@router.get("/verify")
async def magic_link_fallback(token: str = Query(default="")) -> HTMLResponse:
    # Percent-encoding leaves the token with no quotes, "<" or backslashes, so
    # the URL is safe both in the href (escaped) and in the JS string literal.
    app_url = f"{settings.app_deep_link_scheme}://verify?token={quote(token, safe='')}"
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="referrer" content="no-referrer">
<title>DrinkingBuddy sign-in</title>
</head>
<body style="font-family:sans-serif;background:#0e0e12;color:#eee;text-align:center;padding:48px">

<h1>Open DrinkingBuddy to sign in</h1>
<p><a href="{html.escape(app_url)}" style="color:#f5b041">Open the app</a></p>
<p>Open this link on the phone where DrinkingBuddy is installed.</p>
<script>location.replace({json.dumps(app_url)});</script>
</body>
</html>"""
    return HTMLResponse(
        page,
        headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"},
    )
