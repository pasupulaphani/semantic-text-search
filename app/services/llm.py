import logging
import re
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
SUMMARISE_SYSTEM_PROMPT = "You are a concise document analyst. Summarise the provided document in 2–4 sentences, highlighting its type, key facts, and relevance for KYC/compliance purposes."


async def summarise_document(title: str, content: str) -> str:
    logger.debug("Summarising document: %s", title)
    if settings.openai_api_key:
        try:
            summary = await _summarise_openai(title, content)
            logger.debug("OpenAI summary complete for %s", title)
            return summary
        except Exception as exc:
            logger.warning(
                "OpenAI summarisation failed for %s: %s. Falling back locally.",
                title,
                exc,
            )
    summary = _summarise_local(title, content)
    logger.debug("Local summary complete for %s", title)
    return summary


async def _summarise_openai(title: str, content: str) -> str:
    from openai import AsyncOpenAI

    logger.debug("Calling OpenAI for %s", title)
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.chat.completions.create(
        model=settings.openai_chat_model,
        messages=[
            {"role": "system", "content": SUMMARISE_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Title: {title }\n\nContent:\n{content [:4000 ]}",
            },
        ],
        temperature=0.2,
        max_tokens=256,
    )
    message = response.choices[0].message.content or ""
    logger.debug("OpenAI returned %d chars for %s", len(message), title)
    return message


def _summarise_local(title: str, content: str) -> str:
    logger.debug("Building local summary for %s", title)
    sentences = re.split("(?<=[.!?])\\s+", content.strip())
    excerpt = " ".join((s for s in sentences[:3] if s.strip()))
    if excerpt:
        summary = f"{title }. {excerpt }"
    else:
        summary = title
    logger.debug("Local summary for %s is %d chars", title, len(summary))
    return summary
