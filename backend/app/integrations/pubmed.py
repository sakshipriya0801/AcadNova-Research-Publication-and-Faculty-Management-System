"""PubMed (NCBI E-utilities) client."""

import re
from typing import Optional

from app.config.settings import get_settings
from app.integrations.base import BaseIntegrationClient
from app.schemas.external_publication import ExternalAuthor, ExternalPublicationResult
from app.services.publication_service import normalize_doi

_MONTHS = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}


class PubMedClient(BaseIntegrationClient):
    source = "pubmed"

    def __init__(self):
        settings = get_settings()
        self.base_url = settings.pubmed_api_url.rstrip("/")
        self.timeout = settings.pubmed_timeout_seconds
        self.api_key = settings.pubmed_api_key
        self.email = settings.pubmed_email

    def _common_params(self) -> dict:
        params: dict = {"db": "pubmed", "retmode": "json"}
        if self.api_key:
            params["api_key"] = self.api_key
        if self.email:
            params["email"] = self.email
        return params

    def search(
        self,
        query: str = "",
        page: int = 1,
        page_size: int = 10,
        author: Optional[str] = None,
        title: Optional[str] = None,
        doi: Optional[str] = None,
    ) -> dict:
        params = self._common_params()
        params.update(
            {
                "term": self._build_term(query, author, title, doi),
                "retmax": page_size,
                "retstart": (page - 1) * page_size,
            }
        )
        data = self._get_json(f"{self.base_url}/esearch.fcgi", params)
        result = data.get("esearchresult") or {}
        total = int(result.get("count", 0))
        ids = result.get("idlist") or []

        results = self._summaries(ids) if ids else []
        return {"total": total, "results": results}

    def get_by_identifier(self, identifier: str) -> Optional[ExternalPublicationResult]:
        params = self._common_params()
        params["id"] = identifier
        data = self._get_json(f"{self.base_url}/esummary.fcgi", params)
        result = data.get("result") or {}
        uids = result.get("uids") or []
        if not uids:
            return None
        item = result.get(uids[0])
        if not item:
            return None
        return self._normalize(uids[0], item)

    def _summaries(self, ids) -> list[ExternalPublicationResult]:
        params = self._common_params()
        params["id"] = ",".join(str(i) for i in ids)
        data = self._get_json(f"{self.base_url}/esummary.fcgi", params)
        result = data.get("result") or {}
        uids = result.get("uids") or []
        records: list[ExternalPublicationResult] = []
        for uid in uids:
            item = result.get(uid)
            if item:
                records.append(self._normalize(uid, item))
        return records

    @staticmethod
    def _build_term(query, author, title, doi) -> str:
        if doi:
            return f"{doi}[DOI]"
        if title:
            return f"{title}[Title]"
        if author:
            return f"{author}[Author]"
        return query or ""

    def _normalize(self, pmid: str, item: dict) -> ExternalPublicationResult:
        authors: list[ExternalAuthor] = []
        for position, author in enumerate(item.get("authors") or [], start=1):
            authors.append(
                ExternalAuthor(name=author.get("name"), author_position=position)
            )

        doi = None
        for article_id in item.get("articleids") or []:
            if article_id.get("idtype") == "doi":
                doi = normalize_doi(article_id.get("value"))
                break

        pubdate = item.get("pubdate")
        publication_date, publication_year = self._extract_date(pubdate)

        return ExternalPublicationResult(
            source=self.source,
            source_record_id=str(pmid),
            title=item.get("title"),
            abstract=None,
            authors=authors,
            journal=item.get("fulljournalname") or item.get("source"),
            conference=None,
            publisher=None,
            doi=doi,
            publication_date=publication_date,
            publication_year=publication_year,
            url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            indexing=["PubMed"],
            external_identifiers={"pmid": str(pmid), **({"doi": doi} if doi else {})},
            raw_metadata=item,
        )

    @staticmethod
    def _extract_date(pubdate):
        if not pubdate:
            return None, None
        value = str(pubdate).strip()
        match = re.match(r"^(\d{4})(?:\s+([A-Za-z]{3}))?(?:\s+(\d{1,2}))?", value)
        if not match:
            year_match = re.search(r"\d{4}", value)
            if not year_match:
                return None, None
            year = int(year_match.group(0))
            return f"{year:04d}", year

        year = int(match.group(1))
        month = _MONTHS.get(match.group(2).lower()) if match.group(2) else None
        day = int(match.group(3)) if match.group(3) else None

        if month and day:
            return f"{year:04d}-{month:02d}-{day:02d}", year
        if month:
            return f"{year:04d}-{month:02d}", year
        return f"{year:04d}", year
