"""Scopus / Elsevier API client."""

from typing import Optional

import httpx

from app.config.settings import get_settings
from app.integrations.base import BaseIntegrationClient, IntegrationError
from app.schemas.external_publication import ExternalAuthor, ExternalPublicationResult
from app.schemas.scopus import ScopusAuthorResponse
from app.services.publication_service import normalize_doi


class ScopusClient(BaseIntegrationClient):
    source = "scopus"

    def __init__(self):
        settings = get_settings()
        self.base_url = settings.scopus_api_url.rstrip("/")
        self.timeout = settings.scopus_timeout_seconds
        self.api_key = settings.scopus_api_key

    def _headers(self) -> dict:
        if not self.api_key:
            raise IntegrationError(
                "Scopus API key is not configured", status_code=503
            )
        return {"X-ELS-APIKey": self.api_key, "Accept": "application/json"}

    def _get_json(self, url, params=None, headers=None):
        try:
            response = httpx.get(url, params=params, headers=headers, timeout=self.timeout)
        except httpx.TimeoutException:
            raise IntegrationError("Scopus request timed out", status_code=504)
        except httpx.HTTPError as exc:
            raise IntegrationError(f"Scopus request failed: {exc}", status_code=502)

        if response.status_code in (401, 403):
            raise IntegrationError(
                "Scopus API key is invalid or unauthorized", status_code=401
            )
        if response.status_code == 404:
            raise IntegrationError("Scopus record not found", status_code=404)
        if response.status_code == 429:
            raise IntegrationError("Scopus rate limit exceeded", status_code=429)
        if response.status_code >= 400:
            raise IntegrationError(
                f"Scopus returned HTTP {response.status_code}", status_code=502
            )

        try:
            return response.json()
        except ValueError:
            raise IntegrationError("Scopus returned invalid JSON", status_code=502)


    # --- Search (base interface) ---------------------------------------------

    def search(
        self,
        query: str = "",
        page: int = 1,
        page_size: int = 10,
        author: Optional[str] = None,
        title: Optional[str] = None,
        doi: Optional[str] = None,
        author_id: Optional[str] = None,
    ) -> dict:
        params = {
            "query": self._build_query(query, title, author, doi, author_id),
            "count": page_size,
            "start": (page - 1) * page_size,
        }
        data = self._get_json(
            f"{self.base_url}/search/scopus", params=params, headers=self._headers()
        )
        results = data.get("search-results") or {}
        total = int(results.get("opensearch:totalResults", 0))
        entries = results.get("entry") or []
        if isinstance(entries, dict):
            entries = [entries]
        return {
            "total": total,
            "results": [self._normalize_entry(entry) for entry in entries],
        }

    def get_by_identifier(self, identifier: str) -> ExternalPublicationResult:
        return self.get_publication(identifier)

    # --- Publication retrieval ------------------------------------------------

    def get_publication(self, record_id: str) -> ExternalPublicationResult:
        data = self._get_json(
            f"{self.base_url}/abstract/eid/{record_id}", headers=self._headers()
        )
        return self._normalize_abstract(data)

    # --- Author retrieval ------------------------------------------------------

    def get_author(self, author_id: str) -> ScopusAuthorResponse:
        data = self._get_json(
            f"{self.base_url}/author/author_id/{author_id}", headers=self._headers()
        )
        return self._normalize_author(data)

    # --- Helpers --------------------------------------------------------------

    @staticmethod
    def _build_query(query, title, author, doi, author_id=None) -> str:
        if doi:
            return f"DOI({doi})"
        if title:
            return f"TITLE({title})"
        if author_id:
            return f"AU-ID({author_id})"
        if author:
            return f"AUTH({author})"
        return query or ""

    def _normalize_entry(self, entry: dict) -> ExternalPublicationResult:
        eid = entry.get("eid")
        doi = normalize_doi(entry.get("prism:doi"))
        cover_date = entry.get("prism:coverDate")
        scopus_id = self._scopus_id(entry.get("dc:identifier"))
        return ExternalPublicationResult(
            source=self.source,
            source_record_id=eid,
            title=entry.get("dc:title"),
            abstract=entry.get("dc:description"),
            authors=self._parse_entry_authors(entry),
            journal=entry.get("prism:publicationName"),
            conference=None,
            publisher=None,
            doi=doi,
            publication_date=cover_date,
            publication_year=self._year_from_date(cover_date),
            url=entry.get("link")[0].get("@href") if entry.get("link") else None,
            indexing=["Scopus"],
            external_identifiers=self._identifiers(eid, doi, scopus_id),
            raw_metadata=entry,
        )

    def _normalize_abstract(self, data: dict) -> ExternalPublicationResult:
        response = data.get("abstracts-retrieval-response") or {}
        coredata = response.get("coredata") or {}
        eid = coredata.get("eid")
        doi = normalize_doi(coredata.get("prism:doi"))
        cover_date = coredata.get("prism:coverDate")
        scopus_id = self._scopus_id(coredata.get("dc:identifier")) or coredata.get(
            "scopus-id"
        )
        return ExternalPublicationResult(
            source=self.source,
            source_record_id=eid,
            title=coredata.get("dc:title"),
            abstract=coredata.get("dc:description"),
            authors=self._parse_abstract_authors(response.get("authors")),
            journal=coredata.get("prism:publicationName"),
            conference=None,
            publisher=None,
            doi=doi,
            publication_date=cover_date,
            publication_year=self._year_from_date(cover_date),
            url=None,
            indexing=["Scopus"],
            external_identifiers=self._identifiers(eid, doi, scopus_id),
            raw_metadata=data,
        )

    def _parse_entry_authors(self, entry: dict) -> list[ExternalAuthor]:
        authors: list[ExternalAuthor] = []
        author_list = entry.get("author")
        if author_list:
            for position, author in enumerate(author_list, start=1):
                if not isinstance(author, dict):
                    continue
                given = author.get("given-name")
                family = author.get("surname")
                name = " ".join(filter(None, [given, family])) or author.get("authname")
                authors.append(
                    ExternalAuthor(
                        name=name or None,
                        given_name=given,
                        family_name=family,
                        affiliation=self._affiliations(author.get("affiliation")),
                        author_position=position,
                        scopus_author_id=author.get("authid"),
                        orcid_id=author.get("orcid"),
                    )
                )
        else:
            creator = entry.get("dc:creator") or ""
            for position, name in enumerate(
                [n.strip() for n in creator.split(";") if n.strip()], start=1
            ):
                authors.append(ExternalAuthor(name=name, author_position=position))
        return authors

    def _parse_abstract_authors(self, authors_obj) -> list[ExternalAuthor]:
        authors: list[ExternalAuthor] = []
        author_list = (authors_obj or {}).get("author") or []
        for position, author in enumerate(author_list, start=1):
            if not isinstance(author, dict):
                continue
            preferred = author.get("preferred-name") or {}
            given = preferred.get("ce:given-name") or author.get("ce:given-name")
            family = preferred.get("ce:surname") or author.get("ce:surname")
            name = " ".join(filter(None, [given, family])) or author.get(
                "ce:indexed-name"
            )
            authors.append(
                ExternalAuthor(
                    name=name or None,
                    given_name=given,
                    family_name=family,
                    affiliation=self._affiliations(author.get("affiliation")),
                    author_position=position,
                    scopus_author_id=author.get("@auid") or author.get("authid"),
                    orcid_id=author.get("orcid"),
                )
            )
        return authors

    @staticmethod
    def _affiliations(affiliation):
        if not affiliation:
            return None
        items = affiliation if isinstance(affiliation, list) else [affiliation]
        names = [
            item.get("affilname")
            for item in items
            if isinstance(item, dict) and item.get("affilname")
        ]
        return names or None

    @staticmethod
    def _scopus_id(identifier) -> Optional[str]:
        if not identifier:
            return None
        value = str(identifier)
        if value.startswith("SCOPUS_ID:"):
            return value[len("SCOPUS_ID:"):]
        return value

    @staticmethod
    def _identifiers(eid, doi, scopus_id) -> dict:
        identifiers = {}
        if eid:
            identifiers["eid"] = eid
        if doi:
            identifiers["doi"] = doi
        if scopus_id:
            identifiers["scopus_id"] = scopus_id
        return identifiers

    @staticmethod
    def _year_from_date(cover_date) -> Optional[int]:
        if not cover_date:
            return None
        value = str(cover_date)[:4]
        return int(value) if value.isdigit() else None

    def _normalize_author(self, data: dict) -> ScopusAuthorResponse:
        response = data.get("author-retrieval-response") or []
        author = response[0].get("author") if response else {}
        if not author:
            author = response.get("author") if isinstance(response, dict) else {}
        name = author.get("author-name") or {}
        subject_areas = [
            sa.get("$") for sa in (author.get("subject-area") or []) if isinstance(sa, dict) and sa.get("$")
        ]
        return ScopusAuthorResponse(
            author_id=author.get("@authid") or author.get("eid"),
            given_name=name.get("given-name"),
            family_name=name.get("surname"),
            name=" ".join(filter(None, [name.get("given-name"), name.get("surname")])) or None,
            affiliations=[],
            subject_areas=subject_areas,
        )
