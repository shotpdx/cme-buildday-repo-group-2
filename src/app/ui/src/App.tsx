import {
  Bot,
  CheckCircle2,
  ChevronDown,
  CircleDollarSign,
  ClipboardCheck,
  Clock3,
  FileText,
  Gauge,
  LayoutDashboard,
  ListChecks,
  MessageCircle,
  Play,
  RefreshCcw,
  Search,
  Send,
  Settings,
  ShieldCheck,
  SlidersHorizontal,
  Table2,
  TriangleAlert,
  UserCircle,
  Zap
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

type SignalStatus = "new" | "investigating" | "actioned" | "review_required";
type SignalSeverity = "low" | "medium" | "high" | "critical";
type ActionRisk = "low" | "medium" | "high";
type ActionDecision = "auto_simulate" | "review_required" | "blocked";
type ViewId = "command" | "workbench" | "matrix" | "activation" | "leadership" | "settings";

interface SignalListItem {
  signal_id: string;
  title: string;
  status: SignalStatus;
  severity: SignalSeverity;
  segment: string;
  detected_at: string;
  affected_customers: number;
  churn_delta: number;
  churn_risk_score: number;
  content_engagement_score: number;
  billing_friction_score: number;
  signal_drivers: string[];
  estimated_value_at_risk: number;
}

interface NbaActionCandidate {
  action_id: string;
  action_name: string;
  action_type: string;
  channel: string;
  cost_per_delivery: number;
  expected_lift: number;
  rank: number;
  risk_level: ActionRisk;
  target_count: number;
  rationale: string;
  is_offer: boolean;
  holdout_blocked: boolean;
}

interface SignalIncident extends SignalListItem {
  summary: string;
  root_causes: string[];
  recommended_actions: NbaActionCandidate[];
  evidence: string[];
}

interface PolicyConfig {
  var_threshold: number;
  auto_risk_levels: ActionRisk[];
  max_auto_actions: number;
  require_human_for_offers: boolean;
}

interface PolicyDecision {
  action: NbaActionCandidate;
  decision: ActionDecision;
  reasons: string[];
}

interface SupervisorToolCall {
  name: string;
  input: string;
  output: string;
}

interface InvestigationResult {
  signal_id: string;
  supervisor_endpoint: string;
  summary: string;
  tool_calls: SupervisorToolCall[];
  recommended_focus: string[];
}

interface ActivationResult {
  signal_id: string;
  activated_count: number;
  review_required_count: number;
  records: {
    activation_id: string;
    action_id: string;
    action_name: string;
    channel: string;
    target_count: number;
    estimated_cost: number;
    simulation_only: boolean;
    created_at: string;
  }[];
  decisions: PolicyDecision[];
}

interface AppState {
  signals: SignalListItem[];
  signal: SignalIncident | null;
  policy: PolicyConfig | null;
  investigation: InvestigationResult | null;
  activation: ActivationResult | null;
  policyDecisions: PolicyDecision[];
  busyAction: "investigate" | "activate" | "refresh" | null;
  selectedSignalId: string;
  setSelectedSignalId: (signalId: string) => void;
  refreshAll: () => Promise<void>;
  investigate: () => Promise<void>;
  activate: () => Promise<void>;
  patchPolicy: (patch: Partial<PolicyConfig>) => Promise<void>;
}

const statusLabel: Record<SignalStatus, string> = {
  new: "New",
  investigating: "Investigating",
  actioned: "Actioned",
  review_required: "Review"
};

const navItems: { id: ViewId; label: string; shortLabel: string; icon: typeof LayoutDashboard }[] = [
  { id: "command", label: "Command Center", shortLabel: "Command Center", icon: LayoutDashboard },
  { id: "workbench", label: "Agent Workbench", shortLabel: "Workbench", icon: Bot },
  { id: "matrix", label: "Decision Matrix", shortLabel: "Decisions", icon: Table2 },
  { id: "activation", label: "Activation Console", shortLabel: "Activations", icon: ClipboardCheck },
  { id: "settings", label: "Settings", shortLabel: "Settings", icon: Settings }
];

const API_BASE = "";

async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

async function apiSend<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init
  });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

