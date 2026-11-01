"""Tests for system settings endpoints and security policy enforcement."""
from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "backend"))

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.role import Role
from app.models.system_config import SystemConfig
from app.models.user import User


engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


def _create_user(username, email, password, role_name):
    db = TestingSessionLocal()
    role = db.query(Role).filter(Role.name == role_name).first()
    if not role:
        role = Role(name=role_name, description=f"{role_name} role")
        db.add(role)
        db.flush()
    user = User(
        username=username,
        full_name=f"{role_name} User",
        email=email,
        password_hash=hash_password(password),
        is_active=True,
    )
    user.roles.append(role)
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


def _login(client, email, password, role):
    response = client.post("/api/auth/login", json={"email": email, "password": password, "role": role})
    return response


def _admin_token(client):
    _create_user("admin_settings", "admin_settings@test.local", "AdminPass123!", "ADMIN")
    response = _login(client, "admin_settings@test.local", "AdminPass123!", "ADMIN")
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_settings_requires_admin(client):
    _create_user("officer_settings", "officer_settings@test.local", "OfficerPass123!", "OFFICER")
    response = _login(client, "officer_settings@test.local", "OfficerPass123!", "OFFICER")
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/settings", headers=headers).status_code == 403
    assert client.get("/api/settings").status_code == 401


def test_settings_list_and_update_persist(client):
    headers = _admin_token(client)
    response = client.get("/api/settings", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

    update = client.put(
        "/api/settings/general.system_name",
        json={"value": "LandGuard AI Verification"},
        headers=headers,
    )
    assert update.status_code == 200
    assert update.json()["value"] == "LandGuard AI Verification"

    fetched = client.get("/api/settings", headers=headers)
    assert fetched.status_code == 200
    names = [item["key"] for item in fetched.json()]
    assert "general.system_name" in names


def test_settings_update_invalid_value_rejected(client):
    headers = _admin_token(client)
    response = client.put(
        "/api/settings/general.review_threshold",
        json={"value": "critical"},
        headers=headers,
    )
    assert response.status_code == 400


def test_file_storage_policy_endpoint(client):
    headers = _admin_token(client)
    response = client.get("/api/settings/file-storage", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data.get("allowed_file_types"), list)
    assert float(data.get("max_file_size_mb", 0)) > 0


def test_database_health_endpoint(client):
    headers = _admin_token(client)
    response = client.get("/api/settings/database/health", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_change_password_enforces_configured_min_length(client):
    headers = _admin_token(client)
    update = client.put(
        "/api/settings/security.min_password_length",
        json={"value": "12"},
        headers=headers,
    )
    assert update.status_code == 200

    user = _create_user("pw_policy_user", "pw_policy@test.local", "OfficerPass123!", "OFFICER")
    login_response = _login(client, "pw_policy@test.local", "OfficerPass123!", "OFFICER")
    token = login_response.json()["access_token"]
    change_response = client.post(
        "/api/auth/change-password",
        json={"current_password": "OfficerPass123!", "new_password": "NewPass123!"},
        headers={"Authorization": f"Bearer {token}"},
    )
    # New password "NewPass123!" is 10 characters; configured policy requires 12.
    assert change_response.status_code == 400
    assert "at least 12" in change_response.json()["detail"]
