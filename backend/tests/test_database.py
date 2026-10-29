"""MongoDB connection, insert/retrieve, index and shutdown tests."""

from fastapi.testclient import TestClient

from app.database import mongodb
from app.main import app


def test_database_connection_works():
    with TestClient(app):
        assert mongodb.check_database_connection() is True


def test_insert_and_retrieve_document():
    collection_name = "test_documents"
    with TestClient(app):
        collection = mongodb.get_collection(collection_name)
        inserted_id = collection.insert_one({"name": "probe", "value": 42}).inserted_id
        try:
            retrieved = collection.find_one({"_id": inserted_id})
            assert retrieved is not None
            assert retrieved["name"] == "probe"
            assert retrieved["value"] == 42
        finally:
            collection.drop()


def test_index_creation_does_not_fail():
    with TestClient(app):
        created = mongodb.create_indexes()
        assert "faculty" in created
        assert "publications" in created

        indexes = mongodb.get_collection("faculty").index_information()
        assert "employee_id_unique" in indexes
        assert "email_unique" in indexes


def test_shutdown_cleanly():
    with TestClient(app):
        assert mongodb.check_database_connection() is True

    # After lifespan shutdown the client is closed and no longer reachable.
    assert mongodb.check_database_connection() is False
