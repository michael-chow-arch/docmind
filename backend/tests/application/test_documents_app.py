from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, Mock, patch

from app.application.documents_app import DocumentsApp
from app.application.documents_answer_app import DocumentsAnswerApp
from app.domains.documents.vector_repo import VectorRepo


class TestDocumentsApp:
    @pytest.mark.asyncio
    async def test_search_uses_instance_db_and_vector_repo(self):
        mock_db = AsyncMock()
        app = DocumentsApp(mock_db)

        mock_provider = Mock()
        mock_provider.embed_one.return_value = [0.1] * 384

        mock_repo = AsyncMock()
        mock_repo.search_similar = AsyncMock(return_value=[])

        with patch("app.application.documents_app.get_embedding_provider", return_value=mock_provider):
            with patch("app.application.documents_app.VectorRepo", return_value=mock_repo):
                await app.search("test query", document_id=1, top_k=5)

        VectorRepo.assert_called_once_with(mock_db)

    @pytest.mark.asyncio
    async def test_search_propagates_exception(self):
        mock_db = AsyncMock()
        app = DocumentsApp(mock_db)

        mock_provider = Mock()
        mock_provider.embed_one.side_effect = ValueError("Embedding failed")

        with patch("app.application.documents_app.get_embedding_provider", return_value=mock_provider):
            with pytest.raises(ValueError, match="Embedding failed"):
                await app.search("test query")


class TestDocumentsAnswerApp:
    @pytest.mark.asyncio
    async def test_no_chunks_returns_early(self):
        mock_db = AsyncMock()
        app = DocumentsAnswerApp(mock_db)

        with patch.object(app.documents_app, "search", new_callable=AsyncMock, return_value=[]):
            result = await app.answer(
                question="test",
                document_id=1,
                top_k=5,
                session_id=None,
                conversation_id=None,
                user_id="user1",
            )

        assert result["answer"]["summary"] == "I don't have enough information to answer this question based on the available documents."
        assert result["citations"] == []
        assert result["session"]["session_id"] == ""
        assert result["session"]["is_follow_up"] is False
        assert result["conversation"] is None
