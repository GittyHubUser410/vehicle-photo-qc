"""Opt-in Cloudflare Access authentication; local-only mode stays the default."""

import os
import re
from urllib.parse import urlsplit

import jwt
from fastapi import Request
from starlette.concurrency import run_in_threadpool
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import JSONResponse


class AccessSecurity:
    def __init__(self):
        self.public_url = os.environ.get("QC_PUBLIC_URL", "").rstrip("/")
        team = os.environ.get("QC_ACCESS_TEAM_DOMAIN", "")
        self.audience = os.environ.get("QC_ACCESS_AUD", "")
        self.remote = bool(self.public_url or team or self.audience)
        self.host = ""
        if self.remote:
            parsed = urlsplit(self.public_url)
            if (
                parsed.scheme != "https"
                or not parsed.hostname
                or parsed.port
                or parsed.path
                or parsed.query
                or parsed.fragment
                or parsed.username
                or parsed.password
                or not re.fullmatch(r"[a-zA-Z0-9.-]+", parsed.hostname)
            ):
                raise RuntimeError("QC_PUBLIC_URL must be your HTTPS address, without a path or port.")
            if not re.fullmatch(r"[a-z0-9-]+\.cloudflareaccess\.com", team) or not self.audience.strip():
                raise RuntimeError("Remote mode requires QC_ACCESS_TEAM_DOMAIN and QC_ACCESS_AUD.")
            self.host = parsed.hostname
            self.issuer = "https://" + team
            self.keys = jwt.PyJWKClient(self.issuer + "/cdn-cgi/access/certs", timeout=5)

    def verify(self, token):
        key = self.keys.get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=self.audience,
            issuer=self.issuer,
            options={"require": ["exp", "iat", "iss", "aud", "sub", "email"]},
        )
        if not isinstance(claims["email"], str) or not claims["email"]:
            raise jwt.InvalidTokenError("Missing user identity")
        return claims


def configure_security(app):
    security = AccessSecurity()
    app.state.security = security
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "testserver"] + ([security.host] if security.remote else []),
    )
    origins = (
        {security.public_url}
        if security.remote
        else {
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "http://localhost:8001",
            "http://127.0.0.1:8001",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        }
    )

    @app.middleware("http")
    async def access_boundary(request: Request, call_next):
        request.state.user = "local"
        if not security.remote and (
            request.headers.get("cf-ray") or request.headers.get("Cf-Access-Jwt-Assertion")
        ):
            return JSONResponse(
                {"detail": "Configure remote authentication before connecting a tunnel."}, status_code=403
            )
        if security.remote:
            token = request.headers.get("Cf-Access-Jwt-Assertion", "")
            try:
                if not token:
                    raise jwt.InvalidTokenError("Missing token")
                claims = await run_in_threadpool(security.verify, token)
                request.state.user = claims["sub"]
                request.state.email = claims["email"]
            except (jwt.PyJWTError, ValueError, OSError):
                return JSONResponse(
                    {"detail": "Sign in through the configured remote app address, then retry."},
                    status_code=401,
                    headers={"Cache-Control": "no-store"},
                )
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            origin = request.headers.get("origin")
            if (security.remote and not origin) or (origin and origin not in origins):
                return JSONResponse(
                    {"detail": "Requests must come from this app's own address."}, status_code=403
                )
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["X-Frame-Options"] = "DENY"
        if security.remote:
            response.headers["Cache-Control"] = "no-store"
        return response

    return security
