import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import { BookingDetailView } from "./booking-detail";

const mockApiGet = vi.fn();

vi.mock("@/lib/api", () => ({
  apiGet: (...args: unknown[]) => mockApiGet(...args),
}));

vi.mock("@/lib/hooks/use-booking-status", () => ({
  useBookingStatus: () => ({
    status: null,
    isConnected: false,
    lastUpdate: null,
  }),
}));

const BOOKING = {
  id: "abc-123",
  status: "shortlisting",
  service_type: "dentist",
  preferred_date: "2026-02-10",
  preferred_time: "afternoon",
  location_override: null,
  raw_message: "I need a dentist next Tuesday afternoon",
  created_at: "2026-02-08T10:00:00Z",
};

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(cleanup);

describe("BookingDetailView", () => {
  it("shows loading skeleton initially", () => {
    mockApiGet.mockReturnValue(new Promise(() => {}));

    render(<BookingDetailView bookingId="abc-123" />);

    const pulsingElements = document.querySelectorAll(".animate-pulse");
    expect(pulsingElements.length).toBeGreaterThan(0);
  });

  it("renders booking details after loading", async () => {
    mockApiGet.mockResolvedValue(BOOKING);

    render(<BookingDetailView bookingId="abc-123" />);

    await waitFor(() => {
      expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
        "dentist",
      );
    });

    expect(screen.getByText("2026-02-10")).toBeInTheDocument();
    expect(screen.getByText("afternoon")).toBeInTheDocument();
    expect(
      screen.getByText(/I need a dentist next Tuesday afternoon/),
    ).toBeInTheDocument();
  });

  it("renders pipeline progress component", async () => {
    mockApiGet.mockResolvedValue(BOOKING);

    render(<BookingDetailView bookingId="abc-123" />);

    await waitFor(() => {
      expect(screen.getByText("Pipeline Progress")).toBeInTheDocument();
    });

    expect(screen.getByText("Searching")).toBeInTheDocument();
    expect(screen.getByText("Ready")).toBeInTheDocument();
  });

  it("renders status badge", async () => {
    mockApiGet.mockResolvedValue(BOOKING);

    render(<BookingDetailView bookingId="abc-123" />);

    await waitFor(() => {
      const badge = screen.getByText("Shortlisting", {
        selector: "[data-slot='badge']",
      });
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveAttribute("data-variant", "secondary");
    });
  });

  it("shows error state when booking not found", async () => {
    mockApiGet.mockRejectedValue(new Error("Not Found"));

    render(<BookingDetailView bookingId="bad-id" />);

    await waitFor(() => {
      expect(screen.getByText("Booking Not Found")).toBeInTheDocument();
    });

    expect(screen.getByText("Not Found")).toBeInTheDocument();
  });

  it("fetches booking from correct API endpoint", async () => {
    mockApiGet.mockResolvedValue(BOOKING);

    render(<BookingDetailView bookingId="abc-123" />);

    await waitFor(() => {
      expect(mockApiGet).toHaveBeenCalledWith("/api/bookings/abc-123");
    });
  });

  it("does not show optional fields when null", async () => {
    mockApiGet.mockResolvedValue({
      ...BOOKING,
      preferred_date: null,
      preferred_time: null,
      location_override: null,
    });

    render(<BookingDetailView bookingId="abc-123" />);

    await waitFor(() => {
      expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
        "dentist",
      );
    });

    expect(screen.queryByText("Date:")).not.toBeInTheDocument();
    expect(screen.queryByText("Time:")).not.toBeInTheDocument();
    expect(screen.queryByText("Location:")).not.toBeInTheDocument();
  });
});
