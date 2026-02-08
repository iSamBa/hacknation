import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useChat } from "./use-chat";

const mockApiPost = vi.fn();

vi.mock("@/lib/api", () => ({
  apiPost: (...args: unknown[]) => mockApiPost(...args),
}));

beforeEach(() => {
  vi.clearAllMocks();
});

describe("useChat", () => {
  it("starts with empty messages and not loading", () => {
    const { result } = renderHook(() => useChat());
    expect(result.current.messages).toEqual([]);
    expect(result.current.isLoading).toBe(false);
  });

  it("adds user message immediately when sending", async () => {
    mockApiPost.mockResolvedValue({
      booking_id: "abc-123",
      status: "searching",
      intent: {
        service_type: "dentist",
        date: "2026-02-10",
        time_preference: "afternoon",
        location_override: null,
        constraints: [],
        urgency: "flexible",
      },
    });

    const { result } = renderHook(() => useChat());

    await act(async () => {
      result.current.sendMessage("I need a dentist next Tuesday afternoon");
    });

    expect(result.current.messages).toHaveLength(2);
    expect(result.current.messages[0].role).toBe("user");
    expect(result.current.messages[0].content).toBe(
      "I need a dentist next Tuesday afternoon",
    );
  });

  it("calls POST /api/bookings with the message", async () => {
    mockApiPost.mockResolvedValue({
      booking_id: "abc-123",
      status: "searching",
      intent: {
        service_type: "dentist",
        date: null,
        time_preference: null,
        location_override: null,
        constraints: [],
        urgency: "flexible",
      },
    });

    const { result } = renderHook(() => useChat());

    await act(async () => {
      result.current.sendMessage("I need a dentist");
    });

    expect(mockApiPost).toHaveBeenCalledWith("/api/bookings", {
      message: "I need a dentist",
    });
  });

  it("adds assistant message with intent on success", async () => {
    const intent = {
      service_type: "plumber",
      date: "2026-02-12",
      time_preference: "morning",
      location_override: "downtown",
      constraints: ["emergency"],
      urgency: "asap",
    };

    mockApiPost.mockResolvedValue({
      booking_id: "def-456",
      status: "searching",
      intent,
    });

    const { result } = renderHook(() => useChat());

    await act(async () => {
      result.current.sendMessage("Find me a plumber ASAP");
    });

    expect(result.current.messages).toHaveLength(2);

    const assistantMsg = result.current.messages[1];
    expect(assistantMsg.role).toBe("assistant");
    expect(assistantMsg.intent).toEqual(intent);
    expect(assistantMsg.bookingId).toBe("def-456");
    expect(assistantMsg.error).toBeUndefined();
  });

  it("adds error message when API call fails", async () => {
    mockApiPost.mockRejectedValue(new Error("Network error"));

    const { result } = renderHook(() => useChat());

    await act(async () => {
      result.current.sendMessage("I need a dentist");
    });

    expect(result.current.messages).toHaveLength(2);

    const errorMsg = result.current.messages[1];
    expect(errorMsg.role).toBe("assistant");
    expect(errorMsg.error).toBe(true);
    expect(errorMsg.content).toBe("Network error");
    expect(errorMsg.intent).toBeUndefined();
  });

  it("sets isLoading to false after completion", async () => {
    mockApiPost.mockResolvedValue({
      booking_id: "abc-123",
      status: "searching",
      intent: {
        service_type: "dentist",
        date: null,
        time_preference: null,
        location_override: null,
        constraints: [],
        urgency: "flexible",
      },
    });

    const { result } = renderHook(() => useChat());

    await act(async () => {
      result.current.sendMessage("I need a dentist");
    });

    expect(result.current.isLoading).toBe(false);
  });

  it("sets isLoading to false after error", async () => {
    mockApiPost.mockRejectedValue(new Error("fail"));

    const { result } = renderHook(() => useChat());

    await act(async () => {
      result.current.sendMessage("I need a dentist");
    });

    expect(result.current.isLoading).toBe(false);
  });

  it("assigns unique IDs to messages", async () => {
    mockApiPost.mockResolvedValue({
      booking_id: "abc-123",
      status: "searching",
      intent: {
        service_type: "dentist",
        date: null,
        time_preference: null,
        location_override: null,
        constraints: [],
        urgency: "flexible",
      },
    });

    const { result } = renderHook(() => useChat());

    await act(async () => {
      result.current.sendMessage("First message");
    });

    await act(async () => {
      result.current.sendMessage("Second message");
    });

    const ids = result.current.messages.map((m) => m.id);
    const uniqueIds = new Set(ids);
    expect(uniqueIds.size).toBe(ids.length);
  });
});
