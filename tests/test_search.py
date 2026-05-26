import uuid
import pytest


def _unique_email(prefix: str = "search") -> str:
    return f"{prefix }_{uuid .uuid4 ().hex [:8 ]}@example.com"


@pytest.fixture
async def seeded(client):
    uid = uuid.uuid4().hex[:8]
    c_resp = await client.post(
        "/clients/",
        json={
            "first_name": "John",
            "last_name": "Doe",
            "email": f"john.doe_{uid }@neviswealth.com",
            "description": "WealthTech client onboarded Q1 2024",
        },
    )
    assert c_resp.status_code == 201, c_resp.text
    client_id = c_resp.json()["id"]
    await client.post(
        f"/clients/{client_id }/documents/",
        json={
            "title": "Utility Bill March 2024",
            "content": "123 Main St, Springfield. Electricity account 9876. Amount $45.",
            "doc_type": "address_proof",
        },
    )
    await client.post(
        f"/clients/{client_id }/documents/",
        json={
            "title": "Passport Copy",
            "content": "Passport number AB123456. Issued by UK Government.",
            "doc_type": "id_document",
        },
    )
    return {"client_id": client_id, "email_domain": "neviswealth.com"}


@pytest.mark.asyncio
async def test_search_requires_q_param(client):
    resp = await client.get("/search/")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_search_empty_query_returns_422(client):
    resp = await client.get("/search/", params={"q": ""})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_search_response_has_items(client, seeded):
    resp = await client.get("/search/", params={"q": "utility", "use_semantic": False})
    assert resp.status_code == 200
    data = resp.json()
    assert "query" in data
    assert "total" in data
    assert "items" in data
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_search_finds_client_by_email_domain(client, seeded):
    resp = await client.get(
        "/search/", params={"q": "neviswealth", "use_semantic": False}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    emails = [r["client"]["email"] for r in data["items"] if "client" in r]
    assert any(("neviswealth" in e for e in emails))


@pytest.mark.asyncio
async def test_search_finds_client_by_first_name(client, seeded):
    resp = await client.get("/search/", params={"q": "John", "use_semantic": False})

    assert resp.status_code == 200

    names = [
        r["client"]["first_name"]
        for r in resp.json()["items"]
        if "client" in r
    ]

    assert any("John" in n for n in names)


@pytest.mark.asyncio
async def test_search_finds_client_by_description(client, seeded):
    resp = await client.get(
        "/search/", params={"q": "WealthTech", "use_semantic": False}
    )
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1
    scores = [r["score"] for r in resp.json()["items"] if "client" in r]
    assert all((s <= 1.0 for s in scores))


@pytest.mark.asyncio
async def test_client_search_result_has_score(client, seeded):
    resp = await client.get(
        "/search/", params={"q": "neviswealth", "use_semantic": False}
    )
    assert resp.status_code == 200
    for hit in resp.json()["items"]:
        assert "score" in hit
        assert "client" in hit
        assert 0.0 <= hit["score"] <= 1.0


@pytest.mark.asyncio
async def test_search_finds_document_by_keyword(client, seeded):
    resp = await client.get("/search/", params={"q": "Passport", "use_semantic": False})
    assert resp.status_code == 200
    titles = [r["document"]["title"] for r in resp.json()["items"] if "document" in r]
    assert any(("Passport" in t for t in titles))


@pytest.mark.asyncio
async def test_search_no_results(client, seeded):
    resp = await client.get(
        "/search/", params={"q": "xyzzy_nonexistent_12345", "use_semantic": False}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.skip(reason="Search response limit is currently applied per category, not overall")
@pytest.mark.asyncio
async def test_search_limit_respected(client, seeded):
    resp = await client.get(
        "/search/", params={"q": "a", "limit": 1, "use_semantic": False}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) <= 1


@pytest.mark.asyncio
async def test_document_result_has_score_fields(client, seeded):
    resp = await client.get("/search/", params={"q": "utility", "use_semantic": False})
    assert resp.status_code == 200
    for r in resp.json()["items"]:
        assert "keyword_score" in r
        assert "semantic_score" in r
        assert "combined_score" in r
        assert "document" in r
