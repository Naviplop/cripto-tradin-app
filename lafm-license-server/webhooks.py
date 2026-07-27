import logging
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

from fastapi import Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from models import License, PlanType, LicenseStatus
from auth import build_expiration, _now_utc
from schemas import PaymentWebhookEvent

logger = logging.getLogger("lafm.license.webhooks")


class StripeEventType(str, Enum):
    CHECKOUT_COMPLETED = "checkout.session.completed"
    INVOICE_PAYMENT_SUCCEEDED = "invoice.payment_succeeded"
    SUBSCRIPTION_DELETED = "customer.subscription.deleted"
    CHARGE_REFUNDED = "charge.refunded"


def _plan_type_from_stripe_price(price_id: Optional[str], metadata: Optional[dict]) -> PlanType:
    if not price_id and not metadata:
        raise ValueError("Missing price metadata in payment event")
    if metadata and metadata.get("la_plan_type"):
        raw = metadata["la_plan_type"]
        return PlanType(raw)
    price_id = (price_id or "").lower()
    if "trial" in price_id:
        return PlanType.FREE_TRIAL_7D
    if "3m" in price_id or "quarter" in price_id:
        return PlanType.SUBSCRIPTION_3M
    if "6m" in price_id or "half" in price_id:
        return PlanType.SUBSCRIPTION_6M
    if "1y" in price_id or "annual" in price_id:
        return PlanType.ANNUAL_1Y
    if "lifetime" in price_id:
        return PlanType.LIFETIME
    raise ValueError(f"Unsupported Stripe price id: {price_id}")


def _plan_type_from_gumroad_product_id(product_id: Optional[str]) -> PlanType:
    if not product_id:
        raise ValueError("Missing product_id in Gumroad event")
    product_id = product_id.lower()
    if "trial" in product_id:
        return PlanType.FREE_TRIAL_7D
    if "3m" in product_id or "quarter" in product_id:
        return PlanType.SUBSCRIPTION_3M
    if "6m" in product_id or "half" in product_id:
        return PlanType.SUBSCRIPTION_6M
    if "1y" in product_id or "annual" in product_id:
        return PlanType.ANNUAL_1Y
    if "lifetime" in product_id:
        return PlanType.LIFETIME
    raise ValueError(f"Unsupported Gumroad product_id: {product_id}")


async def _get_license_by_key(db: AsyncSession, license_key: str) -> Optional[License]:
    result = await db.execute(select(License).where(License.license_key == license_key))
    return result.scalar_one_or_none()


async def _upsert_license(
    db: AsyncSession,
    license_key: str,
    user_email: str,
    plan_type: PlanType,
    starts_at: Optional[datetime] = None,
    hwid: Optional[str] = None,
    hostname: Optional[str] = None,
    max_devices: int = 1,
    hwid_resets_left: int = 3,
) -> License:
    existing = await _get_license_by_key(db, license_key)
    starts_at = starts_at if starts_at else _now_utc()
    expires_at = build_expiration(plan_type.value, starts_at)

    if existing:
        existing.status = LicenseStatus.ACTIVE
        existing.plan_type = plan_type
        existing.expires_at = expires_at
        existing.starts_at = starts_at
        existing.hwid = hwid or existing.hwid
        existing.hostname = hostname or existing.hostname
        existing.max_devices = max(max_devices, existing.max_devices)
        existing.hwid_resets_left = max(hwid_resets_left, existing.hwid_resets_left)
        existing.is_revoked = False
        existing.revoked_at = None
        await db.commit()
        await db.refresh(existing)
        return existing

    license_obj = License(
        license_key=license_key,
        user_email=user_email,
        status=LicenseStatus.ACTIVE,
        plan_type=plan_type,
        hwid=hwid,
        hostname=hostname,
        max_devices=max_devices,
        hwid_resets_left=hwid_resets_left,
        starts_at=starts_at,
        expires_at=expires_at,
    )
    db.add(license_obj)
    await db.commit()
    await db.refresh(license_obj)
    return license_obj


async def _extend_subscription(db: AsyncSession, license_key: str, plan_type: PlanType) -> License:
    existing = await _get_license_by_key(db, license_key)
    if not existing:
        raise ValueError(f"License {license_key} not found")
    starts_at = _now_utc()
    expires_at = build_expiration(plan_type.value, starts_at)
    existing.plan_type = plan_type
    existing.expires_at = expires_at
    existing.starts_at = starts_at
    existing.status = LicenseStatus.ACTIVE
    existing.is_revoked = False
    existing.revoked_at = None
    await db.commit()
    await db.refresh(existing)
    return existing


async def _revoke_license(db: AsyncSession, license_key: str, reason: str = "REVOKED") -> License:
    existing = await _get_license_by_key(db, license_key)
    if not existing:
        raise ValueError(f"License {license_key} not found")
    existing.status = LicenseStatus.REVOKED
    existing.is_revoked = True
    existing.revoked_at = _now_utc()
    await db.commit()
    await db.refresh(existing)
    return existing