export function App() {
  const [activeView, setActiveView] = useState<ViewId>(() => parseViewFromHash());
  const [signals, setSignals] = useState<SignalListItem[]>([]);
  const [selectedSignalId, setSelectedSignalId] = useState<string>("");
  const [signal, setSignal] = useState<SignalIncident | null>(null);
  const [policy, setPolicy] = useState<PolicyConfig | null>(null);
  const [investigation, setInvestigation] = useState<InvestigationResult | null>(null);
  const [activation, setActivation] = useState<ActivationResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyAction, setBusyAction] = useState<"investigate" | "activate" | "refresh" | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void refreshAll();
  }, []);

  useEffect(() => {
    const handleHashChange = () => setActiveView(parseViewFromHash());
    handleHashChange();
    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  useEffect(() => {
    if (!selectedSignalId) return;
    void loadSignal(selectedSignalId);
  }, [selectedSignalId]);

  const policyDecisions = useMemo(() => {
    const currentActivation = activation;
    if (currentActivation && currentActivation.signal_id === signal?.signal_id) {
      return currentActivation.decisions;
    }
    return signal?.recommended_actions.map((action) => ({
      action,
      decision: previewDecision(action, policy),
      reasons: previewReasons(action, policy)
    })) ?? [];
  }, [activation, policy, signal]);

  async function refreshAll() {
    setBusyAction("refresh");
    setError(null);
    try {
      const [signalList, nextPolicy] = await Promise.all([
        apiGet<SignalListItem[]>("/api/signals"),
        apiGet<PolicyConfig>("/api/policy")
      ]);
      setSignals(signalList);
      setPolicy(nextPolicy);
      const first = selectedSignalId || signalList[0]?.signal_id || "";
      setSelectedSignalId(first);
      if (first) {
        await loadSignal(first);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load NBA engine state");
    } finally {
      setLoading(false);
      setBusyAction(null);
    }
  }

  async function loadSignal(signalId: string) {
    setError(null);
    try {
      const nextSignal = await apiGet<SignalIncident>(`/api/signals/${signalId}`);
      setSignal(nextSignal);
      setInvestigation((current) => (current?.signal_id === signalId ? current : null));
      setActivation((current) => (current?.signal_id === signalId ? current : null));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load signal");
    }
  }

  async function patchPolicy(patch: Partial<PolicyConfig>) {
    setError(null);
    try {
      const nextPolicy = await apiSend<PolicyConfig>("/api/policy", {
        method: "PATCH",
        body: JSON.stringify(patch)
      });
      setPolicy(nextPolicy);
      setActivation(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update policy");
    }
  }

  async function investigate() {
    if (!signal) return;
    setBusyAction("investigate");
    setError(null);
    try {
      const result = await apiSend<InvestigationResult>(`/api/signals/${signal.signal_id}/investigate`, {
        method: "POST"
      });
      setInvestigation(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Supervisor investigation failed");
    } finally {
      setBusyAction(null);
    }
  }

  async function activate() {
    if (!signal) return;
    setBusyAction("activate");
    setError(null);
    try {
      const result = await apiSend<ActivationResult>(`/api/signals/${signal.signal_id}/activate`, {
        method: "POST"
      });
      setActivation(result);
      const nextSignals = await apiGet<SignalListItem[]>("/api/signals");
      setSignals(nextSignals);
      await loadSignal(signal.signal_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Agent deployment failed");
    } finally {
      setBusyAction(null);
    }
  }

  const appState: AppState = {
    signals,
    signal,
    policy,
    investigation,
    activation,
    policyDecisions,
    busyAction,
    selectedSignalId,
    setSelectedSignalId,
    refreshAll,
    investigate,
    activate,
    patchPolicy
  };

  if (loading) {
    return (
      <Shell activeView={activeView} onViewChange={setActiveView}>
        <LoadingState />
      </Shell>
    );
  }

  return (
    <Shell activeView={activeView} onViewChange={setActiveView}>
      <Topbar title={navItems.find((item) => item.id === activeView)?.label ?? "Command Center"} state={appState} />
      {error ? <div className="error-bar"><TriangleAlert size={16} />{error}</div> : null}
      {activeView === "command" ? <CommandCenterView state={appState} /> : null}
      {activeView === "workbench" ? <AgentWorkbenchView state={appState} /> : null}
      {activeView === "matrix" ? <DecisionMatrixView state={appState} /> : null}
      {activeView === "activation" ? <ActivationConsoleView state={appState} /> : null}
      {activeView === "settings" ? <SettingsView state={appState} /> : null}
    </Shell>
  );
}

function Shell({
  activeView,
  onViewChange,
  children
}: {
  activeView: ViewId;
  onViewChange: (view: ViewId) => void;
  children: React.ReactNode;
}) {
  return (
    <div className="app-frame">
      <aside className="product-sidebar">
        <div className="brand-block">
          <div className="brand-mark">CME</div>
          <div>
            <strong>Next Best Actions</strong>
            <span>Decisioning Engine</span>
          </div>
        </div>
        <nav className="product-nav" aria-label="Workspace">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                type="button"
                className={activeView === item.id ? "nav-item active" : "nav-item"}
                onClick={() => {
                  window.location.hash = item.id;
                  onViewChange(item.id);
                }}
              >
                <Icon size={17} />
                <span>{item.shortLabel}</span>
              </button>
            );
          })}
        </nav>
        <div className="sidebar-footer">
          <span>Agent Autopilot</span>
          <strong>Sandbox mode</strong>
        </div>
      </aside>
      <div className="app-main">{children}</div>
    </div>
  );
}

function Topbar({ title, state }: { title: string; state: AppState }) {
  const { signal, busyAction, refreshAll } = state;
  return (
    <header className="topbar">
      <div>
        <p className="eyebrow">Next Best Actions Engine <ChevronDown size={13} /></p>
        <h1>{title}</h1>
      </div>
      <div className="topbar-actions">
        {signal ? <StatusBadge label={signal.status.replace("_", " ")} tone={signal.status} /> : null}
        <button className="secondary-button" title="Generate Report"><FileText size={17} />Report</button>
        <button className="icon-button" onClick={refreshAll} disabled={busyAction === "refresh"} title="Refresh">
          <RefreshCcw size={18} />
        </button>
        <div className="user-chip">
          <UserCircle size={22} />
          <span>Alex Morgan</span>
        </div>
      </div>
    </header>
  );
}

function CommandCenterView({ state }: { state: AppState }) {
  const { signal, policyDecisions, investigate, activate, busyAction } = state;
  return (
    <main className="page-grid command-layout-simple">
      <SignalQueue state={state} />
      <section className="signal-detail">
        {signal ? (
          <>
            <CaseHeader signal={signal} busyAction={busyAction} onInvestigate={investigate} onActivate={activate} />
            <MetricsGrid signal={signal} />
            <div className="summary-band">
              <p>{signal.summary}</p>
              <ul className="root-cause-list">
                {signal.root_causes.map((cause) => <li key={cause}>{cause}</li>)}
              </ul>
            </div>
            <DecisionMatrix decisions={policyDecisions} compact />
          </>
        ) : (
          <LoadingState />
        )}
      </section>
    </main>
  );
}

function AgentWorkbenchView({ state }: { state: AppState }) {
  const { signal, investigation } = state;
  return (
    <main className="workbench-simple">
      {signal ? (
        <>
          <CaseHeader signal={signal} busyAction={state.busyAction} onInvestigate={state.investigate} onActivate={state.activate} />
          <div className="workbench-columns">
            <div className="workbench-left">
              <AgentPanel state={state} large />
              <ToolCallTable investigation={investigation} />
            </div>
            <GenieChat signal={signal} />
          </div>
        </>
      ) : <LoadingState />}
    </main>
  );
}

interface ChatMessage {
  id: string;
  role: "user" | "genie";
  text: string;
}

function GenieChat({ signal }: { signal: SignalIncident }) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    { id: "welcome", role: "genie", text: `I'm your Genie assistant for this signal. Ask me anything about the ${formatNumber(signal.affected_customers)} affected customers, root causes, or recommended actions.` },
    { id: "q1", role: "user", text: "Have these customers interacted with support recently?" },
    { id: "a1", role: "genie", text: `Of the ${formatNumber(signal.affected_customers)} customers in this signal, approximately 34% have opened a support ticket in the last 30 days — primarily around billing issues and content availability complaints.\n\nThis is 2.1x the baseline rate for the broader subscriber population, suggesting support friction is a contributing churn driver for this cohort.` }
  ]);
  const [input, setInput] = useState("");
  const [typing, setTyping] = useState(false);
  const bottomRef = { current: null as HTMLDivElement | null };

  function generateResponse(question: string): string {
    const q = question.toLowerCase();
    if (q.includes("root cause") || q.includes("why")) {
      return `Based on the signal analysis, the primary root causes are:\n\n${signal.root_causes.map((rc, i) => `${i + 1}. ${rc}`).join("\n")}\n\nThe churn delta is ${formatPercent(signal.churn_delta)}, with content engagement at ${formatScore(signal.content_engagement_score)} and billing friction at ${formatScore(signal.billing_friction_score)}.`;
    }
    if (q.includes("action") || q.includes("recommend") || q.includes("what should")) {
      const top3 = signal.recommended_actions.slice(0, 3);
      return `Here are the top recommended actions:\n\n${top3.map((a, i) => `${i + 1}. **${a.action_name}** — ${a.rationale} (${formatNumber(a.target_count)} users, ${a.channel})`).join("\n")}\n\nThe agent will auto-approve actions within your VaR threshold and flag the rest for your review.`;
    }
    if (q.includes("customer") || q.includes("who") || q.includes("segment") || q.includes("audience")) {
      return `This signal affects **${formatNumber(signal.affected_customers)} customers** in the "${signal.segment}" segment. Key drivers: ${signal.signal_drivers.join(", ")}. The estimated value at risk is ${formatMoney(signal.estimated_value_at_risk)}.`;
    }
    if (q.includes("risk") || q.includes("var") || q.includes("value at risk")) {
      return `The total estimated value at risk is **${formatMoney(signal.estimated_value_at_risk)}**. The churn risk score is ${formatScore(signal.churn_risk_score)}. Actions are gated by total VaR — those exceeding your threshold require your approval before the agent can execute.`;
    }
    if (q.includes("investigate") || q.includes("agent")) {
      return `Click "Investigate" to have the agent perform a deep-dive analysis using SQL queries and data tools. It will surface evidence, confirm root causes, and refine the action recommendations based on what it finds in the data.`;
    }
    return `For the current signal ("${signal.title}"), I can help with:\n\n- **Root causes** — why are these customers churning?\n- **Recommended actions** — what should we do?\n- **Customer segment** — who is affected?\n- **Risk analysis** — what's at stake?\n\nAsk me about any of these topics.`;
  }

  function handleSend() {
    const trimmed = input.trim();
    if (!trimmed) return;
    const userMsg: ChatMessage = { id: `u-${Date.now()}`, role: "user", text: trimmed };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setTyping(true);
    setTimeout(() => {
      const response = generateResponse(trimmed);
      const genieMsg: ChatMessage = { id: `g-${Date.now()}`, role: "genie", text: response };
      setMessages((prev) => [...prev, genieMsg]);
      setTyping(false);
    }, 800 + Math.random() * 600);
  }

  return (
    <section className="panel genie-chat">
      <div className="section-heading">
        <span><MessageCircle size={18} />Genie</span>
      </div>
      <div className="chat-messages">
        {messages.map((msg) => (
          <div key={msg.id} className={`chat-bubble ${msg.role}`}>
            {msg.role === "genie" ? <Bot size={14} className="chat-avatar" /> : null}
            <span>{msg.text}</span>
          </div>
        ))}
        {typing ? <div className="chat-bubble genie typing"><Bot size={14} className="chat-avatar" /><span>Thinking...</span></div> : null}
        <div ref={(el) => { bottomRef.current = el; el?.scrollIntoView({ behavior: "smooth" }); }} />
      </div>
      <form className="chat-input-row" onSubmit={(e) => { e.preventDefault(); handleSend(); }}>
        <input
          type="text"
          placeholder="Ask about this signal..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
        />
        <button type="submit" disabled={!input.trim()}>
          <Send size={16} />
        </button>
      </form>
    </section>
  );
}

