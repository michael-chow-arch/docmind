from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, Mock

from sqlalchemy import text

from app.domains.documents.vector_repo import VectorRepo


class TestVectorRepoSQLInjection:
    @pytest.mark.asyncio
    async def test_search_similar_uses_parameterized_query(self):
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.mappings.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = VectorRepo(mock_session)
        query_embedding = [0.1] * 384

        await repo.search_similar(query_embedding, document_id=123, k=5)

        assert mock_session.execute.called
        call_args = mock_session.execute.call_args
        sql_arg = call_args[0][0]
        assert isinstance(sql_arg, text)
        sql_str = str(sql_arg)
        assert "{where_sql}" not in sql_str
        assert ":doc_id" in sql_str
        assert len(call_args[0]) >= 2
        params = call_args[0][1]
        assert isinstance(params, dict)
        assert params.get("doc_id") == 123

    @pytest.mark.asyncio
    async def test_search_similar_with_none_document_id(self):
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.mappings.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = VectorRepo(mock_session)
        query_embedding = [0.1] * 384

        await repo.search_similar(query_embedding, document_id=None, k=5)

        call_args = mock_session.execute.call_args
        params = call_args[0][1]
        assert "doc_id" not in params
        assert "q" in params and "k" in params

    @pytest.mark.asyncio
    async def test_search_similar_injection_attempt_blocked(self):
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.mappings.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = VectorRepo(mock_session)
        query_embedding = [0.1] * 384

        await repo.search_similar(query_embedding, document_id=999, k=5)

        call_args = mock_session.execute.call_args
        sql_arg = call_args[0][0]
        params = call_args[0][1]
        sql_str = str(sql_arg)
        assert "WHERE" in sql_str and "document_id = :doc_id" in sql_str
        assert params.get("doc_id") == 999
        assert "{where_sql}" not in sql_str and "999" not in sql_str

    @pytest.mark.asyncio
    async def test_search_similar_both_paths_parameterized(self):
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.mappings.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = VectorRepo(mock_session)
        query_embedding = [0.1] * 384

        await repo.search_similar(query_embedding, document_id=None, k=5)
        sql_none = str(mock_session.execute.call_args[0][0])
        params_none = mock_session.execute.call_args[0][1]

        mock_session.reset_mock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        await repo.search_similar(query_embedding, document_id=456, k=5)
        sql_with_id = str(mock_session.execute.call_args[0][0])
        params_with_id = mock_session.execute.call_args[0][1]

        assert ":q" in sql_none and ":k" in sql_none
        assert ":q" in sql_with_id and ":k" in sql_with_id and ":doc_id" in sql_with_id
        assert "456" not in sql_with_id
        assert isinstance(params_none, dict) and isinstance(params_with_id, dict)
