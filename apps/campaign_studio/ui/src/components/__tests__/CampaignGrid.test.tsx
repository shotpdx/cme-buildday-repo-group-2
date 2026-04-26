import { describe, it, expect, vi } from "vitest";
import { render, screen, act } from "@testing-library/react";
import CampaignGrid from "../CampaignGrid";
import { MockEventSource } from "../../test/setup";

describe("CampaignGrid", () => {
  const campaign = {
    campaign_id: "camp-xyz",
    filter: { primary_segment: "Sports Enthusiast" },
  };

  it("renders four skeleton tiles initially", () => {
    render(<CampaignGrid campaign={campaign} />);

    const tiles = screen.getAllByTestId(/^tile-/);
    expect(tiles).toHaveLength(4);
    tiles.forEach((t) => {
      expect(t.getAttribute("data-status")).toBe("skeleton");
    });
  });

  it("replaces a skeleton with a ready tile when an SSE 'tile' event arrives", async () => {
    const onComplete = vi.fn();
    render(<CampaignGrid campaign={campaign} onComplete={onComplete} />);

    // The component opens an EventSource on mount; grab the most recent.
    const es = MockEventSource.instances.at(-1)!;
    expect(es.url).toBe(`/campaigns/${campaign.campaign_id}/events`);

    act(() => {
      es.emit("tile", {
        format: "social_square",
        image_path: "",
        copy: "A bold match-day headline",
      });
    });

    const tile = screen.getByTestId("tile-social_square");
    expect(tile.getAttribute("data-status")).toBe("ready");
    expect(tile).toHaveTextContent("A bold match-day headline");

    // Other three still skeleton.
    expect(
      screen.getByTestId("tile-vertical_story").getAttribute("data-status"),
    ).toBe("skeleton");

    // 'done' triggers onComplete.
    act(() => {
      es.emit("done", { campaign_id: campaign.campaign_id });
    });
    expect(onComplete).toHaveBeenCalled();
  });
});
