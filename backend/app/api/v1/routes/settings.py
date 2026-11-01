from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.models.system_config import SystemConfig
from app.schemas.settings import DatabaseHealthOut, FileStoragePolicyOut, SettingOut, SettingUpdate
from app.services.audit.service import record_audit
from app.services.auth.service import require_roles
from app.services.settings.service import (
    check_database_connection,
    get_file_storage_policy,
    get_setting_value,
    list_settings,
    save_setting,
    validate_setting,
)
from app.db.session import get_db

router = APIRouter(prefix="/settings", tags=["System Settings"])


def _setting_out(record: SystemConfig) -> dict:
    return {
        "id": record.id,
        "key": record.key,
        "value": record.value,
        "description": record.description,
        "updated_by": record.updated_by,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
    }


@router.get("", response_model=list[SettingOut])
def list_all_settings(
    db: Session = Depends(get_db),
    _current_user=Depends(require_roles("ADMIN")),
):
    """List all persisted system settings (Admin only)."""
    return [_setting_out(record) for record in list_settings(db)]


@router.put("/{key}", response_model=SettingOut)
def update_setting(
    key: str,
    payload: SettingUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN")),
):
    """Create or update a validated system setting (Admin only)."""
    try:
        value = validate_setting(key, payload.value)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    record = save_setting(db, key=key, value=value, updated_by=current_user.id)
    record_audit(
        db,
        action="SETTINGS_UPDATED",
        entity="SystemConfig",
        entity_id=key,
        user_id=current_user.id,
        details=f"Updated system setting {key}",
        metadata={"key": key, "value": value},
    )
    return _setting_out(record)


@router.get("/file-storage", response_model=FileStoragePolicyOut)
def get_file_storage_policy_endpoint(
    db: Session = Depends(get_db),
    _current_user=Depends(require_roles("ADMIN")),
):
    """Return the effective file storage policy (Admin only)."""
    policy = get_file_storage_policy(db)
    return FileStoragePolicyOut(
        allowed_file_types=list(policy["allowed_file_types"]),
        max_file_size_mb=float(policy["max_file_size_mb"]),
        storage_provider=str(policy.get("storage_provider") or "local"),
    )


@router.get("/database/health", response_model=DatabaseHealthOut)
def database_health(
    db: Session = Depends(get_db),
    _current_user=Depends(require_roles("ADMIN")),
):
    """Return database connectivity health status (Admin only, non-sensitive)."""
    healthy = check_database_connection(db)
    return DatabaseHealthOut(status="ok" if healthy else "error")
