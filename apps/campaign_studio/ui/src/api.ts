// Campaign Studio API client.
//
// The backend is a FastAPI app mounted at the root (no "/api" prefix). In
// local dev, Vite proxies "/campaigns" → http://localhost:8000. The shape
// of the SSE snippet below follows the reference in the campaign-studio-
// pattern skill but with the real backend path ("/campaigns", not
// "/api/campaigns").

export type FormatName =
  | "social_square"
  | "vertical_story"
  | "display_banner"
  | "email_header"
  | string;

export interface SegmentFilter {
  primary_segment?: string;
  value_segment?: string;
  top_genre_1?: string;
  churn_risk_category?: string;
}

export interface CreateCampaignResponse {
  campaign_id: string;
}

export interface Campaign {
  campaign_id: string;
  filter: SegmentFilter;
}

// Emitted by the backend's SSE "tile" event. See app.py::_run_campaign.
export interface Tile {
  format: FormatName;
  image_path: string;
  copy: string;
}

// Returned by POST /campaigns/{id}/regenerate/{format}.
export interface RegeneratedAsset {
  image_path: string;
  copy: string;
  latency_s: number;
}

export type Quality = "low" | "medium";

export async function createCampaign(
  filter: SegmentFilter,
): Promise<CreateCampaignResponse> {
  const res = await fetch("/campaigns", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ segment_filter: filter }),
  });
  if (!res.ok) {
    throw new Error(`createCampaign failed: ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as CreateCampaignResponse;
}

// Minimal SSE consumer. Reference shape from the campaign-studio-pattern
// skill's sse_client_snippet.ts, adapted to the real backend path
// (no "/api" prefix). Returns an unsubscribe function.
export function subscribeCampaign(
  campaignId: string,
  onTile: (t: Tile) => void,
  onDone: () => void,
  onError?: (e: Event) => void,
): () => void {
  const es = new EventSource(`/campaigns/${campaignId}/events`);
  es.addEventListener("tile", (e) => {
    const msg = e as MessageEvent<string>;
    onTile(JSON.parse(msg.data) as Tile);
  });
  es.addEventListener("done", () => {
    onDone();
    es.close();
  });
  es.addEventListener("error", (e) => {
    if (onError) onError(e);
    // EventSource auto-reconnects on transport errors; only close on
    // hard failures (readyState === CLOSED).
    if (es.readyState === EventSource.CLOSED) {
      es.close();
    }
  });
  return () => es.close();
}

export async function regenerateFormat(
  campaignId: string,
  format: FormatName,
  quality: Quality,
): Promise<RegeneratedAsset> {
  const res = await fetch(`/campaigns/${campaignId}/regenerate/${format}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ quality }),
  });
  if (!res.ok) {
    throw new Error(`regenerateFormat failed: ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as RegeneratedAsset;
}

export async function approveCampaign(campaignId: string): Promise<void> {
  const res = await fetch(`/campaigns/${campaignId}/approve`, {
    method: "POST",
  });
  if (!res.ok && res.status !== 204) {
    throw new Error(`approveCampaign failed: ${res.status} ${res.statusText}`);
  }
}

export function exportCampaignUrl(campaignId: string): string {
  return `/campaigns/${campaignId}/export`;
}
