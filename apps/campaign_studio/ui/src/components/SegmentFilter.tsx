import { useState } from "react";
import {
  createCampaign,
  type Campaign,
  type SegmentFilter as Filter,
} from "../api";

const PRIMARY_SEGMENTS = [
  "Sports Enthusiast",
  "News Consumer",
  "Entertainment Seeker",
  "Casual Browser",
  "Digital Native",
];

const VALUE_SEGMENTS = [
  "Premium Engaged",
  "High Value",
  "Standard",
  "Conversion Target",
  "At Risk",
  "Churned",
];

const TOP_GENRES = [
  "Sports",
  "News",
  "Drama",
  "Comedy",
  "Documentary",
  "Reality",
  "Kids",
  "Entertainment",
];

const CHURN_RISKS = ["low", "medium", "high"];

interface Props {
  onSubmit: (campaign: Campaign) => void;
  disabled?: boolean;
}

export default function SegmentFilter({ onSubmit, disabled }: Props) {
  const [primary, setPrimary] = useState("");
  const [value, setValue] = useState("");
  const [genre, setGenre] = useState("");
  const [churn, setChurn] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (busy) return;
    const filter: Filter = {};
    if (primary) filter.primary_segment = primary;
    if (value) filter.value_segment = value;
    if (genre) filter.top_genre_1 = genre;
    if (churn) filter.churn_risk_category = churn;

    setBusy(true);
    setError(null);
    try {
      const resp = await createCampaign(filter);
      onSubmit({ campaign_id: resp.campaign_id, filter });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="filter" onSubmit={handleSubmit} aria-label="Segment filter">
      <div>
        <h2 className="filter__title">Audience</h2>
        <p className="filter__subtitle">Compose a virtual segment</p>
      </div>

      <Field
        id="primary_segment"
        label="Primary segment"
        value={primary}
        onChange={setPrimary}
        options={PRIMARY_SEGMENTS}
      />
      <Field
        id="value_segment"
        label="Value segment"
        value={value}
        onChange={setValue}
        options={VALUE_SEGMENTS}
      />
      <Field
        id="top_genre_1"
        label="Top genre"
        value={genre}
        onChange={setGenre}
        options={TOP_GENRES}
      />
      <Field
        id="churn_risk_category"
        label="Churn risk"
        value={churn}
        onChange={setChurn}
        options={CHURN_RISKS}
      />

      <button
        className="filter__submit"
        type="submit"
        disabled={busy || disabled}
      >
        {busy ? "Spinning up…" : "Generate campaign"}
      </button>

      {error ? (
        <p role="alert" style={{ color: "var(--accent)", fontSize: 12 }}>
          {error}
        </p>
      ) : null}
    </form>
  );
}

interface FieldProps {
  id: string;
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: string[];
}

function Field({ id, label, value, onChange, options }: FieldProps) {
  return (
    <div className="filter__field">
      <label className="filter__label" htmlFor={id}>
        {label}
      </label>
      <select
        id={id}
        className="filter__select"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">Any</option>
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    </div>
  );
}
