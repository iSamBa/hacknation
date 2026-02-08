import { describe, it, expect, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { PipelineProgress } from "./pipeline-progress";

afterEach(cleanup);

describe("PipelineProgress", () => {
  it("renders all four pipeline phases", () => {
    render(<PipelineProgress status={null} />);

    expect(screen.getByText("Searching")).toBeInTheDocument();
    expect(screen.getByText("Shortlisting")).toBeInTheDocument();
    expect(screen.getByText("Calling")).toBeInTheDocument();
    expect(screen.getByText("Ready")).toBeInTheDocument();
  });

  it("marks active phase differently from pending", () => {
    render(<PipelineProgress status="searching" />);

    const searching = screen.getByText("Searching");
    expect(searching.className).toContain("text-foreground");

    const shortlisting = screen.getByText("Shortlisting");
    expect(shortlisting.className).toContain("text-muted-foreground");
  });

  it("marks completed phases with primary color when calling", () => {
    render(<PipelineProgress status="calling" />);

    expect(screen.getByText("Searching").className).toContain("text-primary");
    expect(screen.getByText("Shortlisting").className).toContain(
      "text-primary",
    );
  });

  it("shows error state when status is call_failed", () => {
    render(<PipelineProgress status="call_failed" />);

    expect(screen.getByText("Failed")).toBeInTheDocument();
  });

  it("marks first three phases completed when status is options_ready", () => {
    render(<PipelineProgress status="options_ready" />);

    expect(screen.getByText("Searching").className).toContain("text-primary");
    expect(screen.getByText("Shortlisting").className).toContain(
      "text-primary",
    );
    expect(screen.getByText("Calling").className).toContain("text-primary");
  });

  it("applies custom className", () => {
    const { container } = render(
      <PipelineProgress status="searching" className="my-custom-class" />,
    );
    expect(container.firstChild).toHaveClass("my-custom-class");
  });

  it("renders spinner for active phase", () => {
    const { container } = render(<PipelineProgress status="shortlisting" />);

    const spinners = container.querySelectorAll(".animate-spin");
    expect(spinners).toHaveLength(1);
  });
});
