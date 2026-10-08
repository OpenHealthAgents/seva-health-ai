import pytest
from packages.types.enums import UserRole
from packages.auth.jwt import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_access_token,
)


def test_password_hashing():
    raw = "secure-clinical-password"
    hashed = get_password_hash(raw)
    assert hashed != raw
    assert verify_password(raw, hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_jwt_lifecycle():
    token = create_access_token(
        subject="user-123",
        tenant_id="karnataka_health",
        role=UserRole.CLINICIAN,
        scopes=["clinical:read", "clinical:write"],
    )
    assert isinstance(token, str)

    payload = decode_access_token(token)
    assert payload.sub == "user-123"
    assert payload.tenant_id == "karnataka_health"
    assert payload.role == UserRole.CLINICIAN
    assert "clinical:read" in payload.scopes
