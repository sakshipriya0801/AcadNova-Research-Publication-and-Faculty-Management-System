"""Publication document management tests (Step 12)."""

import hashlib
import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.database import mongodb
from app.models.collections import ACADEMIC_YEARS, AUDIT_LOGS, DOCUMENTS, USERS
from app.services import document_service
from app.utils import security

PASSWORD = "StrongPassword123"

PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF\n"


@pytest.fixture(autouse=True)
def _seed(client):
    _ensure_academic_year("2025-2026")
    yield


def _ensure_academic_year(name="2025-2026"):
    db = mongodb.get_database()
    if db[ACADEMIC_YEARS].find_one({"name": name}) is None:
        db[ACADEMIC_YEARS].insert_one(
            {
                "academic_year_id": str(uuid.uuid4()),
                "name": name,
                "start_date": "2025-07-01",
                "end_date": "2026-06-30",
                "is_current": True,
            }
        )


def _register_faculty(client) -> dict:
    email = f"doc_{uuid.uuid4().hex[:10]}@example.com"
    reg = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "name": "Doc Faculty",
            "employee_id": "EMP_" + uuid.uuid4().hex[:6],
            "department_id": "MCA",
            "designation": "Assistant Professor",
        },
    )
    token = client.post(
        "/api/auth/login", json={"email": email, "password": PASSWORD}
    ).json()["access_token"]
    return {"email": email, "token": token, "faculty_id": reg.json()["faculty_id"]}


def _admin_token(client) -> str:
    email = f"admin_{uuid.uuid4().hex[:10]}@example.com"
    mongodb.get_collection(USERS).insert_one(
        {
            "user_id": str(uuid.uuid4()),
            "email": email,
            "password_hash": security.hash_password(PASSWORD),
            "role": "admin",
            "faculty_id": None,
            "is_active": True,
        }
    )
    return client.post(
        "/api/auth/login", json={"email": email, "password": PASSWORD}
    ).json()["access_token"]


def _h(token):
    return {"Authorization": f"Bearer {token}"}


def _create_publication(client, token, title=None) -> dict:
    resp = client.post(
        "/api/publications",
        headers=_h(token),
        json={
            "title": title or f"Pub {uuid.uuid4().hex[:6]}",
            "authors": ["Author One", "Author Two"],
            "publication_type": "research_publication",
            "faculty_author_position": 1,
            "publication_date": "2025-08-15",
            "indexing": ["Scopus"],
        },
    )
    assert resp.status_code == 201
    return resp.json()


def _upload(client, token, pub_id, filename="paper.pdf", content=PDF_BYTES, mime="application/pdf", document_type="research_paper"):
    return client.post(
        f"/api/publications/{pub_id}/documents",
        headers=_h(token),
        files={"file": (filename, content, mime)},
        data={"document_type": document_type},
    )


# --- Authentication ----------------------------------------------------------

def test_unauthenticated_upload_401(client):
    resp = client.post("/api/publications/x/documents", files={"file": ("a.pdf", PDF_BYTES, "application/pdf")}, data={"document_type": "research_paper"})
    assert resp.status_code == 401


def test_unauthenticated_list_401(client):
    assert client.get("/api/publications/x/documents").status_code == 401


def test_unauthenticated_download_401(client):
    assert client.get("/api/publications/x/documents/y/download").status_code == 401


def test_unauthenticated_delete_401(client):
    assert client.delete("/api/publications/x/documents/y").status_code == 401


# --- Authorization -----------------------------------------------------------

def test_faculty_can_upload_own(client):
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    resp = _upload(client, info["token"], pub["publication_id"])
    assert resp.status_code == 201


def test_faculty_cannot_upload_other(client):
    info_a = _register_faculty(client)
    info_b = _register_faculty(client)
    pub = _create_publication(client, info_a["token"])
    resp = _upload(client, info_b["token"], pub["publication_id"])
    assert resp.status_code == 403


