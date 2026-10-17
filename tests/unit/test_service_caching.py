
from unittest.mock import Mock

from services import conversation_service
from services import document_service


def test_conversation_cache_hit(monkeypatch):
    service = conversation_service.ConversationService()
    db = Mock()

    cached_result = {
        "data": [],
        "meta": {"page": 1, "limit": 20, "total": 0},
    }

    def fake_cache(key, ttl, fetch_fn):
        assert key == "conversations:user-123:1:20"
        assert ttl == 120
        return cached_result

    monkeypatch.setattr(
        conversation_service,
        "cache_get_or_set",
        fake_cache,
    )

    result = service.list_conversations(
        db=db,
        user_id="user-123",
    )

    assert result == cached_result
    db.execute.assert_not_called()


def test_conversation_cache_invalidation(monkeypatch):
    deleted = []

    monkeypatch.setattr(
        conversation_service,
        "cache_delete_pattern",
        deleted.append,
    )

    service = conversation_service.ConversationService()

    service.invalidate_conversation_cache("user-123")

    assert deleted == ["conversations:user-123:*"]


def test_document_cache_hit_for_owner(monkeypatch):
    service = document_service.DocumentService()
    db = Mock()

    cached_document = {
        "id": "doc-123",
        "user_id": "user-123",
        "title": "Cached document",
        "status": "ready",
        "deleted_at": None,
    }

    def fake_cache(key, ttl, fetch_fn):
        assert key == "doc:doc-123"
        assert ttl == 600
        return cached_document

    monkeypatch.setattr(
        document_service,
        "cache_get_or_set",
        fake_cache,
    )

    result = service.get_document_metadata(
        db=db,
        document_id="doc-123",
        user_id="user-123",
    )

    assert result["title"] == "Cached document"
    db.execute.assert_not_called()


def test_document_cache_invalidation(monkeypatch):
    deleted = []

    monkeypatch.setattr(
        document_service,
        "cache_delete",
        deleted.append,
    )

    service = document_service.DocumentService()

    service.invalidate_document_cache("doc-123")

    assert deleted == ["doc:doc-123"]
