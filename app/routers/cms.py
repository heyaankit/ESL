"""CMS router — privacy policy, FAQ, contact us, and subscription management.

All endpoints return the legacy response format:
    {"status": "1", "data": ..., "message": ...}   — success
    {"status": "0", "data": null, "message": ...}   — failure
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.content import PrivacyPolicy, FAQ, ContactUs, UserSubscription
from app.utils.response import success, error

router = APIRouter(tags=["cms"])


# ---------------------------------------------------------------------------
# Pydantic schemas for JSON request bodies
# ---------------------------------------------------------------------------

class PrivacyPolicyAddRequest(BaseModel):
    content: str = Field(..., min_length=1, description="Privacy policy content")
    created_by: Optional[str] = Field(None, description="Creator identifier")


class FAQAddRequest(BaseModel):
    question: str = Field(..., min_length=1, description="FAQ question")
    answer: str = Field(..., min_length=1, description="FAQ answer")
    category: Optional[str] = Field(None, description="FAQ category")
    sort_order: int = Field(0, description="Sort order for display")


class ContactUsAddRequest(BaseModel):
    user_id: Optional[str] = Field(None, description="User ID")
    name: Optional[str] = Field(None, description="Sender name")
    email: Optional[str] = Field(None, description="Sender email")
    subject: Optional[str] = Field(None, description="Message subject")
    message: str = Field(..., min_length=1, description="Message body")


class SubscriptionVerifyRequest(BaseModel):
    user_id: str = Field(..., min_length=1, description="User ID")
    platform: Optional[str] = Field(None, description="Platform: ios, android, web")
    plan: Optional[str] = Field("free", description="Plan: free, premium, pro")
    status: Optional[str] = Field("active", description="Status: active, expired, cancelled")
    expiry_date: Optional[str] = Field(None, description="Expiry date string")
    transaction_id: Optional[str] = Field(None, description="Transaction ID")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _privacy_policy_to_dict(p: PrivacyPolicy) -> dict:
    return {
        "id": p.id,
        "content": p.content,
        "version": p.version,
        "created_by": p.created_by,
        "created_at": str(p.created_at) if p.created_at else None,
    }


def _faq_to_dict(f: FAQ) -> dict:
    return {
        "id": f.id,
        "question": f.question,
        "answer": f.answer,
        "category": f.category,
        "sort_order": f.sort_order,
        "created_at": str(f.created_at) if f.created_at else None,
    }


def _contact_us_to_dict(c: ContactUs) -> dict:
    return {
        "id": c.id,
        "user_id": c.user_id,
        "name": c.name,
        "email": c.email,
        "subject": c.subject,
        "message": c.message,
        "status": c.status,
        "created_at": str(c.created_at) if c.created_at else None,
    }


def _subscription_to_dict(s: UserSubscription) -> dict:
    return {
        "id": s.id,
        "user_id": s.user_id,
        "platform": s.platform,
        "plan": s.plan,
        "status": s.status,
        "expiry_date": s.expiry_date,
        "transaction_id": s.transaction_id,
        "created_at": str(s.created_at) if s.created_at else None,
        "updated_at": str(s.updated_at) if s.updated_at else None,
    }


# ---------------------------------------------------------------------------
# POST /privacy-policy/add  — add privacy policy entry
# ---------------------------------------------------------------------------

@router.post("/privacy-policy/add")
def add_privacy_policy(
    request: PrivacyPolicyAddRequest,
    db: Session = Depends(get_db),
):
    """Add a new privacy policy entry."""
    entry = PrivacyPolicy(
        content=request.content,
        created_by=request.created_by,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    return success(
        data=_privacy_policy_to_dict(entry),
        message="Privacy policy added successfully",
    )


# ---------------------------------------------------------------------------
# GET /privacy-policy  — return latest privacy policy entries (limit 10)
# ---------------------------------------------------------------------------

@router.get("/privacy-policy")
def get_privacy_policy(
    db: Session = Depends(get_db),
):
    """Return latest privacy policy entries (limit 10)."""
    entries = (
        db.query(PrivacyPolicy)
        .order_by(PrivacyPolicy.created_at.desc())
        .limit(10)
        .all()
    )

    return success(
        data=[_privacy_policy_to_dict(p) for p in entries],
        message="Privacy policy entries fetched successfully",
    )


# ---------------------------------------------------------------------------
# POST /faq/add  — add FAQ item
# ---------------------------------------------------------------------------

@router.post("/faq/add")
def add_faq(
    request: FAQAddRequest,
    db: Session = Depends(get_db),
):
    """Add a new FAQ item."""
    faq = FAQ(
        question=request.question,
        answer=request.answer,
        category=request.category,
        sort_order=request.sort_order,
    )
    db.add(faq)
    db.commit()
    db.refresh(faq)

    return success(
        data=_faq_to_dict(faq),
        message="FAQ added successfully",
    )


# ---------------------------------------------------------------------------
# GET /faq  — return all FAQs sorted by sort_order
# ---------------------------------------------------------------------------

@router.get("/faq")
def get_faqs(
    db: Session = Depends(get_db),
):
    """Return all FAQs sorted by sort_order."""
    faqs = (
        db.query(FAQ)
        .order_by(FAQ.sort_order.asc(), FAQ.created_at.asc())
        .all()
    )

    return success(
        data=[_faq_to_dict(f) for f in faqs],
        message="FAQs fetched successfully",
    )


# ---------------------------------------------------------------------------
# POST /contact-us/add  — create contact us message
# ---------------------------------------------------------------------------

@router.post("/contact-us/add")
def add_contact_us(
    request: ContactUsAddRequest,
    db: Session = Depends(get_db),
):
    """Create a new contact us message."""
    entry = ContactUs(
        user_id=request.user_id,
        name=request.name,
        email=request.email,
        subject=request.subject,
        message=request.message,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    return success(
        data=_contact_us_to_dict(entry),
        message="Contact message submitted successfully",
    )


# ---------------------------------------------------------------------------
# GET /contact-us  — return contact messages for a user_id
# ---------------------------------------------------------------------------

@router.get("/contact-us")
def get_contact_us(
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db),
):
    """Return contact messages for a user_id."""
    entries = (
        db.query(ContactUs)
        .filter(ContactUs.user_id == user_id)
        .order_by(ContactUs.created_at.desc())
        .all()
    )

    return success(
        data=[_contact_us_to_dict(c) for c in entries],
        message="Contact messages fetched successfully",
    )


# ---------------------------------------------------------------------------
# POST /subscription/verify  — store/update subscription status
# ---------------------------------------------------------------------------

@router.post("/subscription/verify")
def verify_subscription(
    request: SubscriptionVerifyRequest,
    db: Session = Depends(get_db),
):
    """Store or update a user's subscription status."""
    # Check if subscription already exists for this user
    existing = (
        db.query(UserSubscription)
        .filter(UserSubscription.user_id == request.user_id)
        .first()
    )

    if existing:
        # Update existing subscription
        if request.platform is not None:
            existing.platform = request.platform
        if request.plan is not None:
            existing.plan = request.plan
        if request.status is not None:
            existing.status = request.status
        if request.expiry_date is not None:
            existing.expiry_date = request.expiry_date
        if request.transaction_id is not None:
            existing.transaction_id = request.transaction_id
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)

        return success(
            data=_subscription_to_dict(existing),
            message="Subscription updated successfully",
        )

    # Create new subscription
    subscription = UserSubscription(
        user_id=request.user_id,
        platform=request.platform,
        plan=request.plan or "free",
        status=request.status or "active",
        expiry_date=request.expiry_date,
        transaction_id=request.transaction_id,
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)

    return success(
        data=_subscription_to_dict(subscription),
        message="Subscription created successfully",
    )