function DecisionMatrixView({ state }: { state: AppState }) {
  return (
    <main className="matrix-simple">
      <PolicyControlStrip policy={state.policy} patchPolicy={state.patchPolicy} />
      <section className="panel matrix-page">
        <div className="section-heading spread">
          <span><Table2 size={18} />Recommended Actions</span>
          <span className="table-note">Ranked against active policy</span>
        </div>
        <DecisionMatrix decisions={state.policyDecisions} />
        <DecisionSummary decisions={state.policyDecisions} />
      </section>
    </main>
  );
}

function ActivationConsoleView({ state }: { state: AppState }) {
  const review = state.policyDecisions.filter((decision) => decision.decision === "review_required");
  const auto = state.policyDecisions.filter((decision) => decision.decision === "auto_simulate");
  return (
    <main className="activation-simple">
      <section className="activation-kpis-simple">
        <div className="kpi-card">
          <span>Value Protected</span>
          <strong>{formatMoney(sumValueAtRisk(auto))}</strong>
        </div>
        <div className="kpi-card">
          <span>Agent Actions</span>
          <strong>{state.activation?.activated_count ?? auto.length}</strong>
        </div>
        <div className="kpi-card">
          <span>Pending Approvals</span>
          <strong>{review.length}</strong>
        </div>
      </section>

      <section className="panel">
        <div className="section-heading spread">
          <span><Play size={18} />Agent Activation</span>
          <button className="primary-button" onClick={state.activate} disabled={state.busyAction === "activate"}>
            <Play size={17} />
            {state.busyAction === "activate" ? "Deploying..." : "Deploy Agent"}
          </button>
        </div>
        <RecentAutoActions decisions={auto} activation={state.activation} signal={state.signal} />
      </section>

      <section className="panel">
        <div className="section-heading spread">
          <span><ListChecks size={18} />Approval Queue</span>
          {review.length > 0 ? <StatusBadge label={`${review.length}`} tone="review_required" /> : null}
        </div>
        <div className="approval-list">
          {review.map((decision) => (
            <div className="approval-item" key={decision.action.action_id}>
              <strong>{decision.action.action_name}</strong>
              <span>{formatMoney(actionValueAtRisk(decision.action))} value at risk / {decision.action.risk_level} risk</span>
              <StatusBadge label="Review Required" tone="review_required" />
              <button className="secondary-button mini-action">Review</button>
            </div>
          ))}
          {review.length === 0 ? <EmptyState label="No actions waiting for approval" /> : null}
        </div>
      </section>
    </main>
  );
}


