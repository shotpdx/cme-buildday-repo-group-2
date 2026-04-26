import { useState } from "react";
import type { Quality } from "../api";

interface Props {
  formatName: string;
  busy?: boolean;
  onRegenerate: (quality: Quality) => void;
  onApprove?: () => void;
  onExport?: () => void;
}

export default function TileActions({
  formatName,
  busy,
  onRegenerate,
  onApprove,
  onExport,
}: Props) {
  const [quality, setQuality] = useState<Quality>("low");

  return (
    <div
      className="tile__actions"
      aria-label={`Actions for ${formatName}`}
    >
      <div className="actions__group" role="group" aria-label="Quality">
        <button
          type="button"
          aria-pressed={quality === "low"}
          className={quality === "low" ? "actions__group--active" : ""}
          onClick={() => setQuality("low")}
        >
          Low
        </button>
        <button
          type="button"
          aria-pressed={quality === "medium"}
          className={quality === "medium" ? "actions__group--active" : ""}
          onClick={() => setQuality("medium")}
        >
          Med
        </button>
      </div>

      <button
        type="button"
        className="btn-ghost"
        disabled={busy}
        onClick={() => onRegenerate(quality)}
      >
        {busy ? "Regenerating…" : "Regenerate"}
      </button>

      <div className="actions__spacer" />

      {onApprove ? (
        <button type="button" className="btn-ghost" onClick={onApprove}>
          Approve
        </button>
      ) : null}
      {onExport ? (
        <button type="button" className="btn-ghost" onClick={onExport}>
          Export
        </button>
      ) : null}
    </div>
  );
}
