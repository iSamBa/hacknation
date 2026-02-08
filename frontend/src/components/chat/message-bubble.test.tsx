import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { MessageBubble } from "./message-bubble";
import type { ChatMessage } from "@/lib/hooks/use-chat";

afterEach(cleanup);

const userMessage: ChatMessage = {
  id: "msg-1",
  role: "user",
  content: "I need a dentist",
  timestamp: new Date("2026-02-08T10:30:00"),
};

const assistantMessage: ChatMessage = {
  id: "msg-2",
  role: "assistant",
  content: "I understood your request for a dentist appointment.",
  intent: {
    service_type: "dentist",
    date: "2026-02-10",
    time_preference: "afternoon",
    location_override: null,
    constraints: [],
    urgency: "flexible",
  },
  bookingId: "abc-123",
  timestamp: new Date("2026-02-08T10:30:01"),
};

const errorMessage: ChatMessage = {
  id: "msg-3",
  role: "assistant",
  content: "Sorry, something went wrong.",
  timestamp: new Date("2026-02-08T10:30:02"),
  error: true,
};

describe("MessageBubble", () => {
  it("renders user message content", () => {
    const { container } = render(<MessageBubble message={userMessage} />);
    expect(container.textContent).toContain("I need a dentist");
  });

  it("renders assistant message content", () => {
    const { container } = render(
      <MessageBubble message={assistantMessage} />,
    );
    expect(container.textContent).toContain(
      "I understood your request for a dentist appointment.",
    );
  });

  it("renders intent card for assistant messages with intent", () => {
    const { container } = render(
      <MessageBubble
        message={assistantMessage}
        onFindProviders={vi.fn()}
      />,
    );
    expect(container.textContent).toContain("Parsed Request");
    const buttons = screen.getAllByRole("button", {
      name: /find providers/i,
    });
    expect(buttons.length).toBeGreaterThanOrEqual(1);
  });

  it("does not render intent card for user messages", () => {
    const { container } = render(<MessageBubble message={userMessage} />);
    expect(container.textContent).not.toContain("Parsed Request");
  });

  it("renders error message content", () => {
    const { container } = render(<MessageBubble message={errorMessage} />);
    expect(container.textContent).toContain("Sorry, something went wrong.");
  });

  it("renders timestamp for messages", () => {
    const { container } = render(<MessageBubble message={userMessage} />);
    expect(container.textContent).toMatch(/10:30/);
  });
});