function SettingsView({ state }: { state: AppState }) {
  const { policy, patchPolicy } = state;
  return (
    <main className="page-grid settings-layout">
      <section className="panel settings-page">
        <div className="section-heading">
          <span><SlidersHorizontal size={18} />Autopilot Policy</span>
        </div>
        <p className="settings-description">
          Configure thresholds that determine which actions the agent can execute autonomously versus those routed for human review.
          Actions whose total value at risk exceeds the threshold require manual approval.
        </p>
        {policy ? <PolicyEditor policy={policy} onChange={patchPolicy} /> : <LoadingState />}
      </section>
    </main>
  );
}

function SignalQueue({ state }: { state: AppState }) {
  return (
    <aside className="signal-queue" aria-label="Signal Queue">
      <div className="section-heading spread">
        <span><Zap size={18} />Signal Queue</span>
        <strong>{state.signals.length}</strong>
      </div>
      <div className="signal-list">
        {state.signals.map((item) => (
          <button
            key={item.signal_id}
            className={`signal-item ${item.signal_id === state.selectedSignalId ? "selected" : ""}`}
            onClick={() => state.setSelectedSignalId(item.signal_id)}
          >
            <span className={`severity-dot ${item.severity}`} />
            <span className="signal-title">
              {item.title}
              <StatusBadge label={statusLabel[item.status]} tone={item.status} />
            </span>
            <span className="signal-meta">{item.segment}</span>
            <span className="signal-row">
              <span>{formatNumber(item.affected_customers)} customers</span>
              <span>{formatPercent(item.churn_delta)} delta</span>
            </span>
            <span className="signal-row muted">
              <span>{formatMoney(item.estimated_value_at_risk)} at risk</span>
              <span>{formatRelative(item.detected_at)}</span>
            </span>
          </button>
        ))}
      </div>
    </aside>
  );
}







