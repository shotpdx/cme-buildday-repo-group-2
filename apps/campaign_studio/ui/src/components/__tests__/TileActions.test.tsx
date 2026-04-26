import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import TileActions from "../TileActions";

describe("TileActions", () => {
  it("renders the low/medium toggle and regenerate button", () => {
    render(
      <TileActions formatName="social_square" onRegenerate={() => {}} />,
    );

    expect(screen.getByRole("button", { name: /low/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /med/i })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /regenerate/i }),
    ).toBeInTheDocument();
    // Low is the default pressed state.
    expect(screen.getByRole("button", { name: /low/i })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("regenerates at the currently-toggled quality", async () => {
    const user = userEvent.setup();
    const onRegenerate = vi.fn();

    render(
      <TileActions
        formatName="social_square"
        onRegenerate={onRegenerate}
      />,
    );

    await user.click(screen.getByRole("button", { name: /med/i }));
    await user.click(screen.getByRole("button", { name: /regenerate/i }));

    expect(onRegenerate).toHaveBeenCalledTimes(1);
    expect(onRegenerate).toHaveBeenCalledWith("medium");
  });
});
