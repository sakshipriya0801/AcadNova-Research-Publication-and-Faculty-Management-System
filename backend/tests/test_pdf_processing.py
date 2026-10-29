"""PDF text extraction & document processing tests (Step 13)."""

import uuid
from pathlib import Path

import pymupdf
import pytest

from app.database import mongodb
from app.models.collections import ACADEMIC_YEARS, DOCUMENT_CONTENTS, DOCUMENTS, USERS
from app.services import pdf_processing_service
from app.utils import security

PASSWORD = "StrongPassword123"

STORAGE_DIR = "/tmp/opencode/test_documents"


def _make_pdf(pages_text, metadata=None) -> bytes:
    doc = pymupdf.open()
    for text in pages_text:
        page = doc.new_page()
        page.insert_text((72, 72), text, fontsize=12)
    if metadata:
        doc.set_metadata(metadata)
    data = doc.tobytes()
    doc.close()
    return data


def _make_encrypted_pdf(tmp_path) -> bytes:
    doc = pymupdf.open()
    doc.new_page()
    doc.new_page().insert_text((72, 72), "secret", fontsize=12)
    path = tmp_path / "encrypted.pdf"
    doc.save(path, encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="secret", owner_pw="secret")
    doc.close()
    return path.read_bytes()


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
    email = f"pdf_{uuid.uuid4().hex[:10]}@example.com"
    reg = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "name": "PDF Faculty",
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


def _create_publication(client, token) -> dict:
    resp = client.post(
        "/api/publications",
        headers=_h(token),
        json={
            "title": f"PDF Pub {uuid.uuid4().hex[:6]}",
            "authors": ["Author One", "Author Two"],
            "publication_type": "research_publication",
            "faculty_author_position": 1,
            "publication_date": "2025-08-15",
            "indexing": ["Scopus"],
        },
    )
    assert resp.status_code == 201
    return resp.json()


def _upload(client, token, pub_id, filename="paper.pdf", content=None):
    return client.post(
        f"/api/publications/{pub_id}/documents",
        headers=_h(token),
        files={"file": (filename, content or _make_pdf(["Page one content"]), "application/pdf")},
        data={"document_type": "research_paper"},
    )


def _process(client, token, pub_id, doc_id):
    return client.post(
        f"/api/publications/{pub_id}/documents/{doc_id}/process", headers=_h(token)
    )


# --- Basic processing --------------------------------------------------------

def test_process_text_pdf(client):
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    doc = _upload(client, info["token"], pub["publication_id"]).json()
    assert doc["processing_status"] == "not_processed"

    resp = _process(client, info["token"], pub["publication_id"], doc["id"])
    assert resp.status_code == 200
    assert resp.json()["processing_status"] == "processed"
    assert resp.json()["page_count"] == 1
    assert resp.json()["extracted_text_length"] > 0


