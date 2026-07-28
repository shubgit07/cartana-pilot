from typing import Optional, Protocol


class AIProvider(Protocol):
    """Swappable LLM generation provider interface.

    Mirrors the Node AIProvider interface. Concrete providers (stub,
    cloudflare, fireworks) are implemented alongside the features that use
    them (extraction, chat, audit).
    """

    async def generate(self, prompt: str, *, system: Optional[str] = None) -> str:
        ...
