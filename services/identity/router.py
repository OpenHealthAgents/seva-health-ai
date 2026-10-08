from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, status, Request
from pydantic import BaseModel, EmailStr
import uuid

from packages.types.enums import UserRole, Gender, AuditAction
from packages.auth.jwt import (
    create_access_token,
    create_refresh_token,
    verify_password,
    get_password_hash,
    validate_password_strength,
    get_current_user_token,
    TokenPayload,
    require_roles,
)
from packages.auth.access_control import HealthcareAuthorizationEngine
from packages.observability.audit import audit_logger
from services.store import store, UserRecord, CitizenRecord, SessionRecord, ConsentDirective

router = APIRouter(prefix="/auth", tags=["Identity & Access Management"])
citizens_router = APIRouter(prefix="/citizens", tags=["Citizen Registry"])


# Request / Response Models
class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    role: UserRole
    name: str
    user_id: str
    tenant_id: str


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str
    role: UserRole = UserRole.CITIZEN
    tenant_id: str = "karnataka_state_health"
    phone: Optional[str] = None
    assigned_jurisdiction: Optional[str] = None
    assigned_patients: Optional[List[str]] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class PasswordRecoveryRequest(BaseModel):
    email: str


class PasswordResetRequest(BaseModel):
    email: str
    recovery_token: str
    new_password: str


class ConsentGrantRequest(BaseModel):
    citizen_id: str
    grantee_id: str
    grantee_role: UserRole
    purpose: str = "CARE_DELIVERY"
    duration_days: int = 30


class ConsentRevokeRequest(BaseModel):
    citizen_id: str
    consent_id: str


class CitizenCreateRequest(BaseModel):
    first_name: str
    last_name: str
    birth_date: str                   # YYYY-MM-DD
    gender: Gender
    phone: str
    state: str = "Karnataka"
    district: str = "Mysuru"
    sub_district: str = "Nanjangud"
    village_or_ward: str = "Ward 4"
    abha_id: Optional[str] = None
    primary_language: str = "en"


# Auth Endpoints
@router.post("/token", response_model=TokenResponse)
@router.post("/login", response_model=TokenResponse)
async def login_for_access_token(form_data: LoginRequest, request: Request):
    user = store.get_user(form_data.email)
    if not user or not verify_password(form_data.password, user.hashed_password):
        audit_logger.record(
            tenant_id="default_org",
            actor_id=form_data.email,
            actor_role=UserRole.CITIZEN,
            action=AuditAction.ACCESS_DENIED,
            resource_type="User",
            resource_id=form_data.email,
            details={"reason": "Invalid credentials"}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_jti = str(uuid.uuid4())
    refresh_jti = str(uuid.uuid4())

    access_token = create_access_token(
        subject=user.id,
        tenant_id=user.tenant_id,
        role=user.role,
        scopes=["*"],
        jti=access_jti,
    )
    refresh_token = create_refresh_token(
        subject=user.id,
        tenant_id=user.tenant_id,
        role=user.role,
        jti=refresh_jti,
    )

    # Record active session
    session_id = str(uuid.uuid4())
    client_ip = request.client.host if request.client else "127.0.0.1"
    store.record_session(SessionRecord(
        id=session_id,
        user_id=user.id,
        tenant_id=user.tenant_id,
        token_jti=access_jti,
        ip_address=client_ip,
        user_agent=request.headers.get("user-agent", "unknown"),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=60),
    ))

    audit_logger.record(
        tenant_id=user.tenant_id,
        actor_id=user.id,
        actor_role=user.role,
        action=AuditAction.LOGIN_SUCCESS,
        resource_type="User",
        resource_id=user.id,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        role=user.role,
        name=user.full_name,
        user_id=user.id,
        tenant_id=user.tenant_id,
    )


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(payload: RegisterRequest):
    # 1. Validate password strength
    valid, reason = validate_password_strength(payload.password)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insecure password: {reason}",
        )

    # 2. Check duplicate email
    if store.get_user(payload.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email is already registered.",
        )

    # 3. Create user record
    user_id = str(uuid.uuid4())
    new_user = UserRecord(
        id=user_id,
        tenant_id=payload.tenant_id,
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        role=payload.role,
        full_name=payload.full_name,
        phone=payload.phone,
        assigned_jurisdiction=payload.assigned_jurisdiction,
        assigned_patients=payload.assigned_patients or [],
    )
    store.add_user(new_user)

    # 4. If Citizen, auto-create linked Citizen record
    citizen_id = None
    if payload.role == UserRole.CITIZEN:
        citizen_id = f"citizen-{user_id[:8]}"
        names = payload.full_name.split(" ", 1)
        first_name = names[0]
        last_name = names[1] if len(names) > 1 else "Citizen"
        new_citizen = CitizenRecord(
            id=citizen_id,
            tenant_id=payload.tenant_id,
            user_id=user_id,
            abha_id=None,
            first_name=first_name,
            last_name=last_name,
            birth_date="1990-01-01",
            gender=Gender.OTHER,
            phone=payload.phone or "+91 00000 00000",
            state="Karnataka",
            district="Mysuru",
            sub_district="Mysuru Urban",
            village_or_ward=payload.assigned_jurisdiction or "Ward 1",
        )
        store.add_citizen(new_citizen)

    audit_logger.record(
        tenant_id=payload.tenant_id,
        actor_id=user_id,
        actor_role=payload.role,
        action=AuditAction.USER_REGISTERED,
        resource_type="User",
        resource_id=user_id,
    )

    return {
        "status": "success",
        "user_id": user_id,
        "email": payload.email,
        "full_name": payload.full_name,
        "role": payload.role.value,
        "tenant_id": payload.tenant_id,
        "citizen_id": citizen_id,
    }


