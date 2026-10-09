"""Comprehensive Test Suite for Healthcare Consent & Privacy Management (PROMPT 21).

Tests:
1. All 8 consent categories:
   - clinical care
   - health screening
   - wearable data
   - AI processing
   - research/analytics
   - notifications
   - data sharing
   - caregiver/family access
2. Mandatory consent fields:
   - subject
   - purpose
   - scope
   - recipient
   - created_at
   - expires_at where applicable
   - revoked_at
   - version
   - audit trail
3. Core operations:
   - grant
   - view
   - modify
   - revoke
4. AI agent consent verification before accessing protected data.
5. Revocable wearable access (instant sync cutoff when revoked).
6. Citizen Privacy Center REST API endpoints and audit logging.
"""

from datetime import datetime, timedelta, timezone
import pytest
from starlette.testclient import TestClient

from packages.clinical_models.consent import (
    ConsentCategory,
    ConsentStatus,
    HealthcareConsent,
    ConsentManager,
    consent_manager,
)
from packages.auth.jwt import decode_access_token
from scripts.seed_data import seed_all_demo_data
from services.ai_agent.prevention_agent import prevention_agent
from services.api.main import app
from services.store import store

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_data():
    seed_all_demo_data()


def get_token_for(email: str = "citizen@sevahealth.ai", password: str = "password123") -> str:
    res = client.post("/api/v1/auth/token", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]


# ==============================================================================
# 1. Verification of all 8 Consent Categories & Mandatory Fields
# ==============================================================================

def test_all_eight_consent_categories_supported():
    """Verifies all 8 required consent categories exist and can be instantiated."""
    expected_categories = [
        "clinical_care",
        "health_screening",
        "wearable_data",
        "ai_processing",
        "research_analytics",
        "notifications",
        "data_sharing",
        "caregiver_family_access",
    ]

    for cat_name in expected_categories:
        cat_enum = ConsentCategory(cat_name)
        assert cat_enum.value == cat_name

    assert len(ConsentCategory) == 8


def test_consent_contains_all_mandatory_fields():
    """Every consent must contain subject, purpose, scope, recipient, created_at, expires_at, revoked_at, version, audit_trail."""
    mgr = ConsentManager()
    exp_time = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()

    consent = mgr.grant(
        subject="citizen-ramesh-patel-01",
        category=ConsentCategory.CLINICAL_CARE,
        purpose="Direct primary healthcare consultation and disease prevention",
        scope=["vitals", "labs", "medications", "screening_surveys"],
        recipient="dr_sharma@sevahealth.ai",
        expires_at=exp_time,
        version="v1.0.0",
        actor_id="citizen-ramesh-patel-01",
        actor_role="CITIZEN",
    )

    # Validate mandatory fields
    assert consent.subject == "citizen-ramesh-patel-01"
    assert consent.category == ConsentCategory.CLINICAL_CARE
    assert "primary healthcare" in consent.purpose
    assert consent.scope == ["vitals", "labs", "medications", "screening_surveys"]
    assert consent.recipient == "dr_sharma@sevahealth.ai"
    assert consent.created_at is not None
    assert consent.expires_at == exp_time
    assert consent.revoked_at is None
    assert consent.version == "v1.0.0"
    assert consent.status == ConsentStatus.ACTIVE
    assert len(consent.audit_trail) >= 1
    assert consent.audit_trail[0].action == "GRANT"


# ==============================================================================
# 2. Lifecycle Operations: Grant, View, Modify, Revoke
# ==============================================================================

def test_consent_lifecycle_operations():
    """Tests complete grant -> view -> modify -> revoke lifecycle with audit trails."""
    mgr = ConsentManager()
    subject = "citizen-test-lifecycle-01"

    # 1. Grant
    consent = mgr.grant(
        subject=subject,
        category=ConsentCategory.RESEARCH_ANALYTICS,
        purpose="De-identified cardiovascular population studies",
        scope=["vitals", "risk_scores"],
        recipient="RESEARCH_REGISTRY",
    )
    assert consent.status == ConsentStatus.ACTIVE
    assert consent.is_valid() is True

    # 2. View
    retrieved = mgr.view(consent.id)
    assert retrieved is not None
    assert retrieved.id == consent.id
    assert retrieved.category == ConsentCategory.RESEARCH_ANALYTICS

    # 3. Modify
    new_scope = ["vitals", "risk_scores", "lifestyle"]
    new_exp = (datetime.now(timezone.utc) + timedelta(days=180)).isoformat()
    modified = mgr.modify(
        consent_id=consent.id,
        new_scope=new_scope,
        new_expires_at=new_exp,
        actor_id=subject,
    )
    assert modified.scope == new_scope
    assert modified.expires_at == new_exp
    assert any(ev.action == "MODIFY" for ev in modified.audit_trail)

    # 4. Revoke
    revoked = mgr.revoke(
        consent_id=consent.id,
        reason="Citizen opted out of research analytics",
        actor_id=subject,
    )
    assert revoked.status == ConsentStatus.REVOKED
    assert revoked.revoked_at is not None
    assert revoked.is_valid() is False
    assert any(ev.action == "REVOKE" for ev in revoked.audit_trail)


# ==============================================================================
# 3. AI Agent Consent Verification
# ==============================================================================

