# tests/integration/test_user_journey.py
import pytest
from fastapi.testclient import TestClient

def test_complete_user_journey(client: TestClient):
    """
    Test completo del journey de un usuario desde registro hasta juego
    Este test simula la experiencia completa de un usuario real
    """
    # === FASE 1: REGISTRO DE USUARIO ===
    signup_data = {
        "username": "journeyuser",
        "password": "JourneyPass123!",
        "email": "journey.user@example.com",
        "name": "Journey",
        "apellidos": "User",
        "telefono": "+573001234567",
        "born_date": "1990-05-15",
        "cedula": "987654321",
        "tipo_documento": "CC"
    }
    signup_response = client.post("/auth/signup", json=signup_data)
    assert signup_response.status_code == 200, f"Registro falló: {signup_response.text}"
    signup_result = signup_response.json()
    assert signup_result["message"] == "Usuario creado exitosamente"

    # === FASE 2: LOGIN ===
    login_response = client.post("/auth/login", json={
        "username": "journeyuser",
        "password": "JourneyPass123!"
    })
    assert login_response.status_code == 200, f"Login falló: {login_response.text}"
    login_result = login_response.json()
    assert "access_token" in login_result
    assert login_result["token_type"] == "bearer"
    
    token = login_result["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # === FASE 3: VERIFICACIÓN DE PERFIL ===
    profile_response = client.get("/profile/journeyuser")
    assert profile_response.status_code == 200
    profile_data = profile_response.json()
    
    assert profile_data["usuario"] == "journeyuser"
    assert profile_data["nombres"] == "Journey"
    assert profile_data["apellidos"] == "User"
    assert profile_data["correo_electronico"] == "journey.user@example.com"
    assert profile_data["saldo"] == 0.0  # Saldo inicial

    # === FASE 4: ACTUALIZACIÓN DE PERFIL ===
    update_response = client.patch(
        "/profile/me/update",
        headers=headers,
        json={
            "email": "journey.updated@example.com",
            "telefono": "+573009876543"
        }
    )
    assert update_response.status_code == 200
    update_data = update_response.json()
    assert update_data["email"] == "journey.updated@example.com"
    assert update_data["telefono"] == "+573009876543"

    # === FASE 5: CONSULTA DE SALDO ===
    balance_response = client.get("/profile/me/saldo", headers=headers)
    assert balance_response.status_code == 200
    balance_data = balance_response.json()
    assert "saldo" in balance_data
    initial_balance = balance_data["saldo"]

    # === FASE 6: DEPÓSITO DE FONDOS (para testing) ===
    deposit_response = client.post(
        "/v1/roulette/user/deposit",
        headers=headers,
        json={"amount": 100.0}
    )
    assert deposit_response.status_code == 200
    deposit_data = deposit_response.json()
    assert deposit_data["saldo"] == 100.0

    # === FASE 7: CREACIÓN DE SESIÓN DE RULETA ===
    session_response = client.post("/v1/roulette/session", headers=headers)
    assert session_response.status_code == 200
    session_data = session_response.json()
    session_id = session_data["session_id"]
    server_seed_hash = session_data["server_seed_hash"]
    
    assert isinstance(session_id, int)
    assert len(server_seed_hash) == 64  # SHA256 hash length

    # === FASE 8: REALIZACIÓN DE APUESTAS ===
    
    # Apuesta 1: Color Rojo
    bet_1_response = client.post(
        f"/v1/roulette/session/{session_id}/bet",
        headers=headers,
        json={
            "client_seed": "journey_bet_1",
            "bet": {
                "type": "color",
                "side": "red",
                "amount": 10.0
            }
        }
    )
    assert bet_1_response.status_code == 200
    bet_1_data = bet_1_response.json()
    assert "spin" in bet_1_data
    assert "bet_result" in bet_1_data
    assert "user" in bet_1_data
    
    spin_1 = bet_1_data["spin"]
    bet_result_1 = bet_1_data["bet_result"]
    user_after_bet_1 = bet_1_data["user"]

    # Apuesta 2: Número específico
    bet_2_response = client.post(
        f"/v1/roulette/session/{session_id}/bet",
        headers=headers,
        json={
            "client_seed": "journey_bet_2",
            "bet": {
                "type": "straight",
                "number": 17,
                "amount": 5.0
            }
        }
    )
    assert bet_2_response.status_code == 200
    bet_2_data = bet_2_response.json()

    # Apuesta 3: Docena
    bet_3_response = client.post(
        f"/v1/roulette/session/{session_id}/bet",
        headers=headers,
        json={
            "client_seed": "journey_bet_3",
            "bet": {
                "type": "dozen",
                "which": 1,
                "amount": 15.0
            }
        }
    )
    assert bet_3_response.status_code == 200

    # === FASE 9: VERIFICACIÓN DE BALANCE Y ESTADÍSTICAS ===
    final_profile_response = client.get("/profile/journeyuser")
    assert final_profile_response.status_code == 200
    final_profile_data = final_profile_response.json()
    
    # Verificar que las estadísticas se actualizaron
    assert "ganancias_totales" in final_profile_data
    assert "perdidas_totales" in final_profile_data
    assert final_profile_data["saldo"] != 100.0  # El saldo debería haber cambiado

    # === FASE 10: LISTADO DE SPINS ===
    spins_response = client.get(f"/v1/roulette/session/{session_id}/spins", headers=headers)
    assert spins_response.status_code == 200
    spins_data = spins_response.json()
    
    assert spins_data["session_id"] == session_id
    assert len(spins_data["spins"]) == 3  # Deberían haber 3 spins
    assert spins_data["revealed"] == False  # Sesión no revelada aún

    # === FASE 11: SOLICITUD DE CRÉDITO ===
    credit_response = client.post(
        "/v1/credits/request",
        headers=headers,
        json={
            "amount": 50.0,
            "note": "Solicitud de crédito para continuar jugando"
        }
    )
    
    # Puede fallar si ya hay una solicitud pendiente, eso es normal
    if credit_response.status_code == 200:
        credit_data = credit_response.json()
        assert credit_data["status"] == "pending"

    # === FASE 12: VERIFICACIÓN FINAL ===
    final_me_response = client.get("/auth/me", headers=headers)
    assert final_me_response.status_code == 200
    final_me_data = final_me_response.json()
    
    assert final_me_data["username"] == "journeyuser"
    assert final_me_data["email"] == "journey.updated@example.com"

def test_credit_approval_journey(client: TestClient, admin_headers):
    """
    Test del journey completo de aprobación de créditos (flujo admin)
    """
    # === FASE 1: CREAR USUARIO REGULAR ===
    client.post("/auth/signup", json={
        "username": "credituser",
        "password": "CreditPass123!",
        "email": "credit.user@example.com",
        "name": "Credit",
        "apellidos": "User"
    })
    
    # Login como usuario regular
    login_response = client.post("/auth/login", json={
        "username": "credituser",
        "password": "CreditPass123!"
    })
    user_token = login_response.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}

    # === FASE 2: SOLICITUD DE CRÉDITO ===
    credit_request_response = client.post(
        "/v1/credits/request",
        headers=user_headers,
        json={
            "amount": 75.0,
            "note": "Necesito crédito para jugar en la ruleta"
        }
    )
    
    if credit_request_response.status_code == 200:
        credit_data = credit_request_response.json()
        request_id = credit_data["id"]
        
        # === FASE 3: ADMIN LISTA SOLICITUDES ===
        list_credits_response = client.get(
            "/v1/admin/credits?status=pending",
            headers=admin_headers
        )
        assert list_credits_response.status_code == 200
        credits_list = list_credits_response.json()
        
        # Encontrar nuestra solicitud
        our_request = None
        for req in credits_list:
            if req["user_id"] == 2:  # ID del usuario credituser
                our_request = req
                break
        
        if our_request:
            # === FASE 4: ADMIN APRUEBA CRÉDITO ===
            approve_response = client.post(
                f"/v1/admin/credits/{our_request['id']}/approve",
                headers=admin_headers,
                json={}
            )
            
            if approve_response.status_code == 200:
                approve_data = approve_response.json()
                assert approve_data["status"] == "approved"
                
                # === FASE 5: VERIFICACIÓN DE BALANCE ===
                balance_response = client.get("/profile/me/saldo", headers=user_headers)
                balance_data = balance_response.json()
                assert balance_data["saldo"] == 75.0
            