def test_multiple_pages_and_boundaries(client):
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    content = _make_pdf(["First page text", "Second page text"])
    doc = _upload(client, info["token"], pub["publication_id"], content=content).json()
    _process(client, info["token"], pub["publication_id"], doc["id"])

    resp = client.get(
        f"/api/publications/{pub['publication_id']}/documents/{doc['id']}/content",
        headers=_h(info["token"]),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["page_count"] == 2
    assert len(body["pages"]) == 2
    assert body["pages"][0]["page_number"] == 1
    assert "First page text" in body["pages"][0]["text"]
    assert body["pages"][1]["page_number"] == 2
    assert "Second page text" in body["pages"][1]["text"]


# --- Metadata ----------------------------------------------------------------

def test_pdf_metadata_extraction(client):
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    content = _make_pdf(
        ["content"],
        metadata={"title": "My Title", "author": "My Author", "subject": "Subj", "keywords": "kw1, kw2"},
    )
    doc = _upload(client, info["token"], pub["publication_id"], content=content).json()
    _process(client, info["token"], pub["publication_id"], doc["id"])

    resp = client.get(
        f"/api/publications/{pub['publication_id']}/documents/{doc['id']}/metadata",
        headers=_h(info["token"]),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "My Title"
    assert body["author"] == "My Author"
    assert body["subject"] == "Subj"
    assert body["keywords"] == "kw1, kw2"
    assert body["page_count"] == 1


def test_missing_metadata_is_null(client):
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    doc = _upload(client, info["token"], pub["publication_id"]).json()
    _process(client, info["token"], pub["publication_id"], doc["id"])

    resp = client.get(
        f"/api/publications/{pub['publication_id']}/documents/{doc['id']}/metadata",
        headers=_h(info["token"]),
    )
    assert resp.status_code == 200
    assert resp.json()["title"] is None


# --- Status endpoint ---------------------------------------------------------

def test_processing_status_endpoint(client):
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    doc = _upload(client, info["token"], pub["publication_id"]).json()

    resp = client.get(
        f"/api/publications/{pub['publication_id']}/documents/{doc['id']}/processing-status",
        headers=_h(info["token"]),
    )
    assert resp.json()["processing_status"] == "not_processed"

    _process(client, info["token"], pub["publication_id"], doc["id"])
    resp = client.get(
        f"/api/publications/{pub['publication_id']}/documents/{doc['id']}/processing-status",
        headers=_h(info["token"]),
    )
    assert resp.json()["processing_status"] == "processed"


# --- Authorization -----------------------------------------------------------

def test_faculty_process_own(client):
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    doc = _upload(client, info["token"], pub["publication_id"]).json()
    resp = _process(client, info["token"], pub["publication_id"], doc["id"])
    assert resp.status_code == 200


def test_faculty_cannot_process_other(client):
    info_a = _register_faculty(client)
    info_b = _register_faculty(client)
    pub = _create_publication(client, info_a["token"])
    doc = _upload(client, info_a["token"], pub["publication_id"]).json()
    resp = _process(client, info_b["token"], pub["publication_id"], doc["id"])
    assert resp.status_code == 403


def test_admin_can_process(client):
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    doc = _upload(client, info["token"], pub["publication_id"]).json()
    admin = _admin_token(client)
    resp = _process(client, admin, pub["publication_id"], doc["id"])
    assert resp.status_code == 200


def test_deleted_document_cannot_process(client):
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    doc = _upload(client, info["token"], pub["publication_id"]).json()
    client.delete(f"/api/publications/{pub['publication_id']}/documents/{doc['id']}", headers=_h(info["token"]))
    resp = _process(client, info["token"], pub["publication_id"], doc["id"])
    assert resp.status_code == 404


def test_cross_faculty_content_access(client):
    info_a = _register_faculty(client)
    info_b = _register_faculty(client)
    pub = _create_publication(client, info_a["token"])
    doc = _upload(client, info_a["token"], pub["publication_id"]).json()
    _process(client, info_a["token"], pub["publication_id"], doc["id"])

    resp = client.get(
        f"/api/publications/{pub['publication_id']}/documents/{doc['id']}/content",
        headers=_h(info_b["token"]),
    )
    assert resp.status_code == 403


def test_path_traversal_document_id(client):
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    for bogus in ["..%2F..%2Fetc%2Fpasswd", "....//....//etc/passwd", "%2e%2e%2fsecret"]:
        resp = client.get(
            f"/api/publications/{pub['publication_id']}/documents/{bogus}/processing-status",
            headers=_h(info["token"]),
        )
        assert resp.status_code == 404


def test_idor_document_from_another_publication(client):
    info_a = _register_faculty(client)
    info_b = _register_faculty(client)
    pub_a = _create_publication(client, info_a["token"])
    pub_b = _create_publication(client, info_b["token"])
    doc_a = _upload(client, info_a["token"], pub_a["publication_id"]).json()
    _process(client, info_a["token"], pub_a["publication_id"], doc_a["id"])

    # faculty B tries A's document id under B's own publication
    resp = client.get(
        f"/api/publications/{pub_b['publication_id']}/documents/{doc_a['id']}/content",
        headers=_h(info_b["token"]),
    )
    assert resp.status_code == 404


# --- Errors ------------------------------------------------------------------

def test_corrupted_pdf(client):
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    doc = _upload(client, info["token"], pub["publication_id"], content=b"%PDF-1.4\nnot really a pdf").json()
    resp = _process(client, info["token"], pub["publication_id"], doc["id"])
    assert resp.status_code == 422
    stored = mongodb.get_collection(DOCUMENTS).find_one({"document_id": doc["id"]})
    assert stored["processing_status"] == "failed"


def test_encrypted_pdf(client, tmp_path):
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    encrypted = _make_encrypted_pdf(tmp_path)
    doc = _upload(client, info["token"], pub["publication_id"], content=encrypted).json()
    resp = _process(client, info["token"], pub["publication_id"], doc["id"])
    assert resp.status_code == 422


def test_zero_page_pdf(client):
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    empty = (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[]/Count 0>>endobj\n"
        b"trailer<</Root 1 0 R>>\n"
    )
    uploaded = _upload(client, info["token"], pub["publication_id"], content=empty).json()
    resp = _process(client, info["token"], pub["publication_id"], uploaded["id"])
    assert resp.status_code == 422
    assert "no pages" in resp.json()["detail"].lower()


def test_missing_stored_file(client):
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    doc = _upload(client, info["token"], pub["publication_id"]).json()
    stored = mongodb.get_collection(DOCUMENTS).find_one({"document_id": doc["id"]})
    Path(STORAGE_DIR, stored["storage_path"]).unlink()

    resp = _process(client, info["token"], pub["publication_id"], doc["id"])
    assert resp.status_code == 404


# --- Reprocessing ------------------------------------------------------------

def test_reprocess_replaces_content(client):
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    doc = _upload(client, info["token"], pub["publication_id"], content=_make_pdf(["Version one"])).json()
    _process(client, info["token"], pub["publication_id"], doc["id"])

    # overwrite the physical file with different content
    stored = mongodb.get_collection(DOCUMENTS).find_one({"document_id": doc["id"]})
    Path(STORAGE_DIR, stored["storage_path"]).write_bytes(_make_pdf(["Version two content"]))

    resp = _process(client, info["token"], pub["publication_id"], doc["id"])
    assert resp.status_code == 200

    contents = list(mongodb.get_collection(DOCUMENT_CONTENTS).find({"document_id": doc["id"]}))
    assert len(contents) == 1
    assert "Version two content" in contents[0]["text"]


def test_failed_reprocess_preserves_content(client):
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    doc = _upload(client, info["token"], pub["publication_id"], content=_make_pdf(["Good content"])).json()
    _process(client, info["token"], pub["publication_id"], doc["id"])

    # corrupt the physical file
    stored = mongodb.get_collection(DOCUMENTS).find_one({"document_id": doc["id"]})
    Path(STORAGE_DIR, stored["storage_path"]).write_bytes(b"%PDF-1.4\ngarbage")

    resp = _process(client, info["token"], pub["publication_id"], doc["id"])
    assert resp.status_code == 422

    contents = list(mongodb.get_collection(DOCUMENT_CONTENTS).find({"document_id": doc["id"]}))
    assert len(contents) == 1
    assert "Good content" in contents[0]["text"]


# --- Data integrity ----------------------------------------------------------

def test_processing_does_not_change_verification(client):
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    doc = _upload(client, info["token"], pub["publication_id"]).json()
    _process(client, info["token"], pub["publication_id"], doc["id"])

    pub_doc = mongodb.get_database()["publications"].find_one(
        {"publication_id": pub["publication_id"]}
    )
    assert pub_doc["verification_status"] == "pending"
    assert pub_doc["points_awarded"] == 0
