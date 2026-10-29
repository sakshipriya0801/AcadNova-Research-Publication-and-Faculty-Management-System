"""Crossref REST API client."""

import re
from typing import Optional

from app.config.settings import get_settings
from app.integrations.base import BaseIntegrationClient, IntegrationError
from app.schemas.external_publication import ExternalAuthor, ExternalPublicationResult
from app.services.publication_service import normalize_doi


def _clean_abstract(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    text = re.sub(r"<[^>]+>", " ", value)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


class CrossrefClient(BaseIntegrationClient):
    source = "crossref"

    def __init__(self):
        settings = get_settings()
        self.base_url = settings.crossref_api_url.rstrip("/")
        self.timeout = settings.crossref_timeout_seconds

    def search(
        self,
        query: str = "",
        page: int = 1,
        page_size: int = 10,
        author: Optional[str] = None,
        title: Optional[str] = None,
        doi: Optional[str] = None,
    ) -> dict:
        params: dict = {
            "rows": page_size,
            "offset": (page - 1) * page_size,
        }
        if doi:
            params["filter"] = f"doi:{doi}"
        else:
            if query:
                params["query"] = query
            if title:
                params["query.title"] = title
            if author:
                params["query.author"] = author

        data = self._get_json(f"{self.base_url}/works", params)
        message = data.get("message") or {}
        total = int(message.get("total-results", 0))
        items = message.get("items") or []
        return {"total": total, "results": [self._normalize(item) for item in items]}

    def get_by_identifier(self, identifier: str) -> Optional[ExternalPublicationResult]:
        doi = normalize_doi(identifier)
        if not doi:
            raise IntegrationError("Invalid DOI", status_code=400)
        data = self._get_json(f"{self.base_url}/works/{doi}")
        item = data.get("message")
        if not item:
            return None
        return self._normalize(item)

    def _normalize(self, item: dict) -> ExternalPublicationResult:
        doi = normalize_doi(item.get("DOI"))

        authors: list[ExternalAuthor] = []
        for position, author in enumerate(item.get("author") or [], start=1):
            given = author.get("given")
            family = author.get("family")
            name = author.get("name") or " ".join(filter(None, [given, family]))
            affiliations = None
            if author.get("affiliation"):
                affiliations = [
                    aff.get("name")
                    for aff in author["affiliation"]
                    if isinstance(aff, dict) and aff.get("name")
                ] or None
            authors.append(
                ExternalAuthor(
                    name=name or None,
                    given_name=given,
                    family_name=family,
                    affiliation=affiliations,
                    author_position=position,
                )
            )

        containers = item.get("container-title") or []
        journal = containers[0] if containers else None
        publication_date, publication_year = self._extract_date(item)

        return ExternalPublicationResult(
            source=self.source,
            source_record_id=doi,
            title=(item.get("title") or [None])[0] if item.get("title") else None,
            abstract=_clean_abstract(item.get("abstract")),
            authors=authors,
            journal=journal,
            conference=None,
            publisher=item.get("publisher"),
            doi=doi,
            publication_date=publication_date,
            publication_year=publication_year,
            url=item.get("URL"),
            indexing=[],
            external_identifiers={"doi": doi} if doi else {},
            raw_metadata=item,
        )

    @staticmethod
    def _extract_date(item: dict):
        published = item.get("published") or {}
        date_parts = published.get("date-parts") or []
        parts = date_parts[0] if date_parts else []
        year = parts[0] if len(parts) > 0 and parts[0] else None
        month = parts[1] if len(parts) > 1 and parts[1] else None
        day = parts[2] if len(parts) > 2 and parts[2] else None

        date_str = None
        if year:
            if month and day:
                date_str = f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
            elif month:
                date_str = f"{int(year):04d}-{int(month):02d}"
            else:
                date_str = f"{int(year):04d}"
        return date_str, int(year) if year else None
