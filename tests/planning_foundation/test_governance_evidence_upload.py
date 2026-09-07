from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient

from services.api import create_app
from services.planning_foundation.governance_models import GovernanceProposal
from services.planning_foundation.governance_service import GovernanceService
from tests.planning_foundation.conftest import make_event_command


PASSWORD = "correct horse battery staple"


def register(client: TestClient, email: str):
    account = client.post("/auth/signup", json={"email":email,"display_name":email.split("@")[0],"account_type":"INDIVIDUAL","password":PASSWORD}).json()
    token = client.post("/auth/signin", json={"email":email,"password":PASSWORD}).json()["access_token"]
    return UUID(account["id"]), {"Authorization":f"Bearer {token}"}


def test_pdf_and_image_evidence_upload_validation_scope_and_isolation(database, service, tmp_path: Path):
    upload_root = tmp_path / "governance"
    client = TestClient(create_app(database, governance_upload_root=upload_root))
    owner, headers = register(client, "evidence-owner@example.com")
    _outsider, outsider_headers = register(client, "evidence-outsider@example.com")
    event = service.create_event(make_event_command(owner, name="Gachibowli Community Lake Cleanup"), idempotency_key="evidence-event")
    with database.connect() as connection:
        connection.execute("INSERT INTO event_memberships(event_id,account_id,role,status) VALUES(%s,%s,'ORGANIZER','ACTIVE')", (event.id, owner))
    state = GovernanceService(database).store_assessment(GovernanceProposal.model_validate({
        "event_id":event.id,"base_event_version":event.version,"governance_required":True,"completeness":"INCOMPLETE","internal_risk":"MEDIUM","review_mode":"ORGANIZER","organizer_visible_status":"NEEDS_INFORMATION","reasoning_summary":"Targeted lake governance information.","items":[{"category":"PUBLIC_SPACE_PERMISSION","label":"Public Lake Access","knowledge_type":"UNKNOWN","reason":"Access confirmation is missing.","suggested_documents":["Permission letter"]}]
    }), owner)
    item_id = state["items"][0]["id"]
    with database.connect() as connection:
        before = {table:connection.execute(f"SELECT count(*) AS n FROM {table}").fetchone()["n"] for table in ("stages","work_items","actor_requirements","event_memberships")}

    pdf = client.post(f"/governance/items/{item_id}/evidence", headers=headers, data={"label":"Lake access permission","note":"Organizer copy"}, files={"file":("permission-letter.pdf", b"%PDF-1.4\nproof\n%%EOF", "application/pdf")})
    assert pdf.status_code == 201
    image = client.post(f"/governance/items/{item_id}/evidence", headers=headers, files={"file":("authority-email.png", b"\x89PNG\r\n\x1a\nproof-image", "image/png")})
    assert image.status_code == 201
    evidence = image.json()["items"][0]["evidence"]
    assert [entry["original_filename"] for entry in evidence] == ["permission-letter.pdf", "authority-email.png"]
    assert all("storage_key" not in entry for entry in evidence)
    assert image.json()["items"][0]["status"] == "PROVIDED"

    unsupported = client.post(f"/governance/items/{item_id}/evidence", headers=headers, files={"file":("proof.exe", b"MZproof", "application/octet-stream")})
    assert unsupported.status_code == 422
    oversized = client.post(f"/governance/items/{item_id}/evidence", headers=headers, files={"file":("large.pdf", b"%PDF-" + b"x" * (10 * 1024 * 1024), "application/pdf")})
    assert oversized.status_code == 422
    denied = client.post(f"/governance/items/{item_id}/evidence", headers=outsider_headers, files={"file":("other.pdf", b"%PDF-1.4\nproof", "application/pdf")})
    assert denied.status_code == 403

    refreshed = client.get(f"/events/{event.id}/governance", headers=headers)
    assert refreshed.status_code == 200
    assert len(refreshed.json()["items"][0]["evidence"]) == 2
    with database.connect() as connection:
        rows = connection.execute("SELECT original_filename,content_type,file_size,storage_key,submitted_by FROM governance_evidence WHERE governance_item_id=%s ORDER BY submitted_at", (item_id,)).fetchall()
        assert len(rows) == 2 and rows[0]["submitted_by"] == owner
        assert all((upload_root / row["storage_key"]).is_file() for row in rows)
        assert len(list(upload_root.iterdir())) == 2
        assert connection.execute("SELECT status FROM governance_items WHERE id=%s", (item_id,)).fetchone()["status"] == "PROVIDED"
        for table, count in before.items():
            assert connection.execute(f"SELECT count(*) AS n FROM {table}").fetchone()["n"] == count