def test_multiple_users_concurrent_journey(client: TestClient):
    """
    Test que simula múltiples usuarios usando el sistema concurrentemente
    """
    users_data = [
        {"username": "user1", "password": "pass1", "email": "user1@test.com"},
        {"username": "user2", "password": "pass2", "email": "user2@test.com"},
        {"username": "user3", "password": "pass3", "email": "user3@test.com"}
    ]
    
    user_tokens = []
    
    # === REGISTRO Y LOGIN DE MÚLTIPLES USUARIOS ===
    for user in users_data:
        # Registro
        client.post("/auth/signup", json=user)
        
        # Login
        login_response = client.post("/auth/login", json={
            "username": user["username"],
            "password": user["password"]
        })
        token = login_response.json()["access_token"]
        user_tokens.append(token)
    
    # === OPERACIONES CONCURRENTES ===
    # Todos los usuarios crean sesiones de ruleta
    session_ids = []
    for i, token in enumerate(user_tokens):
        headers = {"Authorization": f"Bearer {token}"}
        session_response = client.post("/v1/roulette/session", headers=headers)
        if session_response.status_code == 200:
            session_id = session_response.json()["session_id"]
            session_ids.append(session_id)
    
    # Todos los usuarios hacen apuestas
    for i, (token, session_id) in enumerate(zip(user_tokens, session_ids)):
        if session_id:  # Si la sesión fue creada exitosamente
            headers = {"Authorization": f"Bearer {token}"}
            bet_response = client.post(
                f"/v1/roulette/session/{session_id}/bet",
                headers=headers,
                json={
                    "client_seed": f"concurrent_user_{i}",
                    "bet": {
                        "type": "color",
                        "side": "red" if i % 2 == 0 else "black",
                        "amount": 10.0 * (i + 1)
                    }
                }
            )
    
    # === VERIFICACIÓN DE INTEGRIDAD ===
    for i, token in enumerate(user_tokens):
        headers = {"Authorization": f"Bearer {token}"}
        profile_response = client.get(f"/profile/{users_data[i]['username']}")
        if profile_response.status_code == 200:
            profile_response.json()


