import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useBookingStatus } from "./use-booking-status";

// Mock WebSocket
class MockWebSocket {
  static instances: MockWebSocket[] = [];
  url: string;
  onopen: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  readyState = 0;

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  close() {
    this.readyState = 3;
    this.onclose?.();
  }

  // Helper to simulate server sending a message
  simulateMessage(data: Record<string, unknown>) {
    this.onmessage?.({ data: JSON.stringify(data) });
  }

  // Helper to simulate connection open
  simulateOpen() {
    this.readyState = 1;
    this.onopen?.();
  }

  // Helper to simulate connection close
  simulateClose() {
    this.readyState = 3;
    this.onclose?.();
  }

  simulateError() {
    this.onerror?.();
  }
}

beforeEach(() => {
  MockWebSocket.instances = [];
  vi.stubGlobal("WebSocket", MockWebSocket);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("useBookingStatus", () => {
  it("returns initial state when no bookingId provided", () => {
    const { result } = renderHook(() => useBookingStatus(null));

    expect(result.current.status).toBeNull();
    expect(result.current.isConnected).toBe(false);
    expect(result.current.lastUpdate).toBeNull();
  });

  it("connects to WebSocket when bookingId is provided", () => {
    renderHook(() => useBookingStatus("abc-123"));

    expect(MockWebSocket.instances).toHaveLength(1);
    expect(MockWebSocket.instances[0].url).toBe(
      "ws://localhost:8000/ws/bookings/abc-123",
    );
  });

  it("sets isConnected to true when WebSocket opens", () => {
    const { result } = renderHook(() => useBookingStatus("abc-123"));

    act(() => {
      MockWebSocket.instances[0].simulateOpen();
    });

    expect(result.current.isConnected).toBe(true);
  });

  it("updates status when message received", () => {
    const { result } = renderHook(() => useBookingStatus("abc-123"));

    act(() => {
      MockWebSocket.instances[0].simulateOpen();
    });

    act(() => {
      MockWebSocket.instances[0].simulateMessage({
        type: "status",
        status: "shortlisting",
        booking_id: "abc-123",
      });
    });

    expect(result.current.status).toBe("shortlisting");
    expect(result.current.lastUpdate).toEqual({
      type: "status",
      status: "shortlisting",
      booking_id: "abc-123",
    });
  });

  it("updates status through multiple transitions", () => {
    const { result } = renderHook(() => useBookingStatus("abc-123"));

    act(() => {
      MockWebSocket.instances[0].simulateOpen();
    });

    const statuses = ["searching", "shortlisting", "calling", "options_ready"];
    for (const s of statuses) {
      act(() => {
        MockWebSocket.instances[0].simulateMessage({
          type: "status",
          status: s,
          booking_id: "abc-123",
        });
      });
      expect(result.current.status).toBe(s);
    }
  });

  it("sets isConnected to false when WebSocket closes", () => {
    const { result } = renderHook(() => useBookingStatus("abc-123"));

    act(() => {
      MockWebSocket.instances[0].simulateOpen();
    });
    expect(result.current.isConnected).toBe(true);

    act(() => {
      MockWebSocket.instances[0].simulateClose();
    });
    expect(result.current.isConnected).toBe(false);
  });

  it("attempts reconnection after disconnect", async () => {
    vi.useFakeTimers();

    renderHook(() => useBookingStatus("abc-123"));
    expect(MockWebSocket.instances).toHaveLength(1);

    act(() => {
      MockWebSocket.instances[0].simulateOpen();
    });

    act(() => {
      MockWebSocket.instances[0].simulateClose();
    });

    // Advance past reconnect delay
    act(() => {
      vi.advanceTimersByTime(2500);
    });

    expect(MockWebSocket.instances).toHaveLength(2);

    vi.useRealTimers();
  });

  it("cleans up WebSocket on unmount", () => {
    const { unmount } = renderHook(() => useBookingStatus("abc-123"));

    expect(MockWebSocket.instances).toHaveLength(1);
    const ws = MockWebSocket.instances[0];

    unmount();

    expect(ws.readyState).toBe(3); // CLOSED
  });

  it("cleans up and reconnects when bookingId changes", () => {
    const { rerender } = renderHook(
      ({ id }) => useBookingStatus(id),
      { initialProps: { id: "abc-123" as string | null } },
    );

    expect(MockWebSocket.instances).toHaveLength(1);
    expect(MockWebSocket.instances[0].url).toContain("abc-123");

    rerender({ id: "def-456" });

    // Old connection closed, new one created
    expect(MockWebSocket.instances).toHaveLength(2);
    expect(MockWebSocket.instances[1].url).toContain("def-456");
  });

  it("ignores malformed messages", () => {
    const { result } = renderHook(() => useBookingStatus("abc-123"));

    act(() => {
      MockWebSocket.instances[0].simulateOpen();
    });

    act(() => {
      MockWebSocket.instances[0].onmessage?.({
        data: "not valid json{{{",
      });
    });

    expect(result.current.status).toBeNull();
    expect(result.current.lastUpdate).toBeNull();
  });

  it("does not connect when bookingId is null", () => {
    renderHook(() => useBookingStatus(null));

    expect(MockWebSocket.instances).toHaveLength(0);
  });
});