async def handle_stripe_webhook(db: AsyncSession, event: PaymentWebhookEvent) -> dict:
    event_type = event.event_type
    payload = event.payload

    if event_type == StripeEventType.CHECKOUT_COMPLETED.value:
        customer_email = payload.get("customer_details", {}).get("email") or payload.get("customer_email")
        line_items = payload.get("line_items", {}).get("data", [])
        metadata = payload.get("metadata", {}) or {}
        price_id = None
        if line_items:
            price_id = line_items[0].get("price", {}).get("id")
        if not customer_email:
            raise ValueError("Missing customer email in checkout.session.completed")
        plan_type = _plan_type_from_stripe_price(price_id, metadata)
        license_key = metadata.get("la_license_key") or generate_license_key_for_plan(plan_type)
        await _upsert_license(
            db=db,
            license_key=license_key,
            user_email=customer_email,
            plan_type=plan_type,
            hwid=metadata.get("la_hwid"),
            hostname=metadata.get("la_hostname"),
            max_devices=int(metadata.get("la_max_devices", 1)),
            hwid_resets_left=int(metadata.get("la_hwid_resets", 3)),
        )
        logger.info("Stripe checkout completed: issued license %s to %s", license_key, customer_email)
        return {"status": "issued", "license_key": license_key}

    if event_type == StripeEventType.INVOICE_PAYMENT_SUCCEEDED.value:
        customer_email = payload.get("customer_email") or payload.get("customer_details", {}).get("email")
        subscription = payload.get("subscription") or payload.get("id")
        metadata = payload.get("metadata", {}) or payload.get("subscription_details", {}).get("metadata", {}) or {}
        price_id = payload.get("price", {}).get("id") if isinstance(payload, dict) else None
        line_items = payload.get("lines", {}).get("data", [])
        if not price_id and line_items:
            price_id = line_items[0].get("price", {}).get("id")
        if not customer_email and subscription:
            customer_email = metadata.get("customer_email")
        if not customer_email:
            raise ValueError("Missing customer email in invoice.payment_succeeded")
        plan_type = _plan_type_from_stripe_price(price_id, metadata)
        license_key = metadata.get("la_license_key")
        if not license_key:
            raise ValueError("Missing license_key in renewal metadata")
        extended = await _extend_subscription(db, license_key, plan_type)
        logger.info("Subscription renewed for %s until %s", license_key, extended.expires_at.isoformat())
        return {"status": "renewed", "license_key": license_key}

    if event_type in (StripeEventType.SUBSCRIPTION_DELETED.value, StripeEventType.CHARGE_REFUNDED.value):
        customer_email = payload.get("customer_email") or payload.get("customer_details", {}).get("email")
        metadata = payload.get("metadata", {}) or {}
        license_key = metadata.get("la_license_key")
        if not license_key:
            raise ValueError("Missing license_key in refund/cancel metadata")
        revoked = await _revoke_license(db, license_key)
        logger.info("License revoked: %s", license_key)
        return {"status": "revoked", "license_key": license_key}

    raise ValueError(f"Unsupported Stripe event type: {event_type}")


async def handle_gumroad_webhook(db: AsyncSession, event: PaymentWebhookEvent) -> dict:
    payload = event.payload
    event_type = event.event_type

    if event_type == "sale":
        product_id = payload.get("product_id")
        product_name = payload.get("product_name", "")
        user_email = payload.get("email") or payload.get("buyer_email")
        sale_id = payload.get("sale_id") or payload.get("id")
        if not user_email or not product_id:
            raise ValueError("Missing email or product_id in Gumroad sale event")
        plan_type = _plan_type_from_gumroad_product_id(str(product_id))
        license_key = f"LAFM-PRO-{sale_id[-8:].upper()}"
        await _upsert_license(
            db=db,
            license_key=license_key,
            user_email=user_email,
            plan_type=plan_type,
            hwid=payload.get("la_hwid"),
            hostname=payload.get("la_hostname"),
            max_devices=int(payload.get("max_devices", 1)),
            hwid_resets_left=int(payload.get("hwid_resets", 3)),
        )
        logger.info("Gumroad sale processed: issued license %s to %s", license_key, user_email)
        return {"status": "issued", "license_key": license_key}

    raise ValueError(f"Unsupported Gumroad event type: {event_type}")


def generate_license_key_for_plan(plan_type: PlanType) -> str:
    if plan_type == PlanType.FREE_TRIAL_7D:
        return generate_license_key("LAFM-TRIAL", parts=2, part_len=4)
    if plan_type == PlanType.LIFETIME:
        return generate_license_key("LAFM-PRO", parts=3, part_len=4)
    return generate_license_key("LAFM-PRO", parts=3, part_len=4)
