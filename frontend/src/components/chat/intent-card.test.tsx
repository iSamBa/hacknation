import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { IntentCard } from "./intent-card";
import type { BookingIntent } from "@/lib/hooks/use-chat";

afterEach(cleanup);

const baseIntent: BookingIntent = {
  service_type: "dentist",
  date: "2026-02-10",
  time_preference: "afternoon",
  location_override: null,
  constraints: [],
  urgency: "flexible",
};

describe("IntentCard", () => {
  it("renders service type", () => {
    const { container } = render(<IntentCard intent={baseIntent} />);
    expect(container.textContent).toContain("dentist");
  });

  it("renders date when provided", () => {
    const { container } = render(<IntentCard intent={baseIntent} />);
    expect(container.textContent).toContain("Date:");
    expect(container.textContent).toContain("2026-02-10");
  });

  it("renders time preference when provided", () => {
    const { container } = render(<IntentCard intent={baseIntent} />);
    expect(container.textContent).toContain("Time:");
    expect(container.textContent).toContain("afternoon");
  });

  it("does not render date row when date is null", () => {
    const { container } = render(
      <IntentCard intent={{ ...baseIntent, date: null }} />,
    );
    expect(container.textContent).not.toContain("Date:");
  });

  it("does not render time row when time_preference is null", () => {
    const { container } = render(
      <IntentCard intent={{ ...baseIntent, time_preference: null }} />,
    );
    expect(container.textContent).not.toContain("Time:");
  });

  it("renders location override when provided", () => {
    const { container } = render(
      <IntentCard
        intent={{ ...baseIntent, location_override: "downtown" }}
      />,
    );
    expect(container.textContent).toContain("downtown");
  });

  it("renders constraints as badges", () => {
    const { container } = render(
      <IntentCard
        intent={{
          ...baseIntent,
          constraints: ["accepts insurance", "evening hours"],
        }}
      />,
    );
    expect(container.textContent).toContain("accepts insurance");
    expect(container.textContent).toContain("evening hours");
  });

  it("renders ASAP urgency badge", () => {
    const { container } = render(
      <IntentCard intent={{ ...baseIntent, urgency: "asap" }} />,
    );
    expect(container.textContent).toContain("ASAP");
  });

  it("renders Flexible urgency badge", () => {
    const { container } = render(<IntentCard intent={baseIntent} />);
    expect(container.textContent).toContain("Flexible");
  });

  it("renders Find Providers button when bookingId and handler are provided", () => {
    const onFindProviders = vi.fn();
    render(
      <IntentCard
        intent={baseIntent}
        bookingId="abc-123"
        onFindProviders={onFindProviders}
      />,
    );
    const buttons = screen.getAllByRole("button", {
      name: /find providers/i,
    });
    expect(buttons.length).toBeGreaterThanOrEqual(1);
  });

  it("does not render Find Providers button without bookingId", () => {
    render(<IntentCard intent={baseIntent} />);
    expect(
      screen.queryByRole("button", { name: /find providers/i }),
    ).not.toBeInTheDocument();
  });

  it("calls onFindProviders with bookingId when button is clicked", () => {
    const onFindProviders = vi.fn();
    render(
      <IntentCard
        intent={baseIntent}
        bookingId="abc-123"
        onFindProviders={onFindProviders}
      />,
    );
    const buttons = screen.getAllByRole("button", {
      name: /find providers/i,
    });
    fireEvent.click(buttons[0]);
    expect(onFindProviders).toHaveBeenCalledWith("abc-123");
  });
});
