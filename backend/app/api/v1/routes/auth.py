from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.security import decode_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.role import Role
from app.models.user import User
from app.schemas.auth import ChangePasswordRequest, LoginRequest, TokenResponse
from app.schemas.domain import ProfileUpdate
from app.schemas.user import UserCreate, UserOut
from app.services.audit.service import record_audit
from app.services.auth.service import (
    authenticate_user,
    create_auth_token,
    create_user_session,
    get_current_user,
    is_account_locked,
    list_user_sessions,
    record_failed_login,
    require_roles,
    reset_failed_logins,
    revoke_user_sessions,
)
from app.services.settings.service import get_security_policy

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    try:
        identifier = payload.identifier()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    existing_user = (
        db.query(User)
        .filter((User.email == identifier) | (User.username == identifier))
        .first()
    )

    security_policy = get_security_policy(db)
    if existing_user and is_account_locked(
        existing_user,
        max_attempts=security_policy["max_failed_logins"],
        lockout_minutes=security_policy["lockout_minutes"],
    ):
        record_audit(
            db,
            action="LOGIN_LOCKED",
            entity="User",
            entity_id=identifier,
            details="Account temporarily locked",
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account temporarily locked due to too many failed attempts. Try again later.",
        )

    user = authenticate_user(db, identifier, payload.password)
    if not user:
        if existing_user and existing_user.is_active:
            record_failed_login(db, existing_user)
        record_audit(
            db,
            action="LOGIN_FAILED",
            entity="User",
            entity_id=identifier,
            details="Invalid credentials",
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    assigned_roles = {role.name for role in user.roles}
    if payload.role.value not in assigned_roles:
        record_audit(
            db,
            action="LOGIN_ROLE_REJECTED",
            entity="User",
            entity_id=identifier,
            details="Selected role is not assigned to this account",
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Selected role is not assigned to this account",
        )

    reset_failed_logins(db, user)
    token = create_auth_token(user, role=payload.role.value, db=db)
    token_claims = decode_access_token(token)
    create_user_session(
        db,
        user=user,
        token=str(token_claims.get("jti") or token),
        expires_at=datetime.utcnow() + timedelta(minutes=security_policy["jwt_expiry_minutes"]),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    record_audit(
        db,
        action="LOGIN",
        entity="User",
        entity_id=str(user.id),
        user_id=user.id,
    )
    db.commit()
    return TokenResponse(access_token=token)


@router.post("/logout")
def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    revoke_user_sessions(db, current_user.id)
    record_audit(db, action="LOGOUT", entity="User", entity_id=str(current_user.id), user_id=current_user.id)
    db.commit()
    return {"message": "Signed out"}


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")

    security_policy = get_security_policy(db)
    min_password_length = security_policy["min_password_length"]
    if len(payload.new_password) < min_password_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"New password must be at least {min_password_length} characters long.",
        )

    current_user.password_hash = hash_password(payload.new_password)
    revoke_user_sessions(db, current_user.id)
    record_audit(
        db,
        action="PASSWORD_CHANGED",
        entity="User",
        entity_id=str(current_user.id),
        user_id=current_user.id,
        details="Password changed; all sessions revoked",
    )
    db.commit()
    return {"message": "Password updated successfully"}


@router.get("/sessions")
def list_my_sessions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    sessions = list_user_sessions(db, current_user.id)
    return [
        {
            "id": item.id,
            "created_at": item.created_at.isoformat(),
            "expires_at": item.expires_at.isoformat(),
            "ip_address": item.ip_address,
            "user_agent": item.user_agent,
            "revoked": item.revoked,
        }
        for item in sessions
    ]


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "email": current_user.email,
        "is_active": current_user.is_active,
        "roles": [role.name for role in current_user.roles],
    }


@router.put("/me")
def update_profile(
    payload: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.full_name:
        current_user.full_name = payload.full_name
    if payload.password:
        current_user.password_hash = hash_password(payload.password)
    record_audit(db, action="PROFILE_UPDATE", entity="User", entity_id=str(current_user.id), user_id=current_user.id)
    db.commit()
    return {"message": "Profile updated"}


@router.post("/register", response_model=UserOut)
def register_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN")),
):
    existing = db.query(User).filter((User.email == payload.email) | (User.username == (payload.username or payload.email))).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    new_user = User(
        username=payload.username or payload.email.split("@")[0],
        full_name=payload.full_name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        is_active=payload.is_active,
    )
    role = db.query(Role).filter(Role.name == payload.role.value).first()
    if role is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="User role is not configured")
    new_user.roles.append(role)
    db.add(new_user)
    db.flush()
    record_audit(db, action="USER_CREATED", entity="User", entity_id=str(new_user.id), user_id=current_user.id)
    db.commit()
    db.refresh(new_user)
    return new_user
