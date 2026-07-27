import logging
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from pydantic import ValidationError
import os

from database import engine, get_db, Base
from models import License, LicenseStatus, PlanType
from schemas import (
    LicenseTrialClaimRequest,
    LicenseActivateRequest,
    LicenseResetHWIDRequest,
    PaymentWebhookEvent,
    JWTResponse,
    LicenseResponse,
    ErrorResponse,
)
from auth import (
    sign_jwt,
    generate_license_key,
    build_expiration,
    _sha256_hash,
    _now_utc,
    mask_hwid,
    settings as auth_settings,
)
from webhooks import handle_stripe_webhook, handle_gumroad_webhook

logger = logging.getLogger("uvicorn")

Base.metadata.create_all = lambda **kw: None  # migrations expected via alembic

app = FastAPI(
    title="LAFM License Server",
    description="Centralized license lifecycle server for LAFM Crypto Trading Terminal",
    version="1.0.1",
    docs_url="/docs",
    redoc_url="/redoc",
)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok", "service": "lafm-license-server", "version": "1.0.1"}


@app.post(
    "/v1/licenses/trial/claim",
    response_model=JWTResponse,
    responses={400: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
    tags=["licenses"],
)
@limiter.limit(os.getenv("RATE_LIMIT_TRIAL", "5/minute"))
async def claim_trial(
    payload: LicenseTrialClaimRequest, request: Request, db: AsyncSession = Depends(get_db)
):
    hwid_hash = _sha256_hash(payload.hwid)
    existing = await db.execute(
        select(License).where(
            (License.hwid == hwid_hash) | (License.user_email == payload.user_email)
        )
    )
    found = existing.scalar_one_or_none()
    if found:
        logger.warning("Trial duplicate attempt for hwid=%s email=%s", mask_hwid(payload.hwid), payload.user_email)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este dispositivo o email ya utilizó sus 7 días de prueba.",
        )

    plan_type = PlanType.FREE_TRIAL_7D
    license_key = generate_license_key("LAFM-TRIAL", parts=2, part_len=4)
    starts_at = _now_utc()
    expires_at = starts_at + timedelta(days=7)

    license_obj = License(
        license_key=license_key,
        user_email=payload.user_email,
        status=LicenseStatus.TRIAL,
        plan_type=plan_type,
        hwid=hwid_hash,
        hostname=payload.hostname,
        max_devices=1,
        hwid_resets_left=3,
        starts_at=starts_at,
        expires_at=expires_at,
    )
    db.add(license_obj)
    await db.commit()
    await db.refresh(license_obj)

    token = sign_jwt(license_key, plan_type.value, hwid_hash, expires_at)
    logger.info("Trial claimed: %s for %s", license_key, payload.user_email)
    return JWTResponse(
        access_token=token,
        expires_in=int((expires_at - starts_at).total_seconds()),
        license=LicenseResponse.model_validate(license_obj),
    )


@app.post(
    "/v1/licenses/activate",
    response_model=JWTResponse,
    responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    tags=["licenses"],
)
@limiter.limit(os.getenv("RATE_LIMIT_ACTIVATE", "10/minute"))
async def activate_license(
    payload: LicenseActivateRequest, request: Request, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(License).where(License.license_key == payload.license_key))
    license_obj = result.scalar_one_or_none()
    if not license_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="License key not found")

    now = _now_utc()
    if license_obj.expires_at < now and license_obj.plan_type != PlanType.LIFETIME:
        if license_obj.status != LicenseStatus.EXPIRED:
            license_obj.status = LicenseStatus.EXPIRED
            await db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Suscripción vencida. Por favor renueva tu plan.",
        )

    if not license_obj.hwid:
        license_obj.hwid = _sha256_hash(payload.hwid)
        license_obj.hostname = payload.hostname
        await db.commit()
    else:
        if license_obj.hwid != _sha256_hash(payload.hwid):
            logger.warning(
                "HWID mismatch for %s. Current=%s Incoming=%s",
                payload.license_key,
                mask_hwid(license_obj.hwid),
                mask_hwid(payload.hwid),
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="HWID does not match the bound device.",
            )

    license_obj.status = LicenseStatus.ACTIVE
    license_obj.is_revoked = False
    await db.commit()
    await db.refresh(license_obj)

    token = sign_jwt(
        license_obj.license_key,
        license_obj.plan_type.value,
        license_obj.hwid or _sha256_hash(payload.hwid),
        license_obj.expires_at,
    )
    return JWTResponse(
        access_token=token,
        expires_in=int((license_obj.expires_at - now).total_seconds()),
        license=LicenseResponse.model_validate(license_obj),
    )


@app.post(
    "/v1/licenses/reset-hwid",
    response_model=LicenseResponse,
    responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    tags=["licenses"],
)
async def reset_hwid(
    payload: LicenseResetHWIDRequest, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(License).where(License.license_key == payload.license_key))
    license_obj = result.scalar_one_or_none()
    if not license_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="License key not found")

    if license_obj.plan_type == PlanType.FREE_TRIAL_7D:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Trial licenses cannot reset HWID.",
        )
    if license_obj.plan_type == PlanType.LIFETIME:
        if license_obj.hwid_resets_left <= 0:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Lifetime license HWID reset limit reached.",
            )
        license_obj.hwid_resets_left -= 1
    else:
        if license_obj.hwid_resets_left <= 0:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="HWID reset limit reached for this plan.",
            )
        license_obj.hwid_resets_left -= 1

    license_obj.hwid = _sha256_hash(payload.hwid)
    license_obj.hostname = payload.hostname
    license_obj.status = LicenseStatus.ACTIVE
    await db.commit()
    await db.refresh(license_obj)
    logger.info("HWID reset for %s. Resets left=%s", payload.license_key, license_obj.hwid_resets_left)
    return LicenseResponse.model_validate(license_obj)


@app.get("/v1/licenses/status/{license_key}", response_model=LicenseResponse, tags=["licenses"])
async def get_license_status(license_key: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(License).where(License.license_key == license_key))
    license_obj = result.scalar_one_or_none()
    if not license_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="License key not found")
    return LicenseResponse.model_validate(license_obj)


@app.post(
    "/v1/webhooks/stripe",
    tags=["webhooks"],
    include_in_schema=False,
)
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    try:
        import stripe as stripe_sdk
        stripe_sdk.api_key = os.getenv("STRIPE_SECRET_KEY", "")
        webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
        event = stripe_sdk.Webhook.construct_event(payload=body, sig_header=sig_header, secret=webhook_secret)
        event_type = event["type"]
        data = event["data"]["object"]
        event_wrapper = PaymentWebhookEvent(event_type=event_type, payload=dict(data))
        response = await handle_stripe_webhook(db, event_wrapper)
        return JSONResponse(content=response)
    except Exception as exc:
        logger.exception("Stripe webhook error: %s", exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@app.post(
    "/v1/webhooks/gumroad",
    tags=["webhooks"],
    include_in_schema=False,
)
async def gumroad_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        body = await request.json()
        event_type = body.get("product_event_type") or body.get("event_type", "")
        event_wrapper = PaymentWebhookEvent(event_type=event_type, payload=body)
        response = await handle_gumroad_webhook(db, event_wrapper)
        return JSONResponse(content=response)
    except Exception as exc:
        logger.exception("Gumroad webhook error: %s", exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("LAFM License Server started")


@app.on_event("shutdown")
async def on_shutdown():
    await engine.dispose()
