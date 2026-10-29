"""MongoDB configuration tests (local + MongoDB Atlas SRV).

These tests never connect to a real server: they verify that configuration is
loaded from environment variables, that both ``mongodb://`` and
``mongodb+srv://`` URIs are accepted, that the database layer reads the
configured URI/timeouts, and that credentials are never logged.
"""

import logging

import pytest
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

from app.config.settings import Settings, get_settings
from app.database import mongodb

_SRV_URI = (
    "mongodb+srv://atlasuser:TOP_SECRET_PW@cluster0.example.net/"
    "research_faculty_db?retryWrites=true&w=majority"
)


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


# --- Environment loading -----------------------------------------------------

def test_settings_defaults_to_local_uri(monkeypatch):
    for var in (
        "MONGODB_URI",
        "MONGODB_DATABASE",
        "MONGODB_CONNECT_TIMEOUT_MS",
        "MONGODB_SERVER_SELECTION_TIMEOUT_MS",
    ):
        monkeypatch.delenv(var, raising=False)
    settings = Settings(_env_file=None)
    assert settings.mongodb_uri.startswith("mongodb://")
    assert settings.mongodb_database
    assert settings.mongodb_connect_timeout_ms > 0
    assert settings.mongodb_server_selection_timeout_ms > 0


def test_settings_loads_local_uri_from_env(monkeypatch):
    monkeypatch.setenv("MONGODB_URI", "mongodb://127.0.0.1:27018")
    monkeypatch.setenv("MONGODB_DATABASE", "atlas_custom_db")
    monkeypatch.setenv("MONGODB_CONNECT_TIMEOUT_MS", "1111")
    monkeypatch.setenv("MONGODB_SERVER_SELECTION_TIMEOUT_MS", "2222")
    settings = get_settings()
    assert settings.mongodb_uri == "mongodb://127.0.0.1:27018"
    assert settings.mongodb_database == "atlas_custom_db"
    assert settings.mongodb_connect_timeout_ms == 1111
    assert settings.mongodb_server_selection_timeout_ms == 2222


def test_settings_loads_srv_uri_from_env(monkeypatch):
    monkeypatch.setenv("MONGODB_URI", _SRV_URI)
    monkeypatch.setenv("MONGODB_DATABASE", "research_faculty_db")
    settings = get_settings()
    assert settings.mongodb_uri.startswith("mongodb+srv://")
    assert settings.mongodb_uri == _SRV_URI
    assert settings.mongodb_database == "research_faculty_db"


# --- Driver accepts both schemes --------------------------------------------

def test_dnspython_available_for_srv():
    # mongodb+srv:// resolution requires dnspython.
    import dns.resolver  # noqa: F401


def test_pymongo_accepts_local_and_srv_uris():
    local = MongoClient("mongodb://localhost:27017", connect=False)
    srv = MongoClient(_SRV_URI, connect=False)
    try:
        assert local is not None and srv is not None
    finally:
        local.close()
        srv.close()


# --- Database layer reads the configured URI and never logs secrets ----------

def test_mongodb_layer_reads_config_and_never_logs_secret(monkeypatch, caplog):
    captured = {}

    class _FakeAdmin:
        def command(self, *args, **kwargs):
            raise ConnectionFailure("simulated failure")

    class _FakeClient:
        def __init__(self, uri, **kwargs):
            captured["uri"] = uri
            captured["kwargs"] = kwargs
            self.admin = _FakeAdmin()

        def __getitem__(self, name):
            captured["database"] = name
            return object()

        def close(self):
            pass

    monkeypatch.setenv("MONGODB_URI", _SRV_URI)
    monkeypatch.setenv("MONGODB_DATABASE", "research_faculty_db")
    monkeypatch.setenv("MONGODB_CONNECT_TIMEOUT_MS", "1234")
    monkeypatch.setenv("MONGODB_SERVER_SELECTION_TIMEOUT_MS", "2345")
    get_settings.cache_clear()
    monkeypatch.setattr(mongodb, "MongoClient", _FakeClient)

    original_client, original_database = mongodb._client, mongodb._database
    mongodb._client = None
    mongodb._database = None
    try:
        with caplog.at_level(logging.ERROR):
            mongodb.init_mongodb()

        assert captured["uri"] == _SRV_URI
        assert captured["database"] == "research_faculty_db"
        assert captured["kwargs"]["connectTimeoutMS"] == 1234
        assert captured["kwargs"]["serverSelectionTimeoutMS"] == 2345
        # Credentials / full URI must never appear in logs.
        assert "TOP_SECRET_PW" not in caplog.text
        assert _SRV_URI not in caplog.text
        # Unreachable client -> health must report disconnected.
        assert mongodb.check_database_connection() is False
    finally:
        mongodb._client = original_client
        mongodb._database = original_database
