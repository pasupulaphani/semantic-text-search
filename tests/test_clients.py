import pytest

CLIENT_PAYLOAD = {
    "first_name": "Jane",
    "last_name": "Smith",
    "email": "jane@example.com",
    "description": "Test client",
    "social_links": ["https://linkedin.com/in/janesmith"],
}


@pytest.mark.asyncio
async def test_create_client_returns_201(client):
    resp = await client.post("/clients/", json=CLIENT_PAYLOAD)
    assert resp.status_code == 201
    data = resp.json()
    assert data["first_name"] == "Jane"
    assert data["last_name"] == "Smith"
    assert data["email"] == "jane@example.com"
    assert data["description"] == "Test client"
    assert data["social_links"] == ["https://linkedin.com/in/janesmith"]
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_client_duplicate_email_returns_409(client):
    await client.post("/clients/", json=CLIENT_PAYLOAD)
    resp = await client.post("/clients/", json=CLIENT_PAYLOAD)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_create_client_missing_required_fields_returns_422(client):
    resp = await client.post("/clients/", json={"first_name": "Jane"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_client_invalid_email_returns_422(client):
    payload = {**CLIENT_PAYLOAD, "email": "not-an-email"}
    resp = await client.post("/clients/", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_clients(client):
    await client.post(
        "/clients/", json={**CLIENT_PAYLOAD, "email": "list1@example.com"}
    )
    await client.post(
        "/clients/", json={**CLIENT_PAYLOAD, "email": "list2@example.com"}
    )
    resp = await client.get("/clients/")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) >= 2


@pytest.mark.asyncio
async def test_get_client(client):
    create_resp = await client.post(
        "/clients/", json={**CLIENT_PAYLOAD, "email": "get@example.com"}
    )
    client_id = create_resp.json()["id"]
    resp = await client.get(f"/clients/{client_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == client_id


@pytest.mark.asyncio
async def test_get_client_not_found_returns_404(client):
    resp = await client.get("/clients/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_client(client):
    create_resp = await client.post(
        "/clients/", json={**CLIENT_PAYLOAD, "email": "patch@example.com"}
    )
    client_id = create_resp.json()["id"]
    resp = await client.patch(f"/clients/{client_id}", json={"first_name": "Updated"})
    assert resp.status_code == 200
    assert resp.json()["first_name"] == "Updated"
    assert resp.json()["last_name"] == "Smith"


@pytest.mark.asyncio
async def test_delete_client(client):
    create_resp = await client.post(
        "/clients/", json={**CLIENT_PAYLOAD, "email": "delete@example.com"}
    )
    client_id = create_resp.json()["id"]
    del_resp = await client.delete(f"/clients/{client_id}")
    assert del_resp.status_code == 204
    get_resp = await client.get(f"/clients/{client_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_create_client_rejects_dangerous_social_link(client):
    payload = {
        **CLIENT_PAYLOAD,
        "email": "danger@example.com",
        "social_links": ["http://127.0.0.1/admin;DROP TABLE users"],
    }
    resp = await client.post("/clients/", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_client_rejects_ftp_social_link(client):
    payload = {
        **CLIENT_PAYLOAD,
        "email": "ftp@example.com",
        "social_links": ["ftp://example.com/profile"],
    }
    resp = await client.post("/clients/", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_update_client_rejects_localhost_social_link(client):
    create_resp = await client.post(
        "/clients/", json={**CLIENT_PAYLOAD, "email": "update@example.com"}
    )
    client_id = create_resp.json()["id"]
    resp = await client.patch(
        f"/clients/{client_id}", json={"social_links": ["https://localhost/profile"]},
    )
    assert resp.status_code == 422
