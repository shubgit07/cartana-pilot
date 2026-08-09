from fastapi import APIRouter

from app.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, object]:
    """Liveness + provider configuration report.

    Exposes which LLM/embedding providers are configured and whether their
    credentials resolved — without leaking any secret values (booleans only).
    Useful for spotting stale or missing configuration at a glance.
    """
    settings = get_settings()
    return {
        "status": "ok",
        "providers": {
            "llm": settings.llm_provider,
            "embedding": settings.embedding_provider,
        },
        "credentials": {
            "cloudflare_configured": bool(
                settings.cloudflare_account_id and settings.cloudflare_api_token
            ),
            "gemini_configured": bool(settings.gemini_api_key),
            "groq_configured": bool(settings.groq_api_key),
            "cerebras_configured": bool(settings.cerebras_api_key),
            "fireworks_configured": bool(settings.fireworks_api_key),
        },
    }
