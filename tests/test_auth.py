def test_auth_smoke_flow(client):
    register_response = client.post(
        "/api/v1/auth/register",
        json={"email": "alice@example.com", "password": "supersecret123"},
    )
    assert register_response.status_code == 200
    register_payload = register_response.json()
    assert "access_token" in register_payload
    assert "refresh_token" in register_payload

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "supersecret123"},
    )
    assert login_response.status_code == 200
    login_payload = login_response.json()
    access_token = login_payload["access_token"]
    refresh_token = login_payload["refresh_token"]

    me_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_response.status_code == 200
    me_payload = me_response.json()
    assert me_payload["email"] == "alice@example.com"

    refresh_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_response.status_code == 200
    refreshed_payload = refresh_response.json()
    assert "access_token" in refreshed_payload
    assert "refresh_token" in refreshed_payload
