"""Web of Science orchestration service."""

from fastapi import HTTPException

from app.integrations.base import IntegrationError
from app.integrations.web_of_science import WebOfScienceClient


def _client() -> WebOfScienceClient:
    return WebOfScienceClient()


def _run(func):
    try:
        return func()
    except IntegrationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


def search_web_of_science(
    query: str = "",
    page: int = 1,
    page_size: int = 10,
    author=None,
    title=None,
    doi=None,
) -> dict:
    return _run(
        lambda: _client().search(
            query=query, page=page, page_size=page_size, author=author, title=title, doi=doi
        )
    )


def get_publication(record_id: str):
    return _run(lambda: _client().get_publication(record_id))


def get_researcher(researcher_id: str):
    return _run(lambda: _client().get_researcher(researcher_id))
