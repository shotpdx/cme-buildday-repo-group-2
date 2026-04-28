import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import SegmentFilter from "../SegmentFilter";

describe("SegmentFilter", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(JSON.stringify({ campaign_id: "abc-123" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders all four segment pickers", () => {
    render(<SegmentFilter onSubmit={() => {}} />);

    expect(screen.getByLabelText(/primary segment/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/value segment/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/top genre/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/churn risk/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /generate campaign/i }),
    ).toBeInTheDocument();
  });

  it("submits selections to POST /campaigns and invokes onSubmit with response", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();

    render(<SegmentFilter onSubmit={onSubmit} />);

    await user.selectOptions(
      screen.getByLabelText(/primary segment/i),
      "Sports Enthusiast",
    );
    await user.selectOptions(screen.getByLabelText(/churn risk/i), "medium");
    await user.click(
      screen.getByRole("button", { name: /generate campaign/i }),
    );

    const fetchMock = (globalThis as unknown as { fetch: ReturnType<typeof vi.fn> })
      .fetch;
    expect(fetchMock).toHaveBeenCalledWith(
      "/campaigns",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          segment_filter: {
            primary_segment: "Sports Enthusiast",
            churn_risk_category: "medium",
          },
        }),
      }),
    );

    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({ campaign_id: "abc-123" }),
    );
  });
});