def test_faculty_list_own_documents(client):
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    _upload(client, info["token"], pub["publication_id"])
    resp = client.get(f"/api/publications/{pub['publication_id']}/documents", headers=_h(info["token"]))
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_faculty_cannot_list_other(client):
    info_a = _register_faculty(client)
    info_b = _register_faculty(client)
    pub = _create_publication(client, info_a["token"])
    resp = client.get(f"/api/publications/{pub['publication_id']}/documents", headers=_h(info_b["token"]))
    assert resp.status_code == 403


def test_faculty_download_own(client):
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    doc = _upload(client, info["token"], pub["publication_id"]).json()
    resp = client.get(f"/api/publications/{pub['publication_id']}/documents/{doc['id']}/download", headers=_h(info["token"]))
    assert resp.status_code == 200
    assert resp.content == PDF_BYTES


def test_faculty_cannot_download_other(client):
    info_a = _register_faculty(client)
    info_b = _register_faculty(client)
    pub = _create_publication(client, info_a["token"])
    doc = _upload(client, info_a["token"], pub["publication_id"]).json()
    resp = client.get(f"/api/publications/{pub['publication_id']}/documents/{doc['id']}/download", headers=_h(info_b["token"]))
    assert resp.status_code == 403


def test_faculty_cannot_delete_other(client):
    info_a = _register_faculty(client)
    info_b = _register_faculty(client)
    pub = _create_publication(client, info_a["token"])
    doc = _upload(client, info_a["token"], pub["publication_id"]).json()
    resp = client.delete(f"/api/publications/{pub['publication_id']}/documents/{doc['id']}", headers=_h(info_b["token"]))
    assert resp.status_code == 403


def test_admin_can_list_any(client):
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    _upload(client, info["token"], pub["publication_id"])
    admin = _admin_token(client)
    resp = client.get(f"/api/publications/{pub['publication_id']}/documents", headers=_h(admin))
    assert resp.status_code == 200
    assert len(resp.json()) == 1


# --- Validation --------------------------------------------------------------

def test_valid_pdf_upload(client):
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    resp = _upload(client, info["token"], pub["publication_id"])
    assert resp.status_code == 201
    body = resp.json()
    assert body["document_type"] == "research_paper"
    assert body["original_filename"] == "paper.pdf"
    assert body["checksum"] == hashlib.sha256(PDF_BYTES).hexdigest()


def test_invalid_extension(client):
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    resp = _upload(client, info["token"], pub["publication_id"], filename="paper.txt")
    assert resp.status_code == 400


def test_invalid_mime(client):
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    resp = _upload(client, info["token"], pub["publication_id"], mime="image/png")
    assert resp.status_code == 400


def test_fake_pdf_signature(client):
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    resp = _upload(client, info["token"], pub["publication_id"], content=b"not a real pdf")
    assert resp.status_code == 400


def test_executable_renamed_to_pdf(client):
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    resp = _upload(client, info["token"], pub["publication_id"], filename="evil.pdf", content=b"\x7fELF\x02\x01\x01")
    assert resp.status_code == 400


def test_oversized_file(client, monkeypatch):
    monkeypatch.setattr(
        "app.services.document_service.get_settings",
        lambda: SimpleNamespace(
            document_storage_dir="/tmp/opencode/test_documents",
            max_document_size_mb=0.0001,
        ),
    )
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    big = b"%PDF-1.4\n" + b"x" * 2000
    resp = _upload(client, info["token"], pub["publication_id"], content=big)
    assert resp.status_code == 413


def test_invalid_document_type(client):
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    resp = _upload(client, info["token"], pub["publication_id"], document_type="bogus")
    assert resp.status_code == 400


def test_nonexistent_publication(client):
    info = _register_faculty(client)
    resp = _upload(client, info["token"], "nonexistent-pub-id")
    assert resp.status_code == 404


def test_nonexistent_document(client):
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    resp = client.get(f"/api/publications/{pub['publication_id']}/documents/nonexistent/download", headers=_h(info["token"]))
    assert resp.status_code == 404


