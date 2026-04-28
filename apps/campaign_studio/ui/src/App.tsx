import { useCallback, useState } from "react";
import "./styles.css";
import SegmentFilter from "./components/SegmentFilter";
import CampaignGrid from "./components/CampaignGrid";
import {
  approveCampaign,
  exportCampaignUrl,
  type Campaign,
} from "./api";

export default function App() {
  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [complete, setComplete] = useState(false);
  const [approved, setApproved] = useState(false);

  const handleSubmit = useCallback((c: Campaign) => {
    setCampaign(c);
    setComplete(false);
    setApproved(false);
  }, []);

  const handleApprove = useCallback(async () => {
    if (!campaign) return;
    await approveCampaign(campaign.campaign_id);
    setApproved(true);
  }, [campaign]);

  const handleExport = useCallback(() => {
    if (!campaign) return;
    window.location.href = exportCampaignUrl(campaign.campaign_id);
  }, [campaign]);

  const shortId = campaign ? campaign.campaign_id.slice(0, 8) : null;

  return (
    <div className="studio">
      <header className="studio__masthead">
        <h1>Campaign Studio</h1>
        <span className="kicker">
          Editorial · Data-room · {shortId ? `id ${shortId}` : "idle"}
        </span>
      </header>

      <aside className="studio__aside">
        <SegmentFilter onSubmit={handleSubmit} />
      </aside>

      <main className="studio__main">
        {!campaign ? (
          <div className="campaign-empty">
            Pick an audience to brief the creative engine. Four formats will
            fan out in parallel.
          </div>
        ) : (
          <>
            <div className="campaign-header">
              <h2 className="campaign-header__title">Creative fan-out</h2>
              <span className="campaign-header__meta">
                {complete ? "Rendered · 4 of 4" : "Rendering…"}
              </span>
            </div>

            <CampaignGrid
              campaign={campaign}
              onComplete={() => setComplete(true)}
            />

            <footer className="footer">
              <span className="footer__status">
                {approved
                  ? "Approved · ready to ship"
                  : complete
                    ? "Ready for review"
                    : "Awaiting renders…"}
              </span>
              <div className="footer__spacer" />
              <button
                type="button"
                className="btn-secondary"
                disabled={!complete}
                onClick={handleExport}
              >
                Export zip
              </button>
              <button
                type="button"
                className="btn-primary"
                disabled={!complete || approved}
                onClick={handleApprove}
              >
                {approved ? "Approved" : "Approve campaign"}
              </button>
            </footer>
          </>
        )}
      </main>
    </div>
  );
}