@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(payload: RefreshTokenRequest, request: Request):
    from jose import jwt, JWTError
    from packages.config.settings import settings

    try:
        decoded = jwt.decode(payload.refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if decoded.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type for refresh")

        old_jti = decoded.get("jti")
        if old_jti and store.is_token_revoked(old_jti):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token has been revoked")

        user_id = decoded.get("sub")
        user = store.get_user(user_id)
        if not user or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account is inactive or not found")

        # Invalidate old refresh token (token rotation)
        if old_jti:
            store.revoke_token(old_jti)

        new_access_jti = str(uuid.uuid4())
        new_refresh_jti = str(uuid.uuid4())

        new_access_token = create_access_token(
            subject=user.id,
            tenant_id=user.tenant_id,
            role=user.role,
            scopes=["*"],
            jti=new_access_jti,
        )
        new_refresh_token = create_refresh_token(
            subject=user.id,
            tenant_id=user.tenant_id,
            role=user.role,
            jti=new_refresh_jti,
        )

        client_ip = request.client.host if request.client else "127.0.0.1"
        store.record_session(SessionRecord(
            id=str(uuid.uuid4()),
            user_id=user.id,
            tenant_id=user.tenant_id,
            token_jti=new_access_jti,
            ip_address=client_ip,
            user_agent=request.headers.get("user-agent", "unknown"),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=60),
        ))

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            role=user.role,
            name=user.full_name,
            user_id=user.id,
            tenant_id=user.tenant_id,
        )
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate refresh token")


@router.post("/logout")
async def logout_user(current_user: TokenPayload = Depends(get_current_user_token)):
    if current_user.jti:
        store.revoke_token(current_user.jti)

    audit_logger.record(
        tenant_id=current_user.tenant_id,
        actor_id=current_user.sub,
        actor_role=current_user.role,
        action=AuditAction.LOGOUT,
        resource_type="Session",
        resource_id=current_user.jti or current_user.sub,
    )
    return {"status": "success", "message": "Successfully logged out and token revoked"}


@router.get("/sessions")
async def list_active_sessions(current_user: TokenPayload = Depends(get_current_user_token)):
    sessions = store.list_user_sessions(current_user.sub)
    return [
        {
            "id": s.id,
            "user_id": s.user_id,
            "tenant_id": s.tenant_id,
            "token_jti": s.token_jti,
            "ip_address": s.ip_address,
            "created_at": s.created_at.isoformat(),
            "expires_at": s.expires_at.isoformat(),
            "is_revoked": s.is_revoked,
        }
        for s in sessions
    ]


