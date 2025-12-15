import pytest
from fastapi.testclient import TestClient


def test_signup_creates_user(client: TestClient):
    payload = {
        "username": "alice",
        "password": "secret123",
        "email": "alice@example.com",
        "name": "Alice",
        "apellidos": "Doe",
        "telefono": "3001112222",
        "born_date": "1990-01-01",
        "cedula": "12345678",
        "tipo_documento": "CC",
    }

    res = client.post("/auth/signup", json=payload)
    assert res.status_code == 200
    body = res.json()
    assert body["message"] == "Usuario creado exitosamente"
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_signup_duplicate_user_fails(client: TestClient):
    payload = {
        "username": "bob",
        "password": "secret123",
        "email": "bob@example.com",
        "name": "Bob",
        "apellidos": "Smith",
    }
    ok = client.post("/auth/signup", json=payload)
    assert ok.status_code == 200

    dup = client.post("/auth/signup", json=payload)
    assert dup.status_code == 400
    assert dup.json()["detail"] == "El usuario ya existe"


def test_login_success_returns_token_and_role(client: TestClient):
    client.post("/auth/signup", json={
        "username": "charlie",
        "password": "secret123",
        "email": "charlie@example.com",
        "name": "Charlie",
        "apellidos": "Brown",
    })

    res = client.post("/auth/login", json={
        "username": "charlie",
        "password": "secret123",
    })
    assert res.status_code == 200
    body = res.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert body["username"] == "charlie"
    assert body["role"] == "Jugador"


def test_login_missing_data_400(client: TestClient):
    res = client.post("/auth/login", json={"username": "no-pass"})
    assert res.status_code == 400
    assert res.json()["detail"] == "Faltan datos"


def test_login_wrong_credentials_404(client: TestClient):
    client.post("/auth/signup", json={
        "username": "diana",
        "password": "rightpass",
        "email": "diana@example.com",
        "name": "Diana",
        "apellidos": "Prince",
    })

    res = client.post("/auth/login", json={
        "username": "diana",
        "password": "wrongpass",
    })
    assert res.status_code == 404


def test_me_requires_valid_token(client: TestClient, auth_headers):
    res = client.get("/auth/me", headers=auth_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["username"] == "testuser"
    assert body["role"] in ("Jugador", "admin")


def test_me_with_invalid_token_401(client: TestClient):
    res = client.get("/auth/me", headers={"Authorization": "Bearer invalid"})
    assert res.status_code == 401
    assert res.json()["detail"] == "Token Invalido o expirado"


def test_create_admin_endpoint_creates_admin(client: TestClient):
    res = client.get("/auth/create-admin")
    assert res.status_code == 200
    body = res.json()
    assert body["message"] == "Usuario administrador creado exitosamente"
    assert body["username"] == "admin"
    assert body["password"] == "admin"
    assert body["role"] == "admin"

    # Calling again should fail with duplicate
    res2 = client.get("/auth/create-admin")
    assert res2.status_code == 400
    assert res2.json()["detail"] == "El usuario admin ya existe"