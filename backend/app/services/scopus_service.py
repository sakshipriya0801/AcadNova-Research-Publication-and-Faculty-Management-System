"""Scopus orchestration service."""

from fastapi import HTTPException, status

from app.integrations.base import IntegrationError
from app.integrations.scopus import ScopusClient


def _client() -> ScopusClient:
    return ScopusClient()


def _run(func):
    try:
        return func()
    except IntegrationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


def search_scopus(
    query: str = "",
    page: int = 1,
    page_size: int = 10,
    author=None,
    title=None,
    doi=None,
    author_id=None,
) -> dict:
    return _run(
        lambda: _client().search(
            query=query,
            page=page,
            page_size=page_size,
            author=author,
            title=title,
            doi=doi,
            author_id=author_id,
        )
    )


def get_publication(record_id: str):
    return _run(lambda: _client().get_publication(record_id))


def get_author(author_id: str):
    return _run(lambda: _client().get_author(author_id))