# Account Recovery Flow
@router.post("/recover/request")
async def request_password_recovery(payload: PasswordRecoveryRequest):
    user = store.get_user(payload.email)
    if not user:
        # Prevent user enumeration in security-critical environments
        return {"status": "recovery_initiated", "message": "If an account exists with this email, recovery instructions have been initiated."}

    token = uuid.uuid4().hex
    user.recovery_token = token
    user.recovery_token_expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

    return {
        "status": "recovery_initiated",
        "message": "Recovery instructions generated. Valid for 15 minutes.",
        "recovery_token": token,  # Exposed for API testing & offline recovery simulation
    }


@router.post("/recover/reset")
async def reset_password(payload: PasswordResetRequest):
    user = store.get_user(payload.email)
    if not user or not user.recovery_token or user.recovery_token != payload.recovery_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired recovery token",
        )

    if user.recovery_token_expires_at and datetime.now(timezone.utc) > user.recovery_token_expires_at:
        user.recovery_token = None
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recovery token has expired. Please request a new one.",
        )

    valid, reason = validate_password_strength(payload.new_password)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insecure password: {reason}",
        )

    user.hashed_password = get_password_hash(payload.new_password)
    user.recovery_token = None
    user.recovery_token_expires_at = None

    # Revoke all active sessions for this user on password reset
    for s in store.list_user_sessions(user.id):
        store.revoke_token(s.token_jti)

    audit_logger.record(
        tenant_id=user.tenant_id,
        actor_id=user.id,
        actor_role=user.role,
        action=AuditAction.PASSWORD_RESET,
        resource_type="User",
        resource_id=user.id,
    )

    return {"status": "success", "message": "Password successfully reset. Active sessions revoked."}


# Consent Directives (ABDM / DISHA Alignment)
@router.post("/consent/grant", status_code=status.HTTP_201_CREATED)
async def grant_consent(
    payload: ConsentGrantRequest,
    current_user: TokenPayload = Depends(get_current_user_token)
):
    citizen = store.get_citizen(payload.citizen_id)
    if not citizen:
        raise HTTPException(status_code=404, detail="Citizen not found")

    # Only citizen themselves or System Admin can grant consent
    if current_user.role != UserRole.SYSTEM_ADMIN and (citizen.user_id != current_user.sub and citizen.id != current_user.sub):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the citizen or an authorized guardian can grant medical record consent."
        )

    directive = ConsentDirective(
        id=str(uuid.uuid4()),
        citizen_id=payload.citizen_id,
        grantee_id=payload.grantee_id,
        grantee_role=payload.grantee_role,
        purpose=payload.purpose,
        expires_at=datetime.now(timezone.utc) + timedelta(days=payload.duration_days),
    )
    store.add_consent(directive)

    audit_logger.record(
        tenant_id=citizen.tenant_id,
        actor_id=current_user.sub,
        actor_role=current_user.role,
        action=AuditAction.CONSENT_GRANTED,
        resource_type="ConsentDirective",
        resource_id=directive.id,
        details={
            "citizen_id": payload.citizen_id,
            "grantee_id": payload.grantee_id,
            "purpose": payload.purpose,
            "duration_days": payload.duration_days,
        }
    )

    return {
        "status": "granted",
        "consent_id": directive.id,
        "citizen_id": directive.citizen_id,
        "grantee_id": directive.grantee_id,
        "purpose": directive.purpose,
        "expires_at": directive.expires_at.isoformat() if directive.expires_at else None,
    }


@router.post("/consent/revoke")
async def revoke_consent(
    payload: ConsentRevokeRequest,
    current_user: TokenPayload = Depends(get_current_user_token)
):
    citizen = store.get_citizen(payload.citizen_id)
    if not citizen:
        raise HTTPException(status_code=404, detail="Citizen not found")

    if current_user.role != UserRole.SYSTEM_ADMIN and (citizen.user_id != current_user.sub and citizen.id != current_user.sub):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the citizen or an authorized guardian can revoke consent."
        )

    success = store.revoke_consent(payload.citizen_id, payload.consent_id)
    if not success:
        raise HTTPException(status_code=404, detail="Consent directive not found")

    audit_logger.record(
        tenant_id=citizen.tenant_id,
        actor_id=current_user.sub,
        actor_role=current_user.role,
        action=AuditAction.CONSENT_REVOKED,
        resource_type="ConsentDirective",
        resource_id=payload.consent_id,
        details={"citizen_id": payload.citizen_id}
    )

    return {"status": "revoked", "consent_id": payload.consent_id}


