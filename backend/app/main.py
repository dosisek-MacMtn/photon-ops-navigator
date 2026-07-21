from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.adapters.base import ProviderNotFoundError
from app.api import router
from app.config import get_settings
from app.database import engine

settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version="0.2.0",
    description="Provider-neutral fiber network operations analysis API",  # gitleaks:allow
    docs_url=None if settings.environment == "production" else "/docs",
    redoc_url=None if settings.environment == "production" else "/redoc",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


auth_router = APIRouter(prefix="/api/auth")


@auth_router.get("/config")
async def auth_config():
    if settings.auth_mode == "disabled":
        return {"mode": "disabled"}
    if not settings.entra_client_id:
        raise HTTPException(status_code=503, detail="Microsoft Entra ID is not configured")
    return {
        "mode": "entra",
        "tenant_id": settings.entra_tenant_id,
        "client_id": settings.entra_client_id,
        "authority": settings.entra_authority,
        "api_scope": settings.entra_api_scope,
    }


app.include_router(auth_router)
app.include_router(router)


def _health_payload():
    return {
        "status": "ok",
        "service": "photon-ops-api",
        "environment": settings.environment,
    }


@app.get("/")
async def root_health():
    return _health_payload()


@app.get("/health")
async def health():
    return _health_payload()


@app.get("/ready")
async def readiness():
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database is not ready") from exc
    return {"status": "ready"}


@app.exception_handler(ProviderNotFoundError)
async def not_found_handler(_: Request, exc: ProviderNotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(NotImplementedError)
async def not_implemented_handler(_: Request, exc: NotImplementedError):
    return JSONResponse(status_code=501, content={"detail": str(exc)})


@app.exception_handler(ValueError)
async def validation_handler(_: Request, exc: ValueError):
    return JSONResponse(status_code=422, content={"detail": str(exc)})
