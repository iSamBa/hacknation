"use client";

import { useCallback, useRef, useState } from "react";
import { apiPost } from "@/lib/api";

export interface BookingIntent {
  service_type: string;
  date: string | null;
  time_preference: string | null;
  location_override: string | null;
  constraints: string[];
  urgency: string;
}

export interface BookingRequestResponse {
  booking_id: string;
  status: string;
  intent: BookingIntent;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  intent?: BookingIntent;
  bookingId?: string;
  timestamp: Date;
  error?: boolean;
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const idCounter = useRef(0);
  const pendingRef = useRef(false);

  const nextId = () => {
    idCounter.current += 1;
    return `msg-${idCounter.current}`;
  };

  const sendMessage = useCallback(async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || pendingRef.current) return;

    pendingRef.current = true;

    const userMessage: ChatMessage = {
      id: nextId(),
      role: "user",
      content: trimmed,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const response = await apiPost<BookingRequestResponse>(
        "/api/bookings",
        { message: trimmed },
      );

      const intent = response.intent;
      const serviceType = intent?.service_type ?? "unknown";

      const assistantMessage: ChatMessage = {
        id: nextId(),
        role: "assistant",
        content: `I understood your request for a ${serviceType} appointment.`,
        intent,
        bookingId: response.booking_id,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      const errorMessage: ChatMessage = {
        id: nextId(),
        role: "assistant",
        content:
          err instanceof Error
            ? err.message
            : "Sorry, I couldn't process your request. Please try again.",
        timestamp: new Date(),
        error: true,
      };

      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      pendingRef.current = false;
    }
  }, []);

  return { messages, isLoading, sendMessage };
}
