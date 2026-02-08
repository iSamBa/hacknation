"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { apiGet } from "@/lib/api";

const WS_BASE_URL =
  process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";

export interface BookingStatusUpdate {
  type: string;
  status: string;
  booking_id: string;
}

export interface ConversationState {
  isActive: boolean;
  currentProvider: { id: string; name: string } | null;
  transcript: Array<{ type: string; text: string }>;
}

export interface UseBookingStatusReturn {
  status: string | null;
  isConnected: boolean;
  lastUpdate: BookingStatusUpdate | null;
  providerCount: number | null;
  conversation: ConversationState;
  onConversationAudio?: (audioBase64: string, providerId: string, providerName: string) => void;
}

const RECONNECT_DELAY_MS = 2000;
const MAX_RECONNECT_ATTEMPTS = 5;
const POLL_INTERVAL_MS = 3000;
const TERMINAL_STATUSES = new Set(["options_ready", "confirmed", "cancelled"]);

export function useBookingStatus(
  bookingId: string | null,
  onConversationAudio?: (audioBase64: string, providerId: string, providerName: string) => void,
): UseBookingStatusReturn {
  const [status, setStatus] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<BookingStatusUpdate | null>(
    null,
  );
  const [providerCount, setProviderCount] = useState<number | null>(null);
  const [conversation, setConversation] = useState<ConversationState>({
    isActive: false,
    currentProvider: null,
    transcript: [],
  });
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pollTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  const cleanup = useCallback(() => {
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current);
      reconnectTimer.current = null;
    }
    if (pollTimer.current) {
      clearInterval(pollTimer.current);
      pollTimer.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
  }, []);

  // Polling fallback — fetches booking status via REST
  useEffect(() => {
    if (!bookingId) return;

    // Only poll when WS is disconnected and status is non-terminal
    const shouldPoll = !isConnected && !TERMINAL_STATUSES.has(status ?? "");
    if (!shouldPoll) {
      if (pollTimer.current) {
        clearInterval(pollTimer.current);
        pollTimer.current = null;
      }
      return;
    }

    async function fetchStatus() {
      try {
        const data = await apiGet<{ status: string }>(
          `/api/bookings/${bookingId}`,
        );
        setStatus((prev) => {
          // Only update if the polled status is different
          if (prev !== data.status) return data.status;
          return prev;
        });
      } catch {
        // Booking may not exist yet or network issue — ignore
      }
    }

    // Fetch immediately, then set up the interval
    fetchStatus();
    pollTimer.current = setInterval(fetchStatus, POLL_INTERVAL_MS);

    return () => {
      if (pollTimer.current) {
        clearInterval(pollTimer.current);
        pollTimer.current = null;
      }
    };
  }, [bookingId, isConnected, status]);

  // WebSocket connection
  useEffect(() => {
    if (!bookingId) {
      cleanup();
      return;
    }

    function connect() {
      const url = `${WS_BASE_URL}/ws/bookings/${bookingId}`;
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        reconnectAttempts.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          // Handle different message types
          if (data.type === "provider_count") {
            setProviderCount(data.count);
          } else if (data.type === "status") {
            setStatus(data.status);
            setLastUpdate(data as BookingStatusUpdate);
          } else if (data.type === "conversation_started") {
            setConversation({
              isActive: true,
              currentProvider: {
                id: data.provider_id,
                name: data.provider_name,
              },
              transcript: [],
            });
          } else if (data.type === "conversation_audio") {
            // Pass audio to callback if provided
            if (onConversationAudio && data.audio) {
              onConversationAudio(
                data.audio,
                data.provider_id,
                conversation.currentProvider?.name || "Unknown"
              );
            }
          } else if (data.type === "conversation_event") {
            // Add to transcript
            setConversation(prev => ({
              ...prev,
              transcript: [
                ...prev.transcript,
                { type: data.event_type, text: data.text },
              ],
            }));
          } else if (data.type === "conversation_ended") {
            setConversation(prev => ({
              ...prev,
              isActive: false,
            }));
          } else if (data.type === "call_result_updated") {
            // Webhook updated a call result - could trigger UI refresh if needed
            console.log("Call result updated:", data);
          } else {
            // Fallback for other message types
            if (data.status) {
              setStatus(data.status);
              setLastUpdate(data as BookingStatusUpdate);
            }
          }
        } catch {
          // Ignore malformed messages
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        wsRef.current = null;

        if (reconnectAttempts.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttempts.current += 1;
          reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY_MS);
        }
      };

      ws.onerror = () => {
        // onclose will fire after onerror, triggering reconnect
      };
    }

    connect();

    return cleanup;
  }, [bookingId, cleanup]);

  return { status, isConnected, lastUpdate, providerCount, conversation, onConversationAudio };
}