@router.get("/consent/{citizen_id}")
async def list_citizen_consents(
    citizen_id: str,
    current_user: TokenPayload = Depends(get_current_user_token)
):
    citizen = store.get_citizen(citizen_id)
    if not citizen:
        raise HTTPException(status_code=404, detail="Citizen not found")

    # Authorize: citizen themselves, admin, or assigned clinician
    HealthcareAuthorizationEngine.enforce_citizen_access(current_user, citizen)

    directives = store.get_citizen_consents(citizen_id)
    return [
        {
            "id": d.id,
            "citizen_id": d.citizen_id,
            "grantee_id": d.grantee_id,
            "grantee_role": d.grantee_role.value,
            "purpose": d.purpose,
            "status": d.status,
            "granted_at": d.granted_at.isoformat(),
            "expires_at": d.expires_at.isoformat() if d.expires_at else None,
            "is_valid": d.is_valid(),
        }
        for d in directives
    ]


@router.get("/me")
async def get_my_profile(current_user: TokenPayload = Depends(get_current_user_token)):
    user_rec = store.get_user(current_user.sub)
    return {
        "user_id": current_user.sub,
        "tenant_id": current_user.tenant_id,
        "role": current_user.role,
        "name": user_rec.full_name if user_rec else "Evaluator User",
        "email": user_rec.email if user_rec else "evaluator@sevahealth.ai",
        "assigned_jurisdiction": user_rec.assigned_jurisdiction if user_rec else None,
        "assigned_patients": user_rec.assigned_patients if user_rec else [],
    }


# Citizen Registry Endpoints with Resource-Level Least-Privilege
@citizens_router.get("/")
async def list_citizens(current_user: TokenPayload = Depends(get_current_user_token)):
    # 1. Public Health Admin: blocked from raw identifiable citizen lists
    if current_user.role == UserRole.PUBLIC_HEALTH_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Public Health Administrators are restricted to aggregated population intelligence and cannot view identifiable patient health records."
        )

    all_records = store.list_citizens()

    # 2. Citizen: only view own record
    if current_user.role == UserRole.CITIZEN:
        records = [c for c in all_records if c.user_id == current_user.sub or c.id == current_user.sub]
        return [c.to_dict() for c in records]

    # 3. Clinician / Health Worker: filter to records permitted by HealthcareAuthorizationEngine
    permitted = []
    for c in all_records:
        allowed, _ = HealthcareAuthorizationEngine.can_access_citizen_record(current_user, c)
        if allowed:
            permitted.append(c)

    return [c.to_dict() for c in permitted]


@citizens_router.get("/{citizen_id}")
async def get_citizen_by_id(citizen_id: str, current_user: TokenPayload = Depends(get_current_user_token)):
    citizen = store.get_citizen(citizen_id)
    if not citizen:
        raise HTTPException(status_code=404, detail="Citizen not found")

    # Enforce resource-level authorization
    HealthcareAuthorizationEngine.enforce_citizen_access(current_user, citizen)

    return citizen.to_dict()


@citizens_router.post("/", status_code=201)
async def register_citizen(
    payload: CitizenCreateRequest,
    current_user: TokenPayload = Depends(get_current_user_token)
):
    c_id = str(uuid.uuid4())
    citizen = CitizenRecord(
        id=c_id,
        tenant_id=current_user.tenant_id,
        user_id=current_user.sub,
        abha_id=payload.abha_id,
        first_name=payload.first_name,
        last_name=payload.last_name,
        birth_date=payload.birth_date,
        gender=payload.gender,
        phone=payload.phone,
        state=payload.state,
        district=payload.district,
        sub_district=payload.sub_district,
        village_or_ward=payload.village_or_ward,
        primary_language=payload.primary_language,
    )
    store.add_citizen(citizen)

    audit_logger.record(
        tenant_id=current_user.tenant_id,
        actor_id=current_user.sub,
        actor_role=current_user.role,
        action=AuditAction.USER_REGISTERED,
        resource_type="Citizen",
        resource_id=c_id,
    )
    return citizen.to_dict()