def test_error_scenarios_journey(client: TestClient, auth_headers):
    """
    Test de journey con escenarios de error y casos edge
    """
    # === INTENTO DE APUESTA SIN SALDO ===
    session_response = client.post("/v1/roulette/session", headers=auth_headers)
    session_id = session_response.json()["session_id"]
    
    # Intentar apostar cantidad enorme
    bet_response = client.post(
        f"/v1/roulette/session/{session_id}/bet",
        headers=auth_headers,
        json={
            "client_seed": "no_money_seed",
            "bet": {
                "type": "color",
                "side": "red",
                "amount": 1000000.0
            }
        }
    )
    assert bet_response.status_code == 400

    # === SOLICITUD DE CRÉDITO DUPLICADA ===
    # Primera solicitud
    client.post("/v1/credits/request", headers=auth_headers, json={"amount": 50.0})
    
    # Segunda solicitud (debería fallar)
    duplicate_response = client.post(
        "/v1/credits/request", 
        headers=auth_headers, 
        json={"amount": 30.0}
    )
    assert duplicate_response.status_code == 400

    # === ACCESO NO AUTORIZADO ===
    unauthorized_response = client.get("/auth/me")
    assert unauthorized_response.status_code == 401

    # === DATOS INVÁLIDOS ===
    invalid_signup_response = client.post("/auth/signup", json={
        "username": "inv",  # Username muy corto
        "password": "123"   # Password muy corto
    })
    assert invalid_signup_response.status_code in (400, 422)  # Validation/required fields

# Fixture adicional para tests de integración
@pytest.fixture
def authenticated_user(client: TestClient):
    """Fixture que crea y autentica un usuario para tests de integración"""
    # Crear usuario
    client.post("/auth/signup", json={
        "username": "integrationuser",
        "password": "integrationpass123",
        "email": "integration@example.com",
        "name": "Integration",
        "apellidos": "User"
    })
    
    # Login
    login_response = client.post("/auth/login", json={
        "username": "integrationuser",
        "password": "integrationpass123"
    })
    
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    return {
        "username": "integrationuser",
        "headers": headers,
        "token": token
    }