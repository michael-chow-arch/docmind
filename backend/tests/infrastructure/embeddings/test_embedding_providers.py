from __future__ import annotations

import numpy as np
import pytest
from unittest.mock import Mock, patch

from app.infrastructure.embeddings.base import EmbeddingProvider
from app.infrastructure.embeddings.sbert import SBERTEmbeddingProvider
from app.infrastructure.embeddings.openai import OpenAIEmbeddingProvider


class TestEmbeddingProviderInterface:
    def test_base_class_is_abstract(self):
        with pytest.raises(TypeError):
            EmbeddingProvider()

    def test_base_class_has_both_methods(self):
        assert hasattr(EmbeddingProvider, "embed_many")
        assert hasattr(EmbeddingProvider, "embed_one")

    def test_sbert_implements_interface(self):
        assert hasattr(SBERTEmbeddingProvider, "embed_many")
        assert hasattr(SBERTEmbeddingProvider, "embed_one")
        with patch("app.infrastructure.embeddings.sbert.SentenceTransformer"):
            provider = SBERTEmbeddingProvider()
            assert isinstance(provider, EmbeddingProvider)

    def test_openai_implements_interface(self):
        assert hasattr(OpenAIEmbeddingProvider, "embed_many")
        assert hasattr(OpenAIEmbeddingProvider, "embed_one")
        with patch("app.infrastructure.embeddings.openai.OpenAI"):
            with patch("app.infrastructure.embeddings.openai.settings") as mock_settings:
                mock_settings.OPENAI_API_KEY = "test-key"
                mock_settings.OPENAI_BASE_URL = None
                mock_settings.OPENAI_EMBEDDING_MODEL = "test-model"
                provider = OpenAIEmbeddingProvider()
                assert isinstance(provider, EmbeddingProvider)


class TestSBERTEmbeddingProvider:
    @patch("app.infrastructure.embeddings.sbert.SentenceTransformer")
    def test_embed_one_delegates_to_embed_many(self, mock_transformer_class):
        mock_model = Mock()
        mock_model.encode.return_value = np.array([[0.1, 0.2, 0.3]])
        mock_transformer_class.return_value = mock_model

        provider = SBERTEmbeddingProvider()
        result = provider.embed_one("test text")

        mock_model.encode.assert_called_once_with(["test text"], normalize_embeddings=True)
        assert result == [0.1, 0.2, 0.3]

    @patch("app.infrastructure.embeddings.sbert.SentenceTransformer")
    def test_embed_many_works(self, mock_transformer_class):
        mock_model = Mock()
        mock_model.encode.return_value = np.array([[0.1, 0.2], [0.3, 0.4]])
        mock_transformer_class.return_value = mock_model

        provider = SBERTEmbeddingProvider()
        result = provider.embed_many(["text1", "text2"])

        mock_model.encode.assert_called_once_with(["text1", "text2"], normalize_embeddings=True)
        assert result == [[0.1, 0.2], [0.3, 0.4]]

    @patch("app.infrastructure.embeddings.sbert.SentenceTransformer")
    def test_embed_one_returns_single_vector(self, mock_transformer_class):
        mock_model = Mock()
        mock_model.encode.return_value = np.array([[0.1, 0.2, 0.3]])
        mock_transformer_class.return_value = mock_model

        provider = SBERTEmbeddingProvider()
        result = provider.embed_one("test")

        assert isinstance(result, list)
        assert all(isinstance(x, (int, float)) for x in result)
        assert len(result) == 3


class TestOpenAIEmbeddingProvider:
    @patch("app.infrastructure.embeddings.openai.OpenAI")
    @patch("app.infrastructure.embeddings.openai.settings")
    def test_embed_one_delegates_to_embed_many(self, mock_settings, mock_openai_class):
        mock_settings.OPENAI_API_KEY = "test-key"
        mock_settings.OPENAI_BASE_URL = None
        mock_settings.OPENAI_EMBEDDING_MODEL = "test-model"

        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1, 0.2, 0.3])]
        mock_client.embeddings.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        provider = OpenAIEmbeddingProvider()
        result = provider.embed_one("test text")

        mock_client.embeddings.create.assert_called_once_with(
            model="test-model", input=["test text"]
        )
        assert result == [0.1, 0.2, 0.3]

    @patch("app.infrastructure.embeddings.openai.OpenAI")
    @patch("app.infrastructure.embeddings.openai.settings")
    def test_embed_many_works(self, mock_settings, mock_openai_class):
        mock_settings.OPENAI_API_KEY = "test-key"
        mock_settings.OPENAI_BASE_URL = None
        mock_settings.OPENAI_EMBEDDING_MODEL = "test-model"

        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = [
            Mock(embedding=[0.1, 0.2]),
            Mock(embedding=[0.3, 0.4]),
        ]
        mock_client.embeddings.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        provider = OpenAIEmbeddingProvider()
        result = provider.embed_many(["text1", "text2"])

        mock_client.embeddings.create.assert_called_once_with(
            model="test-model", input=["text1", "text2"]
        )
        assert result == [[0.1, 0.2], [0.3, 0.4]]

    @patch("app.infrastructure.embeddings.openai.OpenAI")
    @patch("app.infrastructure.embeddings.openai.settings")
    def test_embed_one_returns_single_vector(self, mock_settings, mock_openai_class):
        mock_settings.OPENAI_API_KEY = "test-key"
        mock_settings.OPENAI_BASE_URL = None
        mock_settings.OPENAI_EMBEDDING_MODEL = "test-model"

        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1, 0.2, 0.3])]
        mock_client.embeddings.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        provider = OpenAIEmbeddingProvider()
        result = provider.embed_one("test")

        assert isinstance(result, list)
        assert all(isinstance(x, (int, float)) for x in result)
        assert len(result) == 3


class TestSearchPathIntegration:
    @pytest.mark.asyncio
    @patch("app.infrastructure.embeddings.sbert.SentenceTransformer")
    async def test_search_path_with_sbert(self, mock_transformer_class):
        from unittest.mock import AsyncMock

        from app.application.documents_app import DocumentsApp

        mock_model = Mock()
        mock_model.encode.return_value = np.array([[0.1] * 384])
        mock_transformer_class.return_value = mock_model

        mock_db = AsyncMock()
        mock_result = Mock()
        mock_result.mappings.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        app = DocumentsApp(mock_db)

        with patch("app.application.documents_app.get_embedding_provider") as mock_get_provider:
            provider = SBERTEmbeddingProvider()
            mock_get_provider.return_value = provider

            result = await app.search("test query", document_id=None, top_k=5)

            assert mock_model.encode.called
            assert result == []

    @pytest.mark.asyncio
    @patch("app.infrastructure.embeddings.openai.OpenAI")
    @patch("app.infrastructure.embeddings.openai.settings")
    async def test_search_path_with_openai(self, mock_settings, mock_openai_class):
        from unittest.mock import AsyncMock

        from app.application.documents_app import DocumentsApp

        mock_settings.OPENAI_API_KEY = "test-key"
        mock_settings.OPENAI_BASE_URL = None
        mock_settings.OPENAI_EMBEDDING_MODEL = "test-model"

        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1] * 384)]
        mock_client.embeddings.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        mock_db = AsyncMock()
        mock_result = Mock()
        mock_result.mappings.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        app = DocumentsApp(mock_db)

        with patch("app.application.documents_app.get_embedding_provider") as mock_get_provider:
            provider = OpenAIEmbeddingProvider()
            mock_get_provider.return_value = provider

            result = await app.search("test query", document_id=None, top_k=5)

            assert mock_client.embeddings.create.called
            assert result == []
