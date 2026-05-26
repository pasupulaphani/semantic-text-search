import uuid
import pytest

DOC_PAYLOAD = {
    "title": "Utility Bill – March 2024",
    "content": "123 Main St, Springfield. Account: 9876. Amount due: $45.00.",
    "doc_type": "address_proof",
}


def _unique_client():
    uid = uuid.uuid4().hex[:8]
    return {
        "first_name": "Doc",
        "last_name": "Owner",
        "email": f"docowner_{uid }@example.com",
    }


@pytest.fixture
async def created_client(client):
    resp = await client.post("/clients/", json=_unique_client())
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_create_document_returns_201(client, created_client):
    client_id = created_client["id"]
    resp = await client.post(f"/clients/{client_id }/documents/", json=DOC_PAYLOAD)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == DOC_PAYLOAD["title"]
    assert data["content"] == DOC_PAYLOAD["content"]
    assert data["client_id"] == client_id
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_document_missing_title_returns_422(client, created_client):
    client_id = created_client["id"]
    resp = await client.post(
        f"/clients/{client_id }/documents/", json={"content": "some content"}
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_document_unknown_client_returns_404(client):
    resp = await client.post(
        "/clients/00000000-0000-0000-0000-000000000000/documents/", json=DOC_PAYLOAD
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_documents(client, created_client):
    client_id = created_client["id"]
    await client.post(f"/clients/{client_id }/documents/", json=DOC_PAYLOAD)
    await client.post(
        f"/clients/{client_id }/documents/",
        json={**DOC_PAYLOAD, "title": "Passport Copy"},
    )
    resp = await client.get(f"/clients/{client_id }/documents/")
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


@pytest.mark.asyncio
async def test_get_document(client, created_client):
    client_id = created_client["id"]
    create_resp = await client.post(
        f"/clients/{client_id }/documents/", json=DOC_PAYLOAD
    )
    doc_id = create_resp.json()["id"]
    resp = await client.get(f"/clients/{client_id }/documents/{doc_id }")
    assert resp.status_code == 200
    assert resp.json()["id"] == doc_id


@pytest.mark.asyncio
async def test_get_document_not_found_returns_404(client, created_client):
    client_id = created_client["id"]
    resp = await client.get(
        f"/clients/{client_id }/documents/00000000-0000-0000-0000-000000000000"
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_document(client, created_client):
    client_id = created_client["id"]
    create_resp = await client.post(
        f"/clients/{client_id }/documents/", json=DOC_PAYLOAD
    )
    doc_id = create_resp.json()["id"]
    resp = await client.patch(
        f"/clients/{client_id }/documents/{doc_id }", json={"title": "Updated Title"}
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated Title"
    assert resp.json()["content"] == DOC_PAYLOAD["content"]


@pytest.mark.asyncio
async def test_delete_document(client, created_client):
    client_id = created_client["id"]
    create_resp = await client.post(
        f"/clients/{client_id }/documents/", json=DOC_PAYLOAD
    )
    doc_id = create_resp.json()["id"]
    del_resp = await client.delete(f"/clients/{client_id }/documents/{doc_id }")
    assert del_resp.status_code == 204
    get_resp = await client.get(f"/clients/{client_id }/documents/{doc_id }")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_client_cascades_documents(client):
    uid = uuid.uuid4().hex[:8]
    create_resp = await client.post(
        "/clients/",
        json={
            "first_name": "Cascade",
            "last_name": "Test",
            "email": f"cascade_{uid }@example.com",
        },
    )
    client_id = create_resp.json()["id"]
    doc_resp = await client.post(f"/clients/{client_id }/documents/", json=DOC_PAYLOAD)
    doc_id = doc_resp.json()["id"]
    await client.delete(f"/clients/{client_id }")
    get_resp = await client.get(f"/clients/{client_id }/documents/{doc_id }")
    assert get_resp.status_code == 404
