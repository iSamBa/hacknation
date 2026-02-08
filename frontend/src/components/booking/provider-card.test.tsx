import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup, fireEvent } from "@testing-library/react";
import { ProviderCard } from "./provider-card";
import type { ResultItem } from "@/lib/types/booking";

afterEach(cleanup);

const BASE_RESULT: ResultItem = {
  rank: 1,
  provider_name: "Downtown Dental",
  place_id: "place_abc",
  slot: "2026-02-15T10:00:00Z",
  travel_minutes: 12,
  rating: 4.7,
  review_count: 234,
  score: 0.85,
  notes: null,
  provider_id: "prov-1",
  call_outcome: "slot_offered",
};

describe("ProviderCard", () => {
  it("renders provider name", () => {
    render(<ProviderCard result={BASE_RESULT} />);
    expect(screen.getByText("Downtown Dental")).toBeInTheDocument();
  });

  it("renders rating with stars", () => {
    render(<ProviderCard result={BASE_RESULT} />);
    expect(screen.getByText("4.7")).toBeInTheDocument();
    expect(screen.getByText("(234)")).toBeInTheDocument();
  });

  it("renders slot date and time", () => {
    render(<ProviderCard result={BASE_RESULT} />);
    // The exact format depends on locale but should contain date parts
    expect(screen.getByText(/Feb/)).toBeInTheDocument();
    expect(screen.getByText(/AM/i)).toBeInTheDocument();
  });

  it("renders travel minutes", () => {
    render(<ProviderCard result={BASE_RESULT} />);
    expect(screen.getByText("12 min")).toBeInTheDocument();
  });

  it("hides travel when null", () => {
    render(
      <ProviderCard result={{ ...BASE_RESULT, travel_minutes: null }} />,
    );
    expect(screen.queryByText(/min/)).not.toBeInTheDocument();
  });

  it("renders score as percentage", () => {
    render(<ProviderCard result={BASE_RESULT} />);
    expect(screen.getByText("85%")).toBeInTheDocument();
  });

  it("shows Best Match badge for rank 1", () => {
    render(<ProviderCard result={BASE_RESULT} />);
    expect(screen.getByText("Best Match")).toBeInTheDocument();
  });

  it("shows numbered badge for rank > 3", () => {
    render(<ProviderCard result={{ ...BASE_RESULT, rank: 5 }} />);
    expect(screen.getByText("#5")).toBeInTheDocument();
  });

  it("shows notes when present", () => {
    render(
      <ProviderCard
        result={{ ...BASE_RESULT, notes: "New patients welcome" }}
      />,
    );
    expect(screen.getByText("New patients welcome")).toBeInTheDocument();
  });

  it("hides notes when null", () => {
    render(<ProviderCard result={BASE_RESULT} />);
    expect(
      screen.queryByText("New patients welcome"),
    ).not.toBeInTheDocument();
  });

  it("renders Select button", () => {
    render(<ProviderCard result={BASE_RESULT} />);
    expect(
      screen.getByRole("button", { name: "Select" }),
    ).toBeInTheDocument();
  });

  it("calls onSelect when Select clicked", () => {
    const onSelect = vi.fn();
    render(<ProviderCard result={BASE_RESULT} onSelect={onSelect} />);

    fireEvent.click(screen.getByRole("button", { name: "Select" }));

    expect(onSelect).toHaveBeenCalledWith(BASE_RESULT);
  });

  it("renders 2nd badge for rank 2", () => {
    render(<ProviderCard result={{ ...BASE_RESULT, rank: 2 }} />);
    expect(screen.getByText("2nd")).toBeInTheDocument();
  });

  it("renders 3rd badge for rank 3", () => {
    render(<ProviderCard result={{ ...BASE_RESULT, rank: 3 }} />);
    expect(screen.getByText("3rd")).toBeInTheDocument();
  });
});
