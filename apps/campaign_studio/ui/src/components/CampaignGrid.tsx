import { useCallback, useEffect, useMemo, useState } from "react";
import {
  regenerateFormat,
  subscribeCampaign,
  type Campaign,
  type FormatName,
  type Quality,
  type Tile,
} from "../api";
import TileActions from "./TileActions";

// Canonical 4-up format list. In production this would come from the
// backend's /campaigns response, but the backend currently only returns
// {campaign_id}. The format names below match app.py::FORMATS.
const FORMATS: FormatName[] = [
  "social_square",
  "vertical_story",
  "display_banner",
  "email_header",
];

type TileState =
  | { status: "skeleton"; format: FormatName }
  | { status: "ready"; format: FormatName; tile: Tile; regenBusy?: boolean };

interface Props {
  campaign: Campaign;
  onComplete?: () => void;
}

export default function CampaignGrid({ campaign, onComplete }: Props) {
  const initial: TileState[] = useMemo(
    () => FORMATS.map((f) => ({ status: "skeleton", format: f })),
    [],
  );
  const [tiles, setTiles] = useState<TileState[]>(initial);

  // Reset tiles whenever the campaign_id changes (new generation).
  useEffect(() => {
    setTiles(FORMATS.map((f) => ({ status: "skeleton", format: f })));
  }, [campaign.campaign_id]);

  useEffect(() => {
    const unsubscribe = subscribeCampaign(
      campaign.campaign_id,
      (tile) => {
        setTiles((prev) =>
          prev.map((t) =>
            t.format === tile.format
              ? { status: "ready", format: t.format, tile }
              : t,
          ),
        );
      },
      () => {
        onComplete?.();
      },
    );
    return unsubscribe;
  }, [campaign.campaign_id, onComplete]);

  const handleRegenerate = useCallback(
    async (format: FormatName, quality: Quality) => {
      setTiles((prev) =>
        prev.map((t) =>
          t.format === format && t.status === "ready"
            ? { ...t, regenBusy: true }
            : t,
        ),
      );
      try {
        const asset = await regenerateFormat(
          campaign.campaign_id,
          format,
          quality,
        );
        setTiles((prev) =>
          prev.map((t) =>
            t.format === format
              ? {
                  status: "ready",
                  format,
                  tile: {
                    format,
                    image_path: asset.image_path,
                    copy: asset.copy,
                  },
                  regenBusy: false,
                }
              : t,
          ),
        );
      } catch {
        setTiles((prev) =>
          prev.map((t) =>
            t.format === format && t.status === "ready"
              ? { ...t, regenBusy: false }
              : t,
          ),
        );
      }
    },
    [campaign.campaign_id],
  );

  return (
    <div className="grid" data-testid="campaign-grid">
      {tiles.map((t) =>
        t.status === "skeleton" ? (
          <SkeletonTile key={t.format} format={t.format} />
        ) : (
          <ReadyTile
            key={t.format}
            state={t}
            onRegenerate={(q) => handleRegenerate(t.format, q)}
          />
        ),
      )}
    </div>
  );
}

function SkeletonTile({ format }: { format: FormatName }) {
  return (
    <article
      className="tile tile--skeleton"
      aria-label={`${format} loading`}
      data-testid={`tile-${format}`}
      data-status="skeleton"
    >
      <span className="tile__label">{format.replace(/_/g, " ")}</span>
      <div className="tile__canvas">
        <div className="tile__copy-skel" aria-hidden>
          <span />
          <span />
        </div>
      </div>
    </article>
  );
}

function ReadyTile({
  state,
  onRegenerate,
}: {
  state: Extract<TileState, { status: "ready" }>;
  onRegenerate: (quality: Quality) => void;
}) {
  const { tile, format, regenBusy } = state;
  return (
    <article
      className="tile"
      data-testid={`tile-${format}`}
      data-status="ready"
    >
      <span className="tile__label">{format.replace(/_/g, " ")}</span>
      <div className="tile__canvas">
        <TileImage src={tile.image_path} alt={tile.copy} />
        <p className="tile__copy">{tile.copy}</p>
      </div>
      <TileActions
        formatName={format}
        busy={regenBusy}
        onRegenerate={onRegenerate}
      />
    </article>
  );
}

// Paths from the backend are filesystem paths (e.g. /Volumes/...). For the
// demo, we try to load them as-is and fall back to a placeholder on error.
function TileImage({ src, alt }: { src: string; alt: string }) {
  const [broken, setBroken] = useState(false);
  if (broken || !src) {
    return (
      <div
        aria-hidden
        style={{
          width: "100%",
          height: "100%",
          background:
            "radial-gradient(circle at 30% 30%, rgba(255,54,86,0.2), transparent 60%), #1b1b27",
        }}
      />
    );
  }
  return <img src={src} alt={alt} onError={() => setBroken(true)} />;
}
