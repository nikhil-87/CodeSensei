import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StatusBadge } from "../StatusBadge";

describe("StatusBadge", () => {
  it("renders the status as label by default", () => {
    const { getByText } = render(<StatusBadge status="ready" />);
    const badge = getByText("ready");
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveAttribute("data-status", "ready");
  });

  it("uses the custom label when provided", () => {
    const { getByText } = render(<StatusBadge status="failed" label="Crashed" />);
    expect(getByText("Crashed")).toBeInTheDocument();
  });

  it.each([
    "pending",
    "analyzing",
    "ready",
    "failed",
    "queued",
    "running",
    "succeeded",
    "cancelled",
  ] as const)("renders status %s without throwing", (status) => {
    const { container } = render(<StatusBadge status={status} />);
    const el = container.querySelector(`[data-status="${status}"]`);
    expect(el).not.toBeNull();
  });
});