function ToolCallTable({ investigation }: { investigation: InvestigationResult | null }) {
  const rows = investigation?.tool_calls.length
    ? investigation.tool_calls.map((call, index) => ({
      time: `${14 - index}m`,
      tool: call.name,
      input: call.input || "signal context",
      status: "Success"
    }))
    : [
      { time: "14m", tool: "nba_signal_analytics.get_cohort_summary", input: "cohort=tenure_band", status: "Pending" },
      { time: "13m", tool: "nba_signal_analytics.get_content_engagement", input: "cohort=top_affected", status: "Pending" },
      { time: "12m", tool: "nba_policy_guardrail", input: "recommended_actions", status: "Pending" }
    ];

  return (
    <section className="panel tool-table-panel">
      <div className="section-heading">
        <span><Table2 size={18} />Tool Calls</span>
      </div>
      <div className="tool-table">
        <div className="tool-row header">
          <span>Time</span>
          <span>Tool</span>
          <span>Input</span>
          <span>Status</span>
        </div>
        {rows.map((row) => (
          <div className="tool-row" key={`${row.time}-${row.tool}`}>
            <span>{row.time}</span>
            <strong>{row.tool}</strong>
            <span>{row.input}</span>
            <StatusBadge label={row.status} tone={row.status === "Success" ? "ready" : "new"} />
          </div>
        ))}
      </div>
    </section>
  );
}

function CaseHeader({
  signal,
  busyAction,
  onInvestigate,
  onActivate
}: {
  signal: SignalIncident;
  busyAction: "investigate" | "activate" | "refresh" | null;
  onInvestigate: () => Promise<void>;
  onActivate: () => Promise<void>;
}) {
  return (
    <div className="detail-header">
      <div>
        <p className="eyebrow">Case File / {signal.segment}</p>
        <h2>{signal.title}</h2>
        <div className="case-meta">
          <StatusBadge label={signal.severity} tone={signal.severity} />
          <span>Signal ID {signal.signal_id}</span>
          <span>Detected {formatRelative(signal.detected_at)}</span>
        </div>
      </div>
      <div className="button-row">
        <button className="secondary-button" onClick={onInvestigate} disabled={busyAction === "investigate"}>
          <Search size={17} />
          {busyAction === "investigate" ? "Investigating" : "Investigate"}
        </button>
        <button className="primary-button" onClick={onActivate} disabled={busyAction === "activate"}>
          <Play size={17} />
          {busyAction === "activate" ? "Deploying..." : "Deploy Agent"}
        </button>
      </div>
    </div>
  );
}


function MetricsGrid({ signal }: { signal: SignalIncident }) {
  return (
    <div className="metrics-grid">
      <Metric label="Affected" value={formatNumber(signal.affected_customers)} icon={<Zap size={18} />} />
      <Metric label="Value at Risk" value={formatMoney(signal.estimated_value_at_risk)} icon={<CircleDollarSign size={18} />} />
      <Metric label="Churn Risk Score" value={formatScore(signal.churn_risk_score)} icon={<Gauge size={18} />} />
      <Metric label="Detected" value={formatRelative(signal.detected_at)} icon={<Clock3 size={18} />} />
    </div>
  );
}


function AgentPanel({ state, large = false }: { state: AppState; large?: boolean }) {
  const { investigation, signal } = state;
  return (
    <section className={`panel agent-panel ${large ? "large" : ""}`}>
      <div className="section-heading spread">
        <span><Bot size={18} />Agent Investigation</span>
        <StatusBadge label={investigation ? investigation.supervisor_endpoint : "idle"} tone={investigation ? "ready" : "new"} />
      </div>
      {large && signal ? (
        <AgentReasoningBoard signal={signal} investigation={investigation} />
      ) : investigation ? (
        <div className="agent-output">
          <p>{investigation.summary}</p>
          <div className="tool-trace">
            {investigation.tool_calls.map((call) => (
              <div key={`${call.name}-${call.input}`}>
                <span>{call.name}</span>
                <p>{call.output}</p>
              </div>
            ))}
          </div>
          <ul className="focus-list">
            {investigation.recommended_focus.map((item) => <li key={item}>{item}</li>)}
          </ul>
        </div>
      ) : (
        <div className="empty-state">
          <Search size={20} />
          <span>Run the supervisor to gather evidence and tool traces.</span>
        </div>
      )}
    </section>
  );
}

