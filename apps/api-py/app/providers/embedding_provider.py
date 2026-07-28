from typing import Protocol


class EmbeddingProvider(Protocol):
    """Swappable embedding provider interface.

    The output dimension must match settings.embedding_dim (768), matching
    the pgvector column width agreed for the Chunk table.
    """

    async def embed(self, texts: list[str]) -> list[list[float]]:
        ...
