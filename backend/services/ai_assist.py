import logging
from uuid import UUID

logger = logging.getLogger(__name__)


async def maybe_summarize(conversation_id: UUID) -> None:
    """
    Placeholder hook for future OpenAI/AI summary support.
    Currently logs and returns immediately.
    """
    logger.debug("AI assist stub invoked for conversation %s", conversation_id)