function AgentReasoningBoard({
  signal,
  investigation
}: {
  signal: SignalIncident;
  investigation: InvestigationResult | null;
}) {
  const reasoning = [
    {
      time: "15m",
      title: "Received signal",
      detail: `${signal.title} opened for agent review.`
    },
    {
      time: "14m",
      title: "Goal",
      detail: "Identify root causes and propose low-risk, low-cost actions."
    },
    {
      time: "13m",
      title: "Plan",
      detail: "Analyze cohorts, content engagement, pricing sensitivity, and campaign eligibility."
    },
    {
      time: "12m",
      title: "Observation",
      detail: signal.root_causes[0] ?? "Behavior changed materially against segment baseline."
    },
    {
      time: "11m",
      title: "Hypothesis",
      detail: signal.root_causes[1] ?? "Content discovery gap is driving churn risk."
    },
    {
      time: "8m",
      title: "Next step",
      detail: investigation ? investigation.summary : "Recommend guarded content and service actions for policy evaluation."
    }
  ];

  return (
    <div className="reasoning-board">
      {reasoning.map((item) => (
        <div className="reasoning-row" key={`${item.time}-${item.title}`}>
          <span>{item.time}</span>
          <strong>{item.title}</strong>
          <p>{item.detail}</p>
        </div>
      ))}
      {investigation ? (
        <div className="agent-evidence-strip">
          {investigation.recommended_focus.map((item) => <span key={item}>{item}</span>)}
        </div>
      ) : (
        <div className="agent-evidence-strip">
          {signal.evidence.slice(0, 3).map((item) => <span key={item}>{item}</span>)}
        </div>
      )}
    </div>
  );
}


function DecisionMatrix({ decisions, compact = false }: { decisions: PolicyDecision[]; compact?: boolean }) {
  return (
    <section className={`panel actions-panel ${compact ? "compact" : ""}`}>
      <div className="section-heading spread">
        <span><CheckCircle2 size={18} />Agent Decisions</span>
        <span className="table-note">Ranked by policy threshold</span>
      </div>
      {compact ? <CompactActionTable decisions={decisions} /> : <FullActionTable decisions={decisions} />}
    </section>
  );
}

