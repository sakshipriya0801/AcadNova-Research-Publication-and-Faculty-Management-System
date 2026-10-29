"""ORCID orchestration service."""

from fastapi import HTTPException, status

from app.integrations.base import IntegrationError
from app.integrations.orcid import OrcidClient
from app.utils.author_matching import normalize_orcid


def _client() -> OrcidClient:
    return OrcidClient()


def _faculty_orcid(faculty: dict) -> str:
    orcid = normalize_orcid(faculty.get("orcid_id"))
    if not orcid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No ORCID ID is linked to this faculty profile",
        )
    return orcid


def _run(func):
    try:
        return func()
    except IntegrationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


def get_profile(faculty: dict):
    orcid = _faculty_orcid(faculty)
    return _run(lambda: _client().get_profile(orcid))


def get_works(faculty: dict, page: int = 1, page_size: int = 10) -> dict:
    orcid = _faculty_orcid(faculty)
    return _run(lambda: _client().get_works(orcid, page, page_size))


def search_researchers(query: str, page: int = 1, page_size: int = 10) -> dict:
    return _run(lambda: _client().search_researchers(query, page, page_size))


def get_researcher(orcid_id: str):
    return _run(lambda: _client().get_profile(orcid_id))


def get_work(faculty: dict, work_id: str):
    orcid = _faculty_orcid(faculty)
    return _run(lambda: _client().get_work(orcid, work_id))
