"""Shared test configuration.

Environment variables are set BEFORE the app is imported so the cached
Settings resolve to an isolated test database rather than the real one.
"""

import os
import shutil

os.environ.setdefault("MONGODB_URI", "mongodb://localhost:27017")
os.environ["MONGODB_DATABASE"] = "research_faculty_db_test"
os.environ["APP_ENV"] = "test"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-tests-only-0123456789"
os.environ["SCOPUS_API_KEY"] = "test-scopus-api-key"
os.environ["WEB_OF_SCIENCE_API_KEY"] = "test-wos-api-key"
os.environ["DOCUMENT_STORAGE_DIR"] = "/tmp/opencode/test_documents"
# Existing tests register faculty and log in immediately; disable approval so
# those flows stay green. Approval-specific tests re-enable it explicitly.
os.environ["REQUIRE_REGISTRATION_APPROVAL"] = "false"

import pytest
from fastapi.testclient import TestClient

from app.database import mongodb
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def _cleanup_test_database():
    """Ensure an isolated test database, and drop it after all tests have run."""
    mongodb.init_mongodb()
    if mongodb.check_database_connection():
        mongodb.get_database().client.drop_database("research_faculty_db_test")
    yield
    mongodb.init_mongodb()
    if mongodb.check_database_connection():
        db = mongodb.get_database()
        db.client.drop_database(db.name)
    mongodb.close_mongodb()
    shutil.rmtree("/tmp/opencode/test_documents", ignore_errors=True)


@pytest.fixture
def client():
    """A TestClient whose lifespan initialises and later closes MongoDB."""
    with TestClient(app) as test_client:
        yield test_client
