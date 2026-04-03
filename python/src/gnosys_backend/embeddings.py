"""
Embeddings provider abstraction for Gnosys.

Supports local (sentence-transformers) and OpenAI embeddings providers.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any, Protocol

import numpy as np

from gnosys_backend.config import AppConfig


class EmbeddingsProvider(ABC):
    """Abstract base class for embeddings providers."""

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        pass

    @abstractmethod
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of texts."""
        pass

    @abstractmethod
    def get_dimension(self) -> int:
        """Return the embedding dimension."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available/initialized."""
        pass


class LocalEmbeddingsProvider(EmbeddingsProvider):
    """Local embeddings using sentence-transformers."""

    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._model = None
        self._dimension = config.embeddings.dimension

    def _load_model(self) -> Any:
        """Lazy load the sentence-transformers model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                model_name = self._config.embeddings.model
                self._model = SentenceTransformer(model_name)
                self._dimension = self._model.get_sentence_embedding_dimension()
            except ImportError as e:
                raise RuntimeError(
                    "sentence-transformers not installed. "
                    "Install with: pip install sentence-transformers"
                ) from e
            except Exception as e:
                raise RuntimeError(f"Failed to load local embeddings model: {e}") from e
        return self._model

    def embed(self, text: str) -> list[float]:
        model = self._load_model()
        embedding = model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self._load_model()
        embeddings = model.encode(
            texts,
            batch_size=self._config.embeddings.batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return embeddings.tolist()

    def get_dimension(self) -> int:
        # Try to get actual dimension if model loaded, otherwise use config
        if self._model is not None:
            return self._model.get_sentence_embedding_dimension()
        return self._dimension

    def is_available(self) -> bool:
        try:
            self._load_model()
            return True
        except Exception:
            return False


class OpenAIEmbeddingsProvider(EmbeddingsProvider):
    """OpenAI embeddings provider."""

    # Dimension mapping for OpenAI embedding models
    OPENAI_MODEL_DIMENSIONS = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
    }

    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._client = None
        # Set dimension based on configured model, default to 1536
        model = self._config.embeddings.openai_model
        self._dimension = self.OPENAI_MODEL_DIMENSIONS.get(model, 1536)

    def _get_client(self) -> Any:
        """Lazy load OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI

                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    raise RuntimeError(
                        "OPENAI_API_KEY not set. Set it in environment or config."
                    )
                self._client = OpenAI(api_key=api_key)
            except ImportError as e:
                raise RuntimeError(
                    "openai package not installed. Install with: pip install openai"
                ) from e
        return self._client

    def embed(self, text: str) -> list[float]:
        client = self._get_client()
        model = self._config.embeddings.openai_model
        response = client.embeddings.create(model=model, input=text)
        embedding = response.data[0].embedding
        self._dimension = len(embedding)
        return embedding

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        client = self._get_client()
        model = self._config.embeddings.openai_model
        # OpenAI has a batch limit of 2048 inputs per request
        all_embeddings = []
        for i in range(0, len(texts), 2048):
            batch = texts[i : i + 2048]
            response = client.embeddings.create(model=model, input=batch)
            all_embeddings.extend([item.embedding for item in response.data])
        if all_embeddings:
            self._dimension = len(all_embeddings[0])
        return all_embeddings

    def get_dimension(self) -> int:
        return self._dimension

    def is_available(self) -> bool:
        try:
            client = self._get_client()
            # Quick check by embedding empty string
            client.embeddings.create(
                model=self._config.embeddings.openai_model, input="test"
            )
            return True
        except Exception:
            return False


class DisabledEmbeddingsProvider(EmbeddingsProvider):
    """Disabled provider that returns zero vectors."""

    def __init__(self, dimension: int = 384) -> None:
        self._dimension = dimension

    def embed(self, text: str) -> list[float]:
        return [0.0] * self._dimension

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * self._dimension for _ in texts]

    def get_dimension(self) -> int:
        return self._dimension

    def is_available(self) -> bool:
        return False


def create_embeddings_provider(config: AppConfig) -> EmbeddingsProvider:
    """Factory function to create the appropriate embeddings provider."""
    provider = config.embeddings.provider.lower()

    if provider == "local":
        return LocalEmbeddingsProvider(config)
    elif provider == "openai":
        return OpenAIEmbeddingsProvider(config)
    elif provider == "disabled":
        return DisabledEmbeddingsProvider(config.embeddings.dimension)
    else:
        raise ValueError(f"Unknown embeddings provider: {provider}")
