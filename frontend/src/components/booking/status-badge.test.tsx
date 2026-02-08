import { describe, it, expect, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { StatusBadge } from "./status-badge";

afterEach(cleanup);

describe("StatusBadge", () => {
  it("renders searching status", () => {
    render(<StatusBadge status="searching" />);
    expect(screen.getByText("Searching")).toBeInTheDocument();
  });

  it("renders options_ready status", () => {
    render(<StatusBadge status="options_ready" />);
    expect(screen.getByText("Options Ready")).toBeInTheDocument();
  });

  it("renders call_failed status with destructive variant", () => {
    render(<StatusBadge status="call_failed" />);
    const badge = screen.getByText("Failed");
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveAttribute("data-variant", "destructive");
  });

  it("renders confirmed status with default variant", () => {
    render(<StatusBadge status="confirmed" />);
    const badge = screen.getByText("Confirmed");
    expect(badge).toHaveAttribute("data-variant", "default");
  });

  it("renders unknown status as-is with outline variant", () => {
    render(<StatusBadge status="unknown_status" />);
    const badge = screen.getByText("unknown_status");
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveAttribute("data-variant", "outline");
  });

  it("renders cancelled status with outline variant", () => {
    render(<StatusBadge status="cancelled" />);
    const badge = screen.getByText("Cancelled");
    expect(badge).toHaveAttribute("data-variant", "outline");
  });
});
