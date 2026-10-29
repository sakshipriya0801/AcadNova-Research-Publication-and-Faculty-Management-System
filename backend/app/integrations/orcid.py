"""ORCID public API client."""

from typing import Optional

from app.config.settings import get_settings
from app.integrations.base import BaseIntegrationClient, IntegrationError
from app.schemas.external_publication import ExternalAuthor, ExternalPublicationResult
from app.schemas.orcid import OrcidEmployment, OrcidProfileResponse
from app.services.publication_service import normalize_doi
from app.utils.author_matching import normalize_orcid


class OrcidClient(BaseIntegrationClient):
    source = "orcid"

    def __init__(self):
        settings = get_settings()
        self.base_url = settings.orcid_api_url.rstrip("/")
        self.timeout = settings.orcid_timeout_seconds
        self.client_id = settings.orcid_client_id
        self.client_secret = settings.orcid_client_secret

    def _headers(self) -> dict:
        return {"Accept": "application/json"}

    def _require_orcid(self, orcid) -> str:
        normalized = normalize_orcid(orcid)
        if not normalized:
            raise IntegrationError("Invalid ORCID identifier", status_code=400)
        return normalized

    # --- Profile / researchers -------------------------------------------------

    def get_profile(self, orcid: str) -> OrcidProfileResponse:
        normalized = self._require_orcid(orcid)
        data = self._get_json(
            f"{self.base_url}/{normalized}/record", headers=self._headers()
        )
        return self._normalize_profile(data)

    def search_researchers(
        self, query: str, page: int = 1, page_size: int = 10
    ) -> dict:
        params = {"q": query, "start": (page - 1) * page_size, "rows": page_size}
        data = self._get_json(
            f"{self.base_url}/search", params=params, headers=self._headers()
        )
        total = int(data.get("num-found", 0))
        results = [
            self._normalize_search_result(item) for item in (data.get("result") or [])
        ]
        return {"total": total, "results": results}

    # --- Works -----------------------------------------------------------------

    def get_works(self, orcid: str, page: int = 1, page_size: int = 10) -> dict:
        normalized = self._require_orcid(orcid)
        data = self._get_json(
            f"{self.base_url}/{normalized}/works", headers=self._headers()
        )
        summaries = []
        for group in data.get("group") or []:
            summaries.extend(group.get("work-summary") or [])

        total = len(summaries)
        start = (page - 1) * page_size
        page_items = summaries[start : start + page_size]
        results = [
            self._normalize_work_summary(normalized, item) for item in page_items
        ]
        return {"total": total, "results": results}

    def get_work(self, orcid: str, put_code: str) -> ExternalPublicationResult:
        normalized = self._require_orcid(orcid)
        data = self._get_json(
            f"{self.base_url}/{normalized}/work/{put_code}", headers=self._headers()
        )
        return self._normalize_work(normalized, data)

    # --- Normalization ---------------------------------------------------------

    def _normalize_profile(self, data: dict) -> OrcidProfileResponse:
        orcid_id = normalize_orcid((data.get("orcid-identifier") or {}).get("path"))
        person = data.get("person") or {}
        name = person.get("name") or {}

        emails = [
            entry.get("email")
            for entry in (person.get("emails") or {}).get("email") or []
            if isinstance(entry, dict) and entry.get("email")
        ]

        employments = []
        activities = data.get("activities-summary") or {}
        for group in (activities.get("employments") or {}).get("affiliation-group") or []:
            for summary in group.get("summaries") or []:
                employments.append(
                    OrcidEmployment(
                        organization=(summary.get("organization") or {}).get("name"),
                        department=summary.get("department-name"),
                        role_title=summary.get("role-title"),
                        start_year=self._year(summary.get("start-date")),
                        end_year=self._year(summary.get("end-date")),
                    )
                )

        identifiers = {}
        for entry in (
            (person.get("external-identifiers") or {}).get("external-identifier") or []
        ):
            if (
                isinstance(entry, dict)
                and entry.get("external-id-type")
                and entry.get("external-id-value")
            ):
                identifiers[entry["external-id-type"]] = entry["external-id-value"]

        return OrcidProfileResponse(
            orcid_id=orcid_id or "",
            given_name=(name.get("given-names") or {}).get("value"),
            family_name=(name.get("family-name") or {}).get("value"),
            credit_name=(name.get("credit-name") or {}).get("value"),
            biography=(person.get("biography") or {}).get("content"),
            emails=emails,
            employments=employments,
            researcher_identifiers=identifiers,
        )

    def _normalize_search_result(self, item: dict) -> OrcidProfileResponse:
        orcid_id = normalize_orcid((item.get("orcid-identifier") or {}).get("path"))
        name = (item.get("person") or {}).get("name") or {}
        return OrcidProfileResponse(
            orcid_id=orcid_id or "",
            given_name=(name.get("given-names") or {}).get("value"),
            family_name=(name.get("family-name") or {}).get("value"),
            credit_name=(name.get("credit-name") or {}).get("value"),
        )

    def _normalize_work_summary(
        self, orcid: str, summary: dict
    ) -> ExternalPublicationResult:
        put_code = summary.get("put-code")
        return ExternalPublicationResult(
            source=self.source,
            source_record_id=str(put_code) if put_code else None,
            title=((summary.get("title") or {}).get("title") or {}).get("value"),
            abstract=None,
            authors=[],
            journal=(summary.get("journal-title") or {}).get("value"),
            conference=None,
            publisher=None,
            doi=self._extract_doi(summary),
            publication_date=self._extract_work_date(summary.get("publication-date")),
            publication_year=self._year(summary.get("publication-date")),
            url=(summary.get("url") or {}).get("value"),
            indexing=[],
            external_identifiers={"orcid": orcid, "put_code": str(put_code)}
            if put_code
            else {"orcid": orcid},
            raw_metadata=summary,
        )

    def _normalize_work(self, orcid: str, data: dict) -> ExternalPublicationResult:
        put_code = data.get("put-code")
        authors = []
        contributors = ((data.get("contributors") or {}).get("contributor")) or []
        for position, contributor in enumerate(contributors, start=1):
            if not isinstance(contributor, dict):
                continue
            authors.append(
                ExternalAuthor(
                    name=(contributor.get("credit-name") or {}).get("value"),
                    orcid_id=normalize_orcid(
                        (contributor.get("contributor-orcid") or {}).get("path")
                    ),
                    author_position=position,
                )
            )

        return ExternalPublicationResult(
            source=self.source,
            source_record_id=str(put_code) if put_code else None,
            title=((data.get("title") or {}).get("title") or {}).get("value"),
            abstract=data.get("short-description"),
            authors=authors,
            journal=(data.get("journal-title") or {}).get("value"),
            conference=None,
            publisher=None,
            doi=self._extract_doi(data),
            publication_date=self._extract_work_date(data.get("publication-date")),
            publication_year=self._year(data.get("publication-date")),
            url=(data.get("url") or {}).get("value"),
            indexing=[],
            external_identifiers={"orcid": orcid, "put_code": str(put_code)}
            if put_code
            else {"orcid": orcid},
            raw_metadata=data,
        )

    @staticmethod
    def _extract_doi(data: dict) -> Optional[str]:
        for entry in ((data.get("external-ids") or {}).get("external-id")) or []:
            if isinstance(entry, dict) and entry.get("external-id-type") == "doi":
                return normalize_doi(entry.get("external-id-value"))
        return None

    @staticmethod
    def _year(date_obj) -> Optional[int]:
        if not date_obj:
            return None
        value = (date_obj.get("year") or {}).get("value")
        return int(value) if value else None

    @classmethod
    def _extract_work_date(cls, date_obj) -> Optional[str]:
        if not date_obj:
            return None
        year = (date_obj.get("year") or {}).get("value")
        month = (date_obj.get("month") or {}).get("value")
        day = (date_obj.get("day") or {}).get("value")
        if not year:
            return None
        if month and day:
            return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
        if month:
            return f"{int(year):04d}-{int(month):02d}"
        return f"{int(year):04d}"