@pytest.mark.asyncio
async def test_ai_agent_verifies_consent_before_processing():
    """AI agent checks active AI_PROCESSING consent; halts and prompts when revoked."""
    subject = "citizen-ramesh-patel-01"
    token_str = get_token_for("citizen@sevahealth.ai")
    actor = decode_access_token(token_str)

    # 1. Ensure active AI_PROCESSING consent is in place
    consent = consent_manager.grant(
        subject=subject,
        category=ConsentCategory.AI_PROCESSING,
        purpose="AI preventive health assessment and trajectory coaching",
        scope=["vitals", "labs", "risk_scores"],
        recipient="AI_AGENT",
    )
    assert consent.status == ConsentStatus.ACTIVE

    # Chat should proceed normally
    resp_normal = await prevention_agent.chat(
        citizen_id=subject,
        user_query="What are my top risk factors?",
        actor=actor,
    )
    assert resp_normal.answer is not None
    assert "CONSENT RESTRICTION" not in resp_normal.answer

    # 2. Revoke AI_PROCESSING consent
    consent_manager.revoke(
        consent_id=consent.id,
        reason="Testing AI consent revocation",
        actor_id=subject,
    )

    # Chat must now block protected data access
    resp_blocked = await prevention_agent.chat(
        citizen_id=subject,
        user_query="What are my top risk factors?",
        actor=actor,
    )
    assert "CONSENT RESTRICTION" in resp_blocked.answer
    assert "Citizen Privacy Center" in resp_blocked.recommended_action

    # 3. Restore consent
    consent_manager.grant(
        subject=subject,
        category=ConsentCategory.AI_PROCESSING,
        purpose="Restored AI processing consent",
        scope=["vitals", "labs"],
        recipient="AI_AGENT",
    )


# ==============================================================================
# 4. Revocable Wearable Access
# ==============================================================================

def test_wearable_access_is_revocable():
    """Wearable access can be revoked by citizen, immediately blocking data sync."""
    token = get_token_for("citizen@sevahealth.ai")
    subject = "citizen-ramesh-patel-01"

    # Grant wearable consent
    w_consent = consent_manager.grant(
        subject=subject,
        category=ConsentCategory.WEARABLE_DATA,
        purpose="Continuous heart rate and sleep tracking",
        scope=["heartrate", "sleep", "steps"],
        recipient="WEARABLE_SYNC_SERVICE",
    )

    # Sync should succeed
    res_ok = client.post(
        f"/api/v1/wearables/sync/{subject}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_ok.status_code == 200
    assert res_ok.json()["status"] == "SUCCESS"

    # Citizen revokes wearable access in Privacy Center
    res_revoke = client.post(
        "/api/v1/privacy/wearables/revoke",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_revoke.status_code == 200
    assert res_revoke.json()["wearable_access_status"] == "REVOKED"

    # Future sync must now be forbidden (HTTP 403)
    res_blocked = client.post(
        f"/api/v1/wearables/sync/{subject}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_blocked.status_code == 403
    assert "REVOKED" in res_blocked.json()["detail"]

    # Re-grant for other tests
    consent_manager.grant(
        subject=subject,
        category=ConsentCategory.WEARABLE_DATA,
        purpose="Restored wearable sync",
        recipient="WEARABLE_SYNC_SERVICE",
    )


# ==============================================================================
# 5. Citizen Privacy Center REST API Endpoints
# ==============================================================================

def test_citizen_privacy_center_api_endpoints():
    """Tests the full suite of Citizen Privacy Center endpoints."""
    token = get_token_for("citizen@sevahealth.ai")

    # 1. Grant consent via API for Caregiver Access
    grant_payload = {
        "category": "caregiver_family_access",
        "purpose": "Allow spouse emergency access to blood pressure logs",
        "scope": ["vitals", "emergency_alerts"],
        "recipient": "spouse_priya@seva.org",
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=90)).isoformat(),
        "version": "v1.0.0",
    }
    res_grant = client.post(
        "/api/v1/privacy/consents",
        headers={"Authorization": f"Bearer {token}"},
        json=grant_payload,
    )
    assert res_grant.status_code == 201
    created_consent = res_grant.json()
    consent_id = created_consent["id"]
    assert created_consent["category"] == "caregiver_family_access"
    assert created_consent["status"] == "ACTIVE"

    # 2. View consent details & audit trail
    res_view = client.get(
        f"/api/v1/privacy/consents/{consent_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_view.status_code == 200
    view_data = res_view.json()
    assert len(view_data["audit_trail"]) >= 1

    # 3. Modify consent scope
    patch_payload = {
        "new_scope": ["vitals", "emergency_alerts", "medications"],
    }
    res_patch = client.patch(
        f"/api/v1/privacy/consents/{consent_id}",
        headers={"Authorization": f"Bearer {token}"},
        json=patch_payload,
    )
    assert res_patch.status_code == 200
    assert "medications" in res_patch.json()["scope"]

    # 4. List consents with filters
    res_list = client.get(
        "/api/v1/privacy/consents?category=caregiver_family_access&status=ACTIVE",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_list.status_code == 200
    assert len(res_list.json()) >= 1

    # 5. Revoke consent
    res_revoke = client.post(
        f"/api/v1/privacy/consents/{consent_id}/revoke",
        headers={"Authorization": f"Bearer {token}"},
        json={"reason": "No longer sharing with this caregiver"},
    )
    assert res_revoke.status_code == 200
    assert res_revoke.json()["status"] == "REVOKED"
    assert res_revoke.json()["revoked_at"] is not None

    # 6. Privacy Center Summary Dashboard
    res_summary = client.get(
        "/api/v1/privacy/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_summary.status_code == 200
    summary = res_summary.json()
    assert "categories" in summary
    assert "caregiver_family_access" in summary["categories"]
    assert "total_consents" in summary
    assert "total_audit_events_logged" in summary

    # 7. Privacy Audit Trail Ledger
    res_audit = client.get(
        "/api/v1/privacy/audit-trail",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_audit.status_code == 200
    audit_events = res_audit.json()
    assert len(audit_events) >= 1
    actions = [ev["action"] for ev in audit_events]
    assert "GRANT" in actions
    assert "REVOKE" in actions
