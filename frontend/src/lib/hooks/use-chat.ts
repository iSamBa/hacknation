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

export interface ChatMessageResponse {
  is_booking_request: boolean;
  reply: string;
  booking_id: string | null;
  status: string | null;
  intent: BookingIntent | null;
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
  const messagesRef = useRef<ChatMessage[]>([]);

  const nextId = () => {
    idCounter.current += 1;
    return `msg-${idCounter.current}`;
  };

  const sendMessage = useCallback(async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || pendingRef.current) return;

    pendingRef.current = true;

    const history = messagesRef.current
      .filter((m) => !m.error)
      .map((m) => ({ role: m.role, content: m.content }));

    const userMessage: ChatMessage = {
      id: nextId(),
      role: "user",
      content: trimmed,
      timestamp: new Date(),
    };

    messagesRef.current = [...messagesRef.current, userMessage];
    setMessages(messagesRef.current);
    setIsLoading(true);

    try {
      const response = await apiPost<ChatMessageResponse>(
        "/api/chat",
        { message: trimmed, history },
      );

      const assistantMessage: ChatMessage = {
        id: nextId(),
        role: "assistant",
        content: response.reply,
        intent: response.intent ?? undefined,
        bookingId: response.booking_id ?? undefined,
        timestamp: new Date(),
      };

      messagesRef.current = [...messagesRef.current, assistantMessage];
      setMessages(messagesRef.current);
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

      messagesRef.current = [...messagesRef.current, errorMessage];
      setMessages(messagesRef.current);
    } finally {
      setIsLoading(false);
      pendingRef.current = false;
    }
  }, []);

  return { messages, isLoading, sendMessage };
}
