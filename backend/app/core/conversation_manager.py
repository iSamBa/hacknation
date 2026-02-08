"""Manage active ElevenLabs conversations."""

import logging
import uuid

logger = logging.getLogger(__name__)


class ConversationManager:
    """Track active ElevenLabs conversations for audio routing."""

    def __init__(self):
        # Map booking_id -> ElevenLabsConversation instance
        self._active_conversations: dict[uuid.UUID, any] = {}

    def register(self, booking_id: uuid.UUID, conversation) -> None:
        """Register an active conversation."""
        self._active_conversations[booking_id] = conversation
        logger.info("Registered conversation for booking %s", booking_id)

    def unregister(self, booking_id: uuid.UUID) -> None:
        """Unregister a conversation when it ends."""
        if booking_id in self._active_conversations:
            del self._active_conversations[booking_id]
            logger.info("Unregistered conversation for booking %s", booking_id)

    def get(self, booking_id: uuid.UUID):
        """Get the active conversation for a booking."""
        return self._active_conversations.get(booking_id)

    def is_active(self, booking_id: uuid.UUID) -> bool:
        """Check if there's an active conversation for a booking."""
        return booking_id in self._active_conversations


# Global conversation manager
conversation_manager = ConversationManager()
