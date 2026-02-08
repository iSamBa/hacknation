"use client";

import { useCallback, useEffect, useRef, useState } from "react";

const WS_BASE_URL =
  process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";

export interface BookingStatusUpdate {
  type: string;
  status: string;
  booking_id: string;
}

export interface UseBookingStatusReturn {
  status: string | null;
  isConnected: boolean;
  lastUpdate: BookingStatusUpdate | null;
  providerCount: number | null;
}

const RECONNECT_DELAY_MS = 2000;
const MAX_RECONNECT_ATTEMPTS = 5;

export function useBookingStatus(
  bookingId: string | null,
): UseBookingStatusReturn {
  const [status, setStatus] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<BookingStatusUpdate | null>(
    null,
  );
  const [providerCount, setProviderCount] = useState<number | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const cleanup = useCallback(() => {
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current);
      reconnectTimer.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
  }, []);

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
          if (data.type === "provider_count") {
            setProviderCount(data.count);
          } else {
            setStatus(data.status);
            setLastUpdate(data as BookingStatusUpdate);
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

  return { status, isConnected, lastUpdate, providerCount };
}