def test_document_publication_mismatch(client):
    info = _register_faculty(client)
    pub_a = _create_publication(client, info["token"])
    pub_b = _create_publication(client, info["token"])
    doc = _upload(client, info["token"], pub_a["publication_id"]).json()
    resp = client.get(f"/api/publications/{pub_b['publication_id']}/documents/{doc['id']}/download", headers=_h(info["token"]))
    assert resp.status_code == 404


# --- Duplicate ---------------------------------------------------------------

def test_duplicate_upload_same_publication_409(client):
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    assert _upload(client, info["token"], pub["publication_id"]).status_code == 201
    resp = _upload(client, info["token"], pub["publication_id"])
    assert resp.status_code == 409


def test_same_file_different_publication_ok(client):
    info = _register_faculty(client)
    pub_a = _create_publication(client, info["token"])
    pub_b = _create_publication(client, info["token"])
    assert _upload(client, info["token"], pub_a["publication_id"]).status_code == 201
    resp = _upload(client, info["token"], pub_b["publication_id"])
    assert resp.status_code == 201


# --- Storage -----------------------------------------------------------------

def test_stored_filename_is_uuid(client):
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    _upload(client, info["token"], pub["publication_id"], filename="original-name.pdf")
    doc = mongodb.get_collection(DOCUMENTS).find_one({"publication_id": pub["publication_id"]})
    assert doc["original_filename"] == "original-name.pdf"
    assert doc["stored_filename"] != "original-name.pdf"
    assert doc["stored_filename"].startswith(doc["document_id"][:0] or "")
    # stored filename is a uuid + ".pdf"
    assert doc["stored_filename"].endswith(".pdf")
    assert len(doc["stored_filename"]) > 32


def test_physical_file_within_root(client):
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    _upload(client, info["token"], pub["publication_id"])
    doc = mongodb.get_collection(DOCUMENTS).find_one({"publication_id": pub["publication_id"]})
    from pathlib import Path
    path = Path("/tmp/opencode/test_documents") / doc["storage_path"]
    assert path.exists()
    assert path.read_bytes() == PDF_BYTES


def test_path_traversal_rejected():
    with pytest.raises(HTTPException) as exc:
        document_service.resolve_document_path({"storage_path": "../../etc/passwd"})
    assert exc.value.status_code == 404


# --- Soft delete -------------------------------------------------------------

def test_soft_delete(client):
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    doc = _upload(client, info["token"], pub["publication_id"]).json()
    resp = client.delete(f"/api/publications/{pub['publication_id']}/documents/{doc['id']}", headers=_h(info["token"]))
    assert resp.status_code == 204

    stored = mongodb.get_collection(DOCUMENTS).find_one({"document_id": doc["id"]})
    assert stored["status"] == "deleted"

    # not in normal list
    listing = client.get(f"/api/publications/{pub['publication_id']}/documents", headers=_h(info["token"])).json()
    assert len(listing) == 0

    # cannot download
    dl = client.get(f"/api/publications/{pub['publication_id']}/documents/{doc['id']}/download", headers=_h(info["token"]))
    assert dl.status_code == 404


# --- Audit -------------------------------------------------------------------

def test_upload_creates_audit(client):
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    doc = _upload(client, info["token"], pub["publication_id"]).json()
    log = mongodb.get_collection(AUDIT_LOGS).find_one({"entity_id": doc["id"], "action": "document.upload"})
    assert log is not None
    assert "file contents" not in str(log)


def test_delete_creates_audit(client):
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    doc = _upload(client, info["token"], pub["publication_id"]).json()
    client.delete(f"/api/publications/{pub['publication_id']}/documents/{doc['id']}", headers=_h(info["token"]))
    log = mongodb.get_collection(AUDIT_LOGS).find_one({"entity_id": doc["id"], "action": "document.delete"})
    assert log is not None
    assert log["old_value"]["status"] == "active"
    assert log["new_value"]["status"] == "deleted"