function CompactActionTable({ decisions }: { decisions: PolicyDecision[] }) {
  return (
    <div className="action-table compact-table">
      {decisions.slice(0, 3).map((decision) => (
        <div className="action-row compact-row" key={decision.action.action_id}>
          <div className="action-rank">{decision.action.rank}</div>
          <div>
            <strong>{decision.action.action_name}</strong>
            <p>{decision.action.rationale}</p>
            <small>{decision.reasons.join(" / ")} / {decision.action.risk_level} risk</small>
            <div className="compact-action-meta">
              <span>{decision.action.channel}</span>
              <span>{formatMoney(actionValueAtRisk(decision.action))} value at risk</span>
              <span>{formatScore(actionChurnRiskScore(decision.action))} churn risk</span>
              <span>{formatPercent(decision.action.expected_lift)}</span>
              <StatusBadge label={decisionLabel(decision.decision)} tone={decision.decision} />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function FullActionTable({ decisions }: { decisions: PolicyDecision[] }) {
  return (
    <div className="action-table full-table-simple">
      <div className="action-header full-header-simple">
        <span>Rank</span>
        <span>Action</span>
        <span>Value at Risk</span>
        <span>Risk Level</span>
        <span>Expected Lift</span>
        <span>Agent Decision</span>
      </div>
      {decisions.map((decision) => (
        <div className="action-row full-row-simple" key={decision.action.action_id}>
          <div className="action-rank">{decision.action.rank}</div>
          <div>
            <strong>{decision.action.action_name}</strong>
            <p>{decision.action.rationale}</p>
          </div>
          <span>{formatMoney(actionValueAtRisk(decision.action))}</span>
          <StatusBadge label={decision.action.risk_level} tone={decision.action.risk_level} />
          <span>{formatPercent(decision.action.expected_lift)}</span>
          <StatusBadge label={decisionLabel(decision.decision)} tone={decision.decision} />
        </div>
      ))}
    </div>
  );
}


function PolicyControlStrip({
  policy,
  patchPolicy
}: {
  policy: PolicyConfig | null;
  patchPolicy: (patch: Partial<PolicyConfig>) => Promise<void>;
}) {
  if (!policy) {
    return null;
  }
  return (
    <div className="policy-strip">
      <div className="policy-control">
        <span>VaR threshold</span>
        <strong>{formatMoney(policy.var_threshold)}</strong>
      </div>
      <div className="policy-control">
        <span>Allowed risk levels</span>
        <strong>{policy.auto_risk_levels.join(", ")}</strong>
      </div>
      <div className="policy-control">
        <span>Exclude offers requiring humans</span>
        <label className="mini-toggle">
          <input
            type="checkbox"
            checked={policy.require_human_for_offers}
            onChange={(event) => patchPolicy({ require_human_for_offers: event.target.checked })}
          />
          <span />
        </label>
      </div>
      <div className="policy-control">
        <span>Auto action limit</span>
        <strong>{policy.max_auto_actions}</strong>
      </div>
      <button className="primary-button" onClick={() => patchPolicy({ var_threshold: policy.var_threshold })}>
        Re-evaluate Actions
      </button>
    </div>
  );
}

function DecisionSummary({ decisions }: { decisions: PolicyDecision[] }) {
  const auto = decisions.filter((decision) => decision.decision === "auto_simulate");
  return (
    <div className="decision-summary">
      <Metric label="Agent-approved" value={`${auto.length}`} />
      <Metric label="Value agent protects" value={formatMoney(sumValueAtRisk(auto))} />
      <Metric label="Est. churn reduction" value={formatPercent(sumLift(decisions))} />
      <Metric label="Needs your review" value={formatMoney(sumValueAtRisk(decisions.filter((decision) => decision.decision === "review_required")))} />
      <button className="primary-button">Deploy Agent on Selected</button>
    </div>
  );
}



function RecentAutoActions({
  decisions,
  activation,
  signal
}: {
  decisions: PolicyDecision[];
  activation: ActivationResult | null;
  signal: SignalIncident | null;
}) {
  const rows = activation?.records.length
    ? activation.records.map((record, index) => {
      const matchingDecision = decisions.find((decision) => decision.action.action_id === record.action_id);
      return {
        time: `${10 + index}:45 AM`,
        action: record.action_name,
        signal: signal?.title ?? "Selected signal",
        audience: formatNumber(record.target_count),
        cost: formatMoney(record.estimated_cost),
        value: formatMoney(matchingDecision ? actionValueAtRisk(matchingDecision.action) : record.estimated_cost * 250),
        status: "Agent Executed"
      };
    })
    : decisions.map((decision, index) => ({
      time: `${10 + index}:45 AM`,
      action: decision.action.action_name,
      signal: signal?.title ?? "Selected signal",
      audience: audienceLabel(decision.action),
      cost: formatMoney(decision.action.cost_per_delivery * decision.action.target_count),
      value: formatMoney(actionValueAtRisk(decision.action)),
      status: "Ready"
    }));

  if (!rows.length) {
    return <EmptyState label="No agent actions yet" icon={<ShieldCheck size={18} />} compact />;
  }

  return (
    <div className="recent-actions-table">
      <div className="recent-row header">
        <span>Time</span>
        <span>Action</span>
        <span>Signal</span>
        <span>Audience</span>
        <span>Value at Risk</span>
        <span>Status</span>
      </div>
      {rows.map((row) => (
        <div className="recent-row" key={`${row.time}-${row.action}`}>
          <span>{row.time}</span>
          <strong>{row.action}</strong>
          <span>{row.signal}</span>
          <span>{row.audience}</span>
          <span>{row.value}</span>
          <StatusBadge label={row.status} tone="ready" />
        </div>
      ))}
    </div>
  );
}





function EmptyState({ label, icon, compact = false }: { label: string; icon?: React.ReactNode; compact?: boolean }) {
  return (
    <div className={`empty-state ${compact ? "compact" : ""}`}>
      {icon}
      <span>{label}</span>
    </div>
  );
}


function LoadingState() {
  return (
    <div className="loading-state">
      <RefreshCcw size={20} />
      <span>Loading</span>
    </div>
  );
}

function StatusBadge({ label, tone, icon }: { label: string; tone: string; icon?: React.ReactNode }) {
  return <span className={`status-badge ${tone}`}>{icon}{label}</span>;
}

function Metric({ label, value, icon }: { label: string; value: string; icon?: React.ReactNode }) {
  return (
    <div className="metric">
      {icon ? <span className="metric-icon">{icon}</span> : null}
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function PolicyEditor({ policy, onChange }: { policy: PolicyConfig; onChange: (patch: Partial<PolicyConfig>) => Promise<void> }) {
  const [draftThreshold, setDraftThreshold] = useState(policy.var_threshold);

  useEffect(() => {
    setDraftThreshold(policy.var_threshold);
  }, [policy.var_threshold]);

  function toggleRisk(risk: ActionRisk) {
    const isActive = policy.auto_risk_levels.includes(risk);
    if (isActive && policy.auto_risk_levels.length === 1) {
      return;
    }
    const next = isActive
      ? policy.auto_risk_levels.filter((item) => item !== risk)
      : [...policy.auto_risk_levels, risk];
    void onChange({ auto_risk_levels: next });
  }

  function applyPreset(name: "strict" | "standard" | "expanded") {
    const presets: Record<"strict" | "standard" | "expanded", Partial<PolicyConfig>> = {
      strict: {
        var_threshold: 5000,
        auto_risk_levels: ["low"],
        max_auto_actions: 10,
        require_human_for_offers: true
      },
      standard: {
        var_threshold: 8000,
        auto_risk_levels: ["low"],
        max_auto_actions: 25,
        require_human_for_offers: false
      },
      expanded: {
        var_threshold: 12000,
        auto_risk_levels: ["low", "medium"],
        max_auto_actions: 75,
        require_human_for_offers: false
      }
    };
    void onChange(presets[name]);
  }

  return (
    <div className="policy-editor">
      <div className="preset-row" aria-label="Policy presets">
        <button onClick={() => applyPreset("strict")}>Strict</button>
        <button onClick={() => applyPreset("standard")}>Standard</button>
        <button onClick={() => applyPreset("expanded")}>Expanded</button>
      </div>

      <label>
        <span>Total value at risk threshold</span>
        <strong>{formatMoney(draftThreshold)}</strong>
        <input
          type="range"
          min="0"
          max="15000"
          step="500"
          value={draftThreshold}
          onChange={(event) => setDraftThreshold(Number(event.target.value))}
          onMouseUp={() => void onChange({ var_threshold: draftThreshold })}
          onTouchEnd={() => void onChange({ var_threshold: draftThreshold })}
        />
      </label>

      <label>
        <span>Auto action limit</span>
        <input
          className="number-input"
          type="number"
          min="1"
          max="500"
          value={policy.max_auto_actions}
          onChange={(event) => void onChange({ max_auto_actions: Number(event.target.value) })}
        />
      </label>

      <div className="risk-selector">
        <span>Auto risk levels</span>
        {(["low", "medium", "high"] as ActionRisk[]).map((risk) => (
          <button
            key={risk}
            className={policy.auto_risk_levels.includes(risk) ? "risk active" : "risk"}
            onClick={() => toggleRisk(risk)}
          >
            {risk}
          </button>
        ))}
      </div>

      <label className="toggle-row">
        <input
          type="checkbox"
          checked={policy.require_human_for_offers}
          onChange={(event) => void onChange({ require_human_for_offers: event.target.checked })}
        />
        <span>Review all offers</span>
      </label>
    </div>
  );
}


function previewDecision(action: NbaActionCandidate, policy: PolicyConfig | null): ActionDecision {
  if (!policy) return "review_required";
  if (action.holdout_blocked) return "blocked";
  if (actionValueAtRisk(action) > policy.var_threshold) return "review_required";
  if (!policy.auto_risk_levels.includes(action.risk_level)) return "review_required";
  if (policy.require_human_for_offers && action.is_offer) return "review_required";
  return "auto_simulate";
}

function previewReasons(action: NbaActionCandidate, policy: PolicyConfig | null) {
  if (!policy) return ["policy loading"];
  if (action.holdout_blocked) return ["orchestration blocked"];
  if (actionValueAtRisk(action) > policy.var_threshold) return ["VaR exceeds threshold — needs human"];
  if (!policy.auto_risk_levels.includes(action.risk_level)) return ["risk level requires human review"];
  return ["within agent authority"];
}

function audienceLabel(action: NbaActionCandidate) {
  if (action.action_name.toLowerCase().includes("service")) return "Premium / service";
  if (action.action_name.toLowerCase().includes("win-back")) return "Lapsed 30-60 days";
  if (action.action_name.toLowerCase().includes("loyalty")) return "Premium 6+ mos";
  return action.target_count >= 800 ? "Premium 3-6 mos" : "Premium";
}

function decisionLabel(decision: ActionDecision): string {
  if (decision === "auto_simulate") return "Agent Approved";
  if (decision === "review_required") return "Needs Review";
  return "Blocked";
}


function actionValueAtRisk(action: NbaActionCandidate) {
  return action.target_count * (action.risk_level === "high" ? 53 : action.risk_level === "medium" ? 31 : 12.8);
}

function actionChurnRiskScore(action: NbaActionCandidate) {
  const base = action.risk_level === "high" ? 0.88 : action.risk_level === "medium" ? 0.74 : 0.61;
  return Math.min(0.96, base + action.expected_lift);
}

function parseViewFromHash(): ViewId {
  const view = window.location.hash.replace("#", "");
  return navItems.some((item) => item.id === view) ? (view as ViewId) : "command";
}

function sumLift(decisions: PolicyDecision[]) {
  return decisions
    .filter((decision) => decision.decision === "auto_simulate")
    .reduce((total, decision) => total + decision.action.expected_lift, 0);
}


function sumValueAtRisk(decisions: PolicyDecision[]) {
  return decisions.reduce((total, decision) => total + actionValueAtRisk(decision.action), 0);
}

function formatMoney(value: number) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 }).format(value);
}

function formatNumber(value: number) {
  return new Intl.NumberFormat("en-US").format(value);
}

function formatPercent(value: number) {
  return new Intl.NumberFormat("en-US", { style: "percent", maximumFractionDigits: 0 }).format(value);
}

function formatScore(value: number) {
  return value.toFixed(2);
}

function formatRelative(value: string) {
  const minutes = Math.max(1, Math.round((Date.now() - new Date(value).getTime()) / 60000));
  return `${minutes}m ago`;
}
