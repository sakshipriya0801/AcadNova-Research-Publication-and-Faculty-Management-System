"""Web of Science / Clarivate Starter API client."""

from typing import Optional

import httpx

from app.config.settings import get_settings
from app.integrations.base import BaseIntegrationClient, IntegrationError
from app.schemas.external_publication import ExternalAuthor, ExternalPublicationResult
from app.services.publication_service import normalize_doi

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


class WebOfScienceClient(BaseIntegrationClient):
    source = "web_of_science"

    def __init__(self):
        settings = get_settings()
        self.base_url = settings.web_of_science_api_url.rstrip("/")
        self.timeout = settings.web_of_science_timeout_seconds
        self.api_key = settings.web_of_science_api_key

    def _headers(self) -> dict:
        if not self.api_key:
            raise IntegrationError(
                "Web of Science API key is not configured", status_code=503
            )
        return {"X-ApiKey": self.api_key, "Accept": "application/json"}

    def _get_json(self, url, params=None, headers=None):
        try:
            response = httpx.get(url, params=params, headers=headers, timeout=self.timeout)
        except httpx.TimeoutException:
            raise IntegrationError("Web of Science request timed out", status_code=504)
        except httpx.HTTPError as exc:
            raise IntegrationError(f"Web of Science request failed: {exc}", status_code=502)

        if response.status_code in (401, 403):
            raise IntegrationError(
                "Web of Science API key is invalid or unauthorized", status_code=401
            )
        if response.status_code == 404:
            raise IntegrationError("Web of Science record not found", status_code=404)
        if response.status_code == 429:
            raise IntegrationError("Web of Science rate limit exceeded", status_code=429)
        if response.status_code >= 400:
            raise IntegrationError(
                f"Web of Science returned HTTP {response.status_code}", status_code=502
            )

        try:
            return response.json()
        except ValueError:
            raise IntegrationError("Web of Science returned invalid JSON", status_code=502)

    # --- Search (base interface) ---------------------------------------------

    def search(
        self,
        query: str = "",
        page: int = 1,
        page_size: int = 10,
        author: Optional[str] = None,
        title: Optional[str] = None,
        doi: Optional[str] = None,
    ) -> dict:
        params = {"q": self._build_query(query, title, author, doi), "limit": page_size, "page": page}
        data = self._get_json(
            f"{self.base_url}/documents", params=params, headers=self._headers()
        )
        metadata = data.get("metadata") or {}
        total = int(metadata.get("total", 0))
        hits = data.get("hits") or []
        return {"total": total, "results": [self._normalize(hit) for hit in hits]}

    def get_by_identifier(self, identifier: str) -> ExternalPublicationResult:
        return self.get_publication(identifier)

    # --- Publication retrieval ------------------------------------------------

    def get_publication(self, record_id: str) -> ExternalPublicationResult:
        data = self._get_json(
            f"{self.base_url}/documents/{record_id}", headers=self._headers()
        )
        return self._normalize(data)

    # --- Researcher retrieval -------------------------------------------------

    def get_researcher(self, researcher_id: str):
        raise IntegrationError(
            "Web of Science researcher retrieval is not supported by the configured API",
            status_code=501,
        )

    # --- Helpers --------------------------------------------------------------

    @staticmethod
    def _build_query(query, title, author, doi) -> str:
        if doi:
            return f"DO=({doi})"
        if title:
            return f"TI=({title})"
        if author:
            return f"AU=({author})"
        return query or ""

    def _normalize(self, doc: dict) -> ExternalPublicationResult:
        uid = doc.get("uid")
        identifiers = doc.get("identifiers") or {}
        doi = normalize_doi(identifiers.get("doi"))
        source = doc.get("source") or {}
        issn = source.get("issn") or identifiers.get("issn")
        eissn = source.get("eissn") or identifiers.get("eissn")
        links = doc.get("links") or {}
        publication_date, publication_year = self._extract_date(source)

        return ExternalPublicationResult(
            source=self.source,
            source_record_id=uid,
            title=doc.get("title"),
            abstract=None,
            authors=self._parse_authors(doc.get("names")),
            journal=source.get("sourceTitle"),
            conference=None,
            publisher=source.get("publisher"),
            doi=doi,
            publication_date=publication_date,
            publication_year=publication_year,
            url=links.get("record"),
            indexing=["Web of Science"],
            external_identifiers=self._identifiers(uid, doi, issn, eissn),
            raw_metadata=doc,
        )

    def _parse_authors(self, names_obj) -> list[ExternalAuthor]:
        authors: list[ExternalAuthor] = []
        author_list = (names_obj or {}).get("authors") or []
        for position, author in enumerate(author_list, start=1):
            if not isinstance(author, dict):
                continue
            standard = author.get("wosStandard") or {}
            given = standard.get("firstName")
            family = standard.get("lastName")
            name = author.get("displayName") or " ".join(filter(None, [given, family]))
            addresses = author.get("addresses") or []
            affiliations = [
                entry.get("address")
                for entry in addresses
                if isinstance(entry, dict) and entry.get("address")
            ]
            authors.append(
                ExternalAuthor(
                    name=name or None,
                    given_name=given,
                    family_name=family,
                    affiliation=affiliations or None,
                    author_position=position,
                    orcid_id=author.get("orcid"),
                    web_of_science_researcher_id=author.get("researcherId"),
                )
            )
        return authors

    @staticmethod
    def _identifiers(uid, doi, issn, eissn) -> dict:
        identifiers = {}
        if uid:
            identifiers["ut"] = uid
        if doi:
            identifiers["doi"] = doi
        if issn:
            identifiers["issn"] = issn
        if eissn:
            identifiers["eissn"] = eissn
        return identifiers

    @classmethod
    def _extract_date(cls, source: dict):
        year = source.get("publishYear")
        if not year:
            return None, None
        year_int = int(year)

        month_raw = source.get("publishMonth")
        month = None
        if month_raw is not None:
            if isinstance(month_raw, int) or str(month_raw).isdigit():
                month = int(month_raw)
            else:
                month = _MONTHS.get(str(month_raw).lower()[:3])

        day_raw = source.get("publishDay")
        day = int(day_raw) if day_raw is not None and str(day_raw).isdigit() else None

        if month and day:
            return f"{year_int:04d}-{month:02d}-{day:02d}", year_int
        if month:
            return f"{year_int:04d}-{month:02d}", year_int
        return f"{year_int:04d}", year_int
