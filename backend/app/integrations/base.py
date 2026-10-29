"""Common interface for external scholarly source clients."""

from typing import Any, Optional

import httpx


class IntegrationError(Exception):
    """Application-level error raised by integration clients.

    Carries a suggested HTTP status code so the service layer can translate it
    into a clean API response without exposing internal details.
    """

    def __init__(self, message: str, status_code: int = 502):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class BaseIntegrationClient:
    """Base class providing HTTP helpers and a common interface.

    Subclasses implement the operations they support (e.g. ``search`` /
    ``get_by_identifier`` for Crossref/PubMed, or profile/works retrieval for
    ORCID).
    """

    source: str = ""
    timeout: float = 10.0

    def search(self, *args, **kwargs):
        raise NotImplementedError(f"{self.source} does not support search")

    def get_by_identifier(self, identifier: str):
        raise NotImplementedError(
            f"{self.source} does not support get_by_identifier"
        )

    def _get_json(
        self, url: str, params: Optional[dict] = None, headers: Optional[dict] = None
    ) -> Any:
        try:
            response = httpx.get(url, params=params, headers=headers, timeout=self.timeout)
        except httpx.TimeoutException:
            raise IntegrationError(
                f"{self.source} request timed out", status_code=504
            )
        except httpx.HTTPError as exc:
            raise IntegrationError(
                f"{self.source} request failed: {exc}", status_code=502
            )

        if response.status_code == 429:
            raise IntegrationError(
                f"{self.source} rate limit exceeded", status_code=429
            )
        if response.status_code >= 400:
            raise IntegrationError(
                f"{self.source} returned HTTP {response.status_code}", status_code=502
            )

        try:
            return response.json()
        except ValueError:
            raise IntegrationError(
                f"{self.source} returned invalid JSON", status_code=502
            )
