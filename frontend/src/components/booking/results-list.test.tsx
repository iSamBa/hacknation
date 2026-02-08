import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import { ResultsList } from "./results-list";
import type { ResultItem } from "@/lib/types/booking";

const mockApiGet = vi.fn();

vi.mock("@/lib/api", () => ({
  apiGet: (...args: unknown[]) => mockApiGet(...args),
}));

const RESULTS: ResultItem[] = [
  {
    rank: 1,
    provider_name: "Top Provider",
    place_id: "place_1",
    slot: "2026-02-15T10:00:00Z",
    travel_minutes: 10,
    rating: 4.8,
    review_count: 300,
    score: 0.92,
    notes: null,
    provider_id: "prov-1",
    call_outcome: "slot_offered",
  },
  {
    rank: 2,
    provider_name: "Second Provider",
    place_id: "place_2",
    slot: "2026-02-16T14:00:00Z",
    travel_minutes: 20,
    rating: 4.5,
    review_count: 150,
    score: 0.78,
    notes: "Cash only",
    provider_id: "prov-2",
    call_outcome: "booked_tentative",
  },
];

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(cleanup);

describe("ResultsList", () => {
  it("shows loading state initially", () => {
    mockApiGet.mockReturnValue(new Promise(() => {}));

    render(<ResultsList bookingId="abc-123" />);

    expect(screen.getByText("Loading results...")).toBeInTheDocument();
  });

  it("fetches results from correct API endpoint", async () => {
    mockApiGet.mockResolvedValue(RESULTS);

    render(<ResultsList bookingId="abc-123" />);

    await waitFor(() => {
      expect(mockApiGet).toHaveBeenCalledWith(
        "/api/bookings/abc-123/results",
      );
    });
  });

  it("renders provider cards after loading", async () => {
    mockApiGet.mockResolvedValue(RESULTS);

    render(<ResultsList bookingId="abc-123" />);

    await waitFor(() => {
      expect(screen.getByText("Top Provider")).toBeInTheDocument();
    });

    expect(screen.getByText("Second Provider")).toBeInTheDocument();
  });

  it("shows result count", async () => {
    mockApiGet.mockResolvedValue(RESULTS);

    render(<ResultsList bookingId="abc-123" />);

    await waitFor(() => {
      expect(screen.getByText("2 results")).toBeInTheDocument();
    });
  });

  it("shows empty state when no results", async () => {
    mockApiGet.mockResolvedValue([]);

    render(<ResultsList bookingId="abc-123" />);

    await waitFor(() => {
      expect(
        screen.getByText("No providers found available slots."),
      ).toBeInTheDocument();
    });
  });

  it("shows error state on API failure", async () => {
    mockApiGet.mockRejectedValue(new Error("Server error"));

    render(<ResultsList bookingId="abc-123" />);

    await waitFor(() => {
      expect(screen.getByText("Server error")).toBeInTheDocument();
    });
  });

  it("shows heading", async () => {
    mockApiGet.mockResolvedValue(RESULTS);

    render(<ResultsList bookingId="abc-123" />);

    await waitFor(() => {
      expect(screen.getByText("Available Options")).toBeInTheDocument();
    });
  });

  it("shows singular result count for 1 result", async () => {
    mockApiGet.mockResolvedValue([RESULTS[0]]);

    render(<ResultsList bookingId="abc-123" />);

    await waitFor(() => {
      expect(screen.getByText("1 result")).toBeInTheDocument();
    });
  });
});
