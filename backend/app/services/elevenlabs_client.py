"""ElevenLabs WebSocket client for real-time agent conversations."""

import asyncio
import base64
import json
import logging
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

import websockets
from websockets.asyncio.client import ClientConnection

from app.config import settings

logger = logging.getLogger(__name__)

# Timeouts
CONNECTION_TIMEOUT = 30  # seconds
CONVERSATION_TIMEOUT = 300  # 5 minutes


class ConversationError(Exception):
    """Base exception for conversation errors."""


class ConversationTimeoutError(ConversationError):
    """Raised when conversation times out."""


class ConversationConnectionError(ConversationError):
    """Raised when WebSocket connection fails."""


class ElevenLabsConversation:
    """Manages a single ElevenLabs agent conversation via WebSocket.

    Connects to ElevenLabs WebSocket API, sends initial message with dynamic
    variables, and streams audio chunks and events back to the caller.
    """

    def __init__(
        self,
        conversation_id: str,
        booking_id: uuid.UUID,
        provider_id: uuid.UUID,
        dynamic_variables: dict[str, str],
    ):
        """Initialize conversation.

        Args:
            conversation_id: Unique ID for this conversation
            booking_id: Booking UUID
            provider_id: Provider UUID
            dynamic_variables: Variables to pass to agent (patient_name, etc.)
        """
        self.conversation_id = conversation_id
        self.booking_id = booking_id
        self.provider_id = provider_id
        self.dynamic_variables = dynamic_variables
        self.ws: ClientConnection | None = None
        self.started_at: datetime | None = None
        self.ended_at: datetime | None = None

    async def connect(self) -> None:
        """Establish WebSocket connection to ElevenLabs API.

        Raises:
            ConversationConnectionError: If connection fails
        """
        if not settings.ELEVENLABS_API_KEY:
            raise ConversationConnectionError("ELEVENLABS_API_KEY not configured")

        if not settings.ELEVENLABS_AGENT_ID:
            raise ConversationConnectionError("ELEVENLABS_AGENT_ID not configured")

        url = f"wss://api.elevenlabs.io/v1/convai/conversation?agent_id={settings.ELEVENLABS_AGENT_ID}"
        headers = {
            "xi-api-key": settings.ELEVENLABS_API_KEY,
        }

        try:
            self.ws = await asyncio.wait_for(
                websockets.connect(url, extra_headers=headers),
                timeout=CONNECTION_TIMEOUT,
            )
            self.started_at = datetime.now(timezone.utc)
            logger.info(
                "Connected to ElevenLabs for conversation %s (provider %s)",
                self.conversation_id,
                self.provider_id,
            )
        except TimeoutError as e:
            msg = f"Connection timeout for conversation {self.conversation_id}"
            logger.error(msg)
            raise ConversationConnectionError(msg) from e
        except Exception as e:
            msg = f"Failed to connect for conversation {self.conversation_id}: {e}"
            logger.error(msg)
            raise ConversationConnectionError(msg) from e

    async def send_initial_message(self) -> None:
        """Send initial message with dynamic variables to start conversation.

        The agent will use these variables in its greeting and conversation.
        """
        if not self.ws:
            raise ConversationConnectionError("Not connected")

        initial_message = {
            "type": "conversation_initiation_metadata",
            "conversation_initiation_metadata_event": {
                "conversation_id": self.conversation_id,
                "agent_output_audio_format": "pcm_16000",
            },
        }

        # Add dynamic variables if provided
        if self.dynamic_variables:
            metadata = initial_message["conversation_initiation_metadata_event"]
            metadata["custom_llm_extra_body"] = {
                "dynamic_variables": self.dynamic_variables,
            }

        try:
            await self.ws.send(json.dumps(initial_message))
            logger.info(
                "Sent initial message for conversation %s with variables: %s",
                self.conversation_id,
                list(self.dynamic_variables.keys()),
            )
        except Exception as e:
            msg = f"Failed to send initial message: {e}"
            logger.error(msg)
            raise ConversationConnectionError(msg) from e

    async def send_user_audio(self, audio_base64: str) -> None:
        """Send user audio to ElevenLabs agent.

        Args:
            audio_base64: Base64-encoded audio string (PCM 16kHz mono)

        Raises:
            ConversationConnectionError: If not connected or send fails
        """
        if not self.ws:
            raise ConversationConnectionError("Not connected")

        # Build audio message using ElevenLabs format
        audio_message = {
            "user_audio_chunk": audio_base64,
        }

        try:
            await self.ws.send(json.dumps(audio_message))
        except Exception as e:
            msg = f"Failed to send user audio: {e}"
            logger.error(msg)
            raise ConversationConnectionError(msg) from e

    async def listen(
        self,
        audio_callback: Callable[[bytes], Any],
        event_callback: Callable[[str, str], Any],
    ) -> str:
        """Listen for audio chunks and events from the conversation.

        Args:
            audio_callback: Called with raw audio bytes (PCM 16kHz)
            event_callback: Called with (event_type, text) for transcripts

        Returns:
            Outcome string: "completed", "timeout", or "failed"

        Raises:
            ConversationTimeoutError: If conversation exceeds timeout
        """
        if not self.ws:
            raise ConversationConnectionError("Not connected")

        outcome = "completed"

        try:
            # Listen with overall conversation timeout
            async for message in asyncio.wait_for(
                self._message_iterator(),
                timeout=CONVERSATION_TIMEOUT,
            ):
                msg_data = json.loads(message)
                msg_type = msg_data.get("type")

                # Handle audio chunks
                if msg_type == "audio":
                    audio_base64 = msg_data.get("audio_event", {}).get("audio_base_64")
                    if audio_base64:
                        audio_bytes = base64.b64decode(audio_base64)
                        try:
                            await audio_callback(audio_bytes)
                        except Exception:
                            logger.exception("Error in audio callback")

                # Handle agent responses (transcript)
                elif msg_type == "agent_response":
                    event = msg_data.get("agent_response_event", {})
                    text = event.get("agent_response")
                    if text:
                        try:
                            await event_callback("agent_response", text)
                        except Exception:
                            logger.exception("Error in event callback")

                # Handle user transcripts
                elif msg_type == "user_transcript":
                    event = msg_data.get("user_transcription_event", {})
                    text = event.get("user_transcript")
                    if text:
                        try:
                            await event_callback("user_transcript", text)
                        except Exception:
                            logger.exception("Error in event callback")

                # Handle interruptions
                elif msg_type == "interruption":
                    logger.debug(
                        "Agent interrupted for conversation %s",
                        self.conversation_id,
                    )

                # Handle conversation end
                elif msg_type == "conversation_end":
                    logger.info("Conversation %s ended normally", self.conversation_id)
                    break

        except TimeoutError:
            logger.warning("Conversation %s timed out", self.conversation_id)
            outcome = "timeout"
            msg = (
                f"Conversation {self.conversation_id} "
                f"exceeded {CONVERSATION_TIMEOUT}s"
            )
            raise ConversationTimeoutError(msg) from None
        except Exception as e:
            logger.exception("Error during conversation %s", self.conversation_id)
            outcome = "failed"
            raise ConversationError(f"Conversation failed: {e}") from e
        finally:
            self.ended_at = datetime.now(timezone.utc)
            await self.close()

        return outcome

    async def _message_iterator(self):
        """Internal iterator for WebSocket messages."""
        if not self.ws:
            return

        try:
            async for message in self.ws:
                yield message
        except websockets.exceptions.ConnectionClosed:
            logger.info(
                "WebSocket connection closed for conversation %s",
                self.conversation_id,
            )
        except Exception:
            logger.exception(
                "Error reading messages for conversation %s",
                self.conversation_id,
            )

    async def close(self) -> None:
        """Close the WebSocket connection."""
        if self.ws:
            try:
                await self.ws.close()
                logger.info(
                    "Closed WebSocket for conversation %s",
                    self.conversation_id,
                )
            except Exception:
                logger.exception(
                    "Error closing WebSocket for conversation %s",
                    self.conversation_id,
                )
            finally:
                self.ws = None

    async def start(self) -> None:
        """Connect and send initial message (convenience method)."""
        await self.connect()
        await self.send_initial_message()
