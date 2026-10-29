"""API response schema for the health endpoint."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    database: str
