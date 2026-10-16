import { useCallback, useEffect, useState, type FormEvent } from "react";

import {
    CartesianGrid,
    Line,
    LineChart,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from "recharts";

type MetricValues = {
    cpu?: {
        percent?: number;
        logical_count?: number;
        load_average?: number[];
    };
    memory?: {
        total_bytes?: number;
        available_bytes?: number;
        used_percent?: number;
    };
    disk?: {
        path?: string;
        total_bytes?: number;
        used_percent?: number;
        free_bytes?: number;
    };
    processes?: {
        total?: number;
        running?: number;
    };
};

type Snapshot = {
    id: number;
    agent_id: string;
    hostname: string;
    platform: string;
    observed_at: string;
    received_at: string;
    uptime_seconds: number;
    metrics: MetricValues;
};

type HostStatus = {
    agent_id: string;
    hostname: string;
    status: string;
    last_seen_at?: string | null;
    age_seconds?: number | null;
    platform?: string | null;
};

type Incident = {
    id: number;
    agent_id: string;
    hostname: string;
    rule_key: string;
    title: string;
    severity: string;
    status: string;
    started_at: string;
    last_seen_at: string;
    resolved_at?: string | null;
    evidence?: Record<string, unknown> | null;
};

type IncidentSummary = {
    active: number;
    critical: number;
    warning: number;
};

type ChartPoint = {
    observed_at: string;
    value: number;
};

const RANGES = [
    {label: "1 hour", hours: 1},
    {label: "6 hours", hours: 6},
    {label: "24 hours", hours: 24},
    {label: "7 days", hours: 168},
];

function formatPercent(value?: number) {
    return typeof value === "number" ? `${value.toFixed(1)}%` : "—";
}

function formatBytes(value?: number) {
    if (typeof value !== "number") return "—";
    return `${(value / 1024 ** 3).toFixed(1)} GiB`;
}

function formatTime(value?: string | null) {
    if (!value) return "Unknown";

    const date = new Date(value);

    return Number.isNaN(date.getTime())
        ? "Unknown"
        : date.toLocaleString();
}

function formatAxisTime(value: string) {
    const date = new Date(value);

    if (Number.isNaN(date.getTime())) return "";

    return date.toLocaleString([], {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
    });
}

function formatUptime(seconds?: number) {
    if (typeof seconds !== "number" || !Number.isFinite(seconds)) {
        return "Unknown";
    }

    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);

    if (days > 0) return `${days}d ${hours}h`;
    if (hours > 0) return `${hours}h ${minutes}m`;

    return `${minutes}m`;
}

function formatAge(seconds?: number | null) {
    if (typeof seconds !== "number" || !Number.isFinite(seconds)) {
        return "Unknown";
    }

    if (seconds < 60) return `${Math.max(0, Math.floor(seconds))}s ago`;

    if (seconds < 3600) {
        return `${Math.floor(seconds / 60)}m ago`;
    }

    if (seconds < 86400) {
        return `${Math.floor(seconds / 3600)}h ago`;
    }

    return `${Math.floor(seconds / 86400)}d ago`;
}

function MetricCard({
                        label,
                        value,
                        detail,
                    }: {
    label: string;
    value: string;
    detail: string;
}) {
    return (
        <article className="metric-card">
            <p className="metric-label">{label}</p>
            <strong className="metric-value">{value}</strong>
            <small>{detail}</small>
        </article>
    );
}

function SummaryCard({
                         label,
                         value,
                         tone,
                     }: {
    label: string;
    value: number;
    tone?: string;
}) {
    return (
        <article className={`summary-card ${tone ?? ""}`}>
            <span>{label}</span>
            <strong>{value}</strong>
        </article>
    );
}

function makeChartPoints(
    snapshots: Snapshot[],
    getValue: (snapshot: Snapshot) => number | undefined,
): ChartPoint[] {
    return snapshots
        .map((snapshot) => ({
            observed_at: snapshot.observed_at,
            value: getValue(snapshot),
        }))
        .filter(
            (point): point is ChartPoint =>
                typeof point.value === "number" &&
                Number.isFinite(point.value),
        )
        .sort(
            (a, b) =>
                new Date(a.observed_at).getTime() -
                new Date(b.observed_at).getTime(),
        );
}

function HistoryChart({
                          title,
                          color,
                          points,
                      }: {
    title: string;
    color: string;
    points: ChartPoint[];
}) {
    return (
        <article className="chart-card">
            <div className="chart-heading">
                <h4>{title}</h4>
                <span>{points.length} samples</span>
            </div>

            {points.length < 2 ? (
                <div className="chart-empty">
                    Collecting history. At least two snapshots are needed to draw a
                    trend.
                </div>
            ) : (
                <ResponsiveContainer width="100%" height={250}>
                    <LineChart
                        data={points}
                        margin={{top: 12, right: 16, left: 0, bottom: 8}}
                    >
                        <CartesianGrid
                            stroke="#26313f"
                            strokeDasharray="4 4"
                            vertical={false}
                        />

                        <XAxis
                            dataKey="observed_at"
                            tickFormatter={(value) => formatAxisTime(String(value))}
                            tick={{fill: "#9aa9ba", fontSize: 11}}
                            minTickGap={35}
                            axisLine={{stroke: "#344253"}}
                            tickLine={false}
                        />

                        <YAxis
                            domain={[0, 100]}
                            ticks={[0, 25, 50, 75, 100]}
                            tickFormatter={(value) => `${value}%`}
                            tick={{fill: "#9aa9ba", fontSize: 11}}
                            axisLine={false}
                            tickLine={false}
                            width={42}
                        />

                        <Tooltip
                            labelFormatter={(value) => formatTime(String(value))}
                            formatter={(value) => [
                                `${Number(value).toFixed(1)}%`,
                                title,
                            ]}
                            contentStyle={{
                                background: "#111923",
                                border: "1px solid #344253",
                                borderRadius: 10,
                                color: "#e8edf4",
                            }}
                            labelStyle={{color: "#9aa9ba", marginBottom: 5}}
                        />

                        <Line
                            type="monotone"
                            dataKey="value"
                            name={title}
                            stroke={color}
                            strokeWidth={2}
                            dot={false}
                            activeDot={{r: 4}}
                            isAnimationActive={false}
                        />
                    </LineChart>
                </ResponsiveContainer>
            )}
        </article>
    );
}

function getArray<T>(data: unknown): T[] {
    if (Array.isArray(data)) return data as T[];

    if (data && typeof data === "object") {
        const object = data as Record<string, unknown>;

        for (const key of ["items", "results", "hosts", "incidents"]) {
            if (Array.isArray(object[key])) {
                return object[key] as T[];
            }
        }
    }

    return [];
}

function normalizeSummary(data: unknown): IncidentSummary {
    const value = data as Partial<IncidentSummary> | null;

    return {
        active: Number(value?.active ?? 0),
        critical: Number(value?.critical ?? 0),
        warning: Number(value?.warning ?? 0),
    };
}

function getEvidenceText(evidence?: Record<string, unknown> | null) {
    if (!evidence) return "";

    return Object.entries(evidence)
        .filter(([, value]) => value !== null && value !== undefined)
        .slice(0, 4)
        .map(([key, value]) => {
            const displayValue =
                typeof value === "object"
                    ? JSON.stringify(value)
                    : String(value);

            return `${key.replaceAll("_", " ")}: ${displayValue}`;
        })
        .join(" · ");
}

function getStatusClass(status?: string) {
    const normalized = (status ?? "").toLowerCase();

    if (normalized === "reporting") return "health-reporting";
    if (normalized === "stale") return "health-stale";
    if (normalized === "critical") return "severity-critical";
    if (normalized === "warning") return "severity-warning";
    if (normalized === "resolved") return "severity-resolved";
    if (normalized === "active") return "severity-active";

    return "";
}

export default function App() {
    const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
    const [history, setHistory] = useState<Snapshot[]>([]);
    const [hostStatuses, setHostStatuses] = useState<HostStatus[]>([]);
    const [incidents, setIncidents] = useState<Incident[]>([]);

    const [incidentSummary, setIncidentSummary] = useState<IncidentSummary>({
        active: 0,
        critical: 0,
        warning: 0,
    });

    const [rangeHours, setRangeHours] = useState(24);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [lastChecked, setLastChecked] = useState<Date | null>(null);
    const [authenticated, setAuthenticated] = useState(false);
    const [authChecked, setAuthChecked] = useState(false);
    const [loginUsername, setLoginUsername] = useState("admin");
    const [loginPassword, setLoginPassword] = useState("");
    const [loginError, setLoginError] = useState("");
    const [loginLoading, setLoginLoading] = useState(false);
    const loadSnapshots = useCallback(
        async (signal?: AbortSignal) => {
            try {
                const endpoints = [
                    "/api/v1/metrics/latest",
                    `/api/v1/metrics/history?hours=${rangeHours}&limit=1000`,
                    "/api/v1/hosts/status",
                    "/api/v1/incidents?limit=100",
                    "/api/v1/incidents/summary",
                ];

                const responses = await Promise.all(
                    endpoints.map((url) => fetch(url, {signal})),
                );

                const failedResponse = responses.find((response) => !response.ok);

                if (failedResponse) {
                    if (failedResponse.status === 401) {
                        setAuthenticated(false);
                        setSnapshots([]);
                        setHistory([]);
                        setHostStatuses([]);
                        setIncidents([]);
                        setIncidentSummary({active: 0, critical: 0, warning: 0});
                        setError("");
                        return;
                    }

                    throw new Error(
                        `API request failed: HTTP ${failedResponse.status}`,
                    );
                }

                const [
                    latestData,
                    historyData,
                    hostsData,
                    incidentsData,
                    summaryData,
                ] = await Promise.all(responses.map((response) => response.json()));

                if (!Array.isArray(latestData) || !Array.isArray(historyData)) {
                    throw new Error("Unexpected response from the metrics API");
                }

                setSnapshots(latestData as Snapshot[]);
                setHistory(historyData as Snapshot[]);
                setHostStatuses(getArray<HostStatus>(hostsData));
                setIncidents(getArray<Incident>(incidentsData));
                setIncidentSummary(normalizeSummary(summaryData));

                setError("");
                setLastChecked(new Date());
            } catch (err) {
                if (err instanceof Error && err.name === "AbortError") return;

                setError(
                    err instanceof Error
                        ? err.message
                        : "Unable to load server diagnostics",
                );
            } finally {
                if (!signal?.aborted) setLoading(false);
            }
        },
        [rangeHours],
    );

    useEffect(() => {
        let active = true;

        async function checkSession() {
            try {
                const response = await fetch("/api/v1/auth/me", {
                    credentials: "same-origin",
                });

                if (!active) return;

                if (response.status === 401) {
                    setAuthenticated(false);
                    return;
                }

                if (!response.ok) {
                    throw new Error("Unable to check login status");
                }

                setAuthenticated(true);
            } catch {
                if (active) {
                    setAuthenticated(false);
                    setLoginError("Unable to connect to the API. Please retry.");
                }
            } finally {
                if (active) setAuthChecked(true);
            }
        }

        void checkSession();

        return () => {
            active = false;
        };
    }, []);
    useEffect(() => {
        if (!authChecked || !authenticated) return;

        const controller = new AbortController();

        void loadSnapshots(controller.signal);

        const interval = window.setInterval(() => {
            void loadSnapshots(controller.signal);
        }, 30_000);

        return () => {
            controller.abort();
            window.clearInterval(interval);
        };
    }, [loadSnapshots, authenticated, authChecked]);

    const latest = snapshots.reduce<Snapshot | undefined>(
        (newest, snapshot) =>
            !newest ||
            new Date(snapshot.observed_at).getTime() >
            new Date(newest.observed_at).getTime()
                ? snapshot
                : newest,
        undefined,
    );

    const metrics = latest?.metrics;

    const cpuPoints = makeChartPoints(
        history,
        (snapshot) => snapshot.metrics.cpu?.percent,
    );

    const memoryPoints = makeChartPoints(
        history,
        (snapshot) => snapshot.metrics.memory?.used_percent,
    );

    const diskPoints = makeChartPoints(
        history,
        (snapshot) => snapshot.metrics.disk?.used_percent,
    );

    const staleHosts = hostStatuses.filter(
        (host) => host.status.toLowerCase() === "stale",
    ).length;

    async function handleLogin(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        setLoginError("");
        setLoginLoading(true);

        try {
            const response = await fetch("/api/v1/auth/login", {
                method: "POST",
                credentials: "same-origin",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({
                    username: loginUsername,
                    password: loginPassword,
                }),
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.detail || "Login failed");
            }

            setLoginPassword("");
            setAuthenticated(true);
            setLoading(true);
        } catch (error) {
            setLoginError(
                error instanceof Error ? error.message : "Login failed",
            );
        } finally {
            setLoginLoading(false);
        }
    }

    async function handleLogout() {
        try {
            const response = await fetch("/api/v1/auth/logout", {
                method: "POST",
                credentials: "same-origin",
            });

            if (!response.ok) {
                throw new Error("Logout failed");
            }

            setAuthenticated(false);
            setSnapshots([]);
            setHistory([]);
            setHostStatuses([]);
            setIncidents([]);
            setIncidentSummary({active: 0, critical: 0, warning: 0});
            setError("");
            setLoginError("");
        } catch {
            setError("Unable to log out. Please try again.");
        }
    }

    if (!authChecked) {
        return (
            <main className="shell login-shell">
                <p className="eyebrow">ANAS LABS</p>
                <h1>Production Diagnostics</h1>
                <p className="muted">Checking administrator session…</p>
            </main>
        );
    }

    if (!authenticated) {
        return (
            <main className="shell login-shell">
                <section className="login-card">
                    <div className="mark">A</div>
                    <p className="eyebrow">ANAS LABS</p>
                    <h1>Production Diagnostics</h1>
                    <p className="muted">
                        Sign in to view your server metrics and incidents.
                    </p>

                    <form className="login-form" onSubmit={handleLogin}>
                        <label htmlFor="login-username">Username</label>
                        <input
                            id="login-username"
                            autoComplete="username"
                            value={loginUsername}
                            onChange={(event) => setLoginUsername(event.target.value)}
                            required
                        />

                        <label htmlFor="login-password">Password</label>
                        <input
                            id="login-password"
                            type="password"
                            autoComplete="current-password"
                            value={loginPassword}
                            onChange={(event) => setLoginPassword(event.target.value)}
                            required
                        />

                        {loginError && (
                            <p className="login-error" role="alert">
                                {loginError}
                            </p>
                        )}

                        <button type="submit" disabled={loginLoading}>
                            {loginLoading ? "Signing in…" : "Sign in"}
                        </button>
                    </form>
                </section>
            </main>
        );
    }

    return (
        <main className="shell">
        <style>{`
        .diagnostics-section { margin-top: 34px; }
        .diagnostics-grid {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 16px;
        }
        .summary-card {
          display: flex;
          flex-direction: column;
          gap: 12px;
          padding: 20px;
          border: 1px solid #263444;
          border-radius: 14px;
          background: #111923;
        }
        .summary-card span { color: #9aa9ba; font-size: 13px; }
        .summary-card strong { font-size: 30px; line-height: 1.2; }
        .summary-card.danger strong { color: #ff8585; }
        .summary-card.warning strong { color: #f2bb77; }
        .summary-card.success strong { color: #7bd8a5; }
        .diagnostics-panel {
          border: 1px solid #263444;
          border-radius: 14px;
          overflow: hidden;
          background: #111923;
        }
        .diagnostics-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 18px;
          padding: 16px 18px;
          border-bottom: 1px solid #26313f;
        }
        .diagnostics-row:last-child { border-bottom: 0; }
        .diagnostics-main {
          display: flex;
          flex-direction: column;
          gap: 5px;
          min-width: 0;
        }
        .diagnostics-main strong {
          overflow-wrap: anywhere;
          color: #e8edf4;
        }
        .diagnostics-main small,
        .diagnostics-muted {
          color: #9aa9ba;
          font-size: 12px;
          overflow-wrap: anywhere;
        }
        .diagnostics-meta {
          display: flex;
          flex-direction: column;
          align-items: flex-end;
          gap: 6px;
          text-align: right;
          flex-shrink: 0;
        }
        .diagnostics-badge {
          display: inline-flex;
          align-items: center;
          width: fit-content;
          border: 1px solid #344253;
          border-radius: 999px;
          padding: 4px 9px;
          font-size: 11px;
          font-weight: 600;
          text-transform: capitalize;
          white-space: nowrap;
        }
        .health-reporting, .severity-resolved {
          color: #7bd8a5;
          background: #173326;
          border-color: #28563f;
        }
        .health-stale, .severity-critical {
          color: #ff9999;
          background: #3a2025;
          border-color: #63323b;
        }
        .severity-warning {
          color: #f2bb77;
          background: #392d1e;
          border-color: #5b462a;
        }
        .severity-active {
          color: #b7c9ff;
          background: #202d45;
          border-color: #35496e;
        }
        .incident-evidence {
          color: #9aa9ba;
          font-size: 12px;
          line-height: 1.5;
          overflow-wrap: anywhere;
          margin-top: 3px;
        }
        .panel-empty {
          padding: 24px 18px;
          color: #9aa9ba;
          font-size: 13px;
        }
        .panel-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          padding: 16px 18px;
          border-bottom: 1px solid #26313f;
        }
        .panel-header h4 { margin: 0; }
        .panel-header span { color: #9aa9ba; font-size: 12px; }
        @media (max-width: 760px) {
          .diagnostics-grid { grid-template-columns: 1fr; }
          .diagnostics-row { align-items: flex-start; }
          .diagnostics-meta { max-width: 45%; }
        }
        @media (max-width: 480px) {
          .diagnostics-row { flex-direction: column; }
          .diagnostics-meta {
            align-items: flex-start;
            max-width: 100%;
            text-align: left;
          }
        }
      `}</style>

        <header className="topbar">
            {authenticated && (
                <button
                    className="logout-button"
                    type="button"
                    onClick={() => void handleLogout()}
                >
                    Log out
                </button>
            )}
            <div className="brand">
                <div className="mark">A</div>
                <div>
                    <p className="eyebrow">ANAS LABS</p>
                    <h1>Production Diagnostics</h1>
                </div>
            </div>

            <div className={`status ${error ? "status-error" : ""}`}>
                <span className="status-dot"/>
                {error
                    ? "Connection issue"
                    : loading
                        ? "Connecting…"
                        : "API connected"}
            </div>
        </header>

        <section className="intro">
            <p className="eyebrow">HOST MONITORING · DEVELOPMENT BUILD</p>
            <h2>Understand what changed when production breaks.</h2>
            <p className="muted">
                A practical view of server health, resource usage, and the latest
                collected evidence.
            </p>
        </section>

        {error && (
            <section className="notice notice-error" role="alert">
                <div>
                    <strong>Couldn't refresh server diagnostics</strong>
                    <p>{error}</p>
                </div>
                <button
                    onClick={() => void loadSnapshots()}
                    type="button"
                >
                    Retry
                </button>
            </section>
        )}

        {!loading && !error && snapshots.length === 0 && (
            <section className="empty-state">
                <h3>No server snapshots yet</h3>
                <p>Start the diagnostics agent and submit a snapshot.</p>
            </section>
        )}

        <section className="section-heading diagnostics-section">
            <div>
                <p className="eyebrow">INCIDENTS</p>
                <h3>Incident summary</h3>
            </div>
            <span className="muted small">
          {incidentSummary.active} active
        </span>
        </section>

        <section className="diagnostics-grid">
            <SummaryCard
                label="Active incidents"
                value={incidentSummary.active}
                tone={incidentSummary.active > 0 ? "danger" : "success"}
            />
            <SummaryCard
                label="Critical incidents"
                value={incidentSummary.critical}
                tone={incidentSummary.critical > 0 ? "danger" : "success"}
            />
            <SummaryCard
                label="Warning incidents"
                value={incidentSummary.warning}
                tone={incidentSummary.warning > 0 ? "warning" : "success"}
            />
        </section>

        <section className="section-heading diagnostics-section">
            <div>
                <p className="eyebrow">HOST STATUS</p>
                <h3>Agent reporting status</h3>
            </div>
            <span className="muted small">
          {hostStatuses.length} agents · {staleHosts} stale
        </span>
        </section>

        <section className="diagnostics-panel">
            {hostStatuses.length === 0 ? (
                <div className="panel-empty">
                    {loading
                        ? "Loading host status…"
                        : "No host status data available yet."}
                </div>
            ) : (
                hostStatuses.map((host) => (
                    <article className="diagnostics-row" key={host.agent_id}>
                        <div className="diagnostics-main">
                            <strong>{host.hostname}</strong>
                            <small>{host.agent_id}</small>
                            {host.platform && (
                                <small>{host.platform}</small>
                            )}
                        </div>

                        <div className="diagnostics-meta">
                <span
                    className={`diagnostics-badge ${getStatusClass(host.status)}`}
                >
                  {host.status}
                </span>
                            <span className="diagnostics-muted">
                  Last seen {formatAge(host.age_seconds)}
                </span>
                            <span className="diagnostics-muted">
                  {formatTime(host.last_seen_at)}
                </span>
                        </div>
                    </article>
                ))
            )}
        </section>

        <section className="section-heading diagnostics-section">
            <div>
                <p className="eyebrow">DETECTION</p>
                <h3>Recent incidents</h3>
            </div>
            <span className="muted small">
          Showing up to 100 incidents
        </span>
        </section>

        <section className="diagnostics-panel">
            {incidents.length === 0 ? (
                <div className="panel-empty">
                    {loading
                        ? "Loading incidents…"
                        : "No incidents found. No active incidents is a good sign, provided metrics are being collected."}
                </div>
            ) : (
                incidents.map((incident) => (
                    <article className="diagnostics-row" key={incident.id}>
                        <div className="diagnostics-main">
                            <strong>{incident.title || incident.rule_key}</strong>
                            <small>
                                {incident.hostname} · {incident.agent_id}
                            </small>
                            <small>
                                Started {formatTime(incident.started_at)}
                            </small>
                            {incident.last_seen_at && (
                                <small>
                                    Last
                                    observed {formatTime(incident.last_seen_at)}
                                </small>
                            )}
                            {getEvidenceText(incident.evidence) && (
                                <div className="incident-evidence">
                                    Evidence: {getEvidenceText(incident.evidence)}
                                </div>
                            )}
                        </div>

                        <div className="diagnostics-meta">
                <span
                    className={`diagnostics-badge ${getStatusClass(incident.severity)}`}
                >
                  {incident.severity}
                </span>
                            <span
                                className={`diagnostics-badge ${getStatusClass(incident.status)}`}
                            >
                  {incident.status}
                </span>
                            {incident.resolved_at && (
                                <span className="diagnostics-muted">
                    Resolved {formatTime(incident.resolved_at)}
                  </span>
                            )}
                        </div>
                    </article>
                ))
            )}
        </section>

        {latest && metrics && (
            <>
                <section className="section-heading diagnostics-section">
                    <div>
                        <p className="eyebrow">OVERVIEW</p>
                        <h3>Server resources</h3>
                    </div>
                    <span className="muted small">
              Updated {formatTime(latest.observed_at)}
            </span>
                </section>

                <section className="cards">
                    <MetricCard
                        label="CPU usage"
                        value={formatPercent(metrics.cpu?.percent)}
                        detail={`${metrics.cpu?.logical_count ?? "—"} logical CPUs`}
                    />

                    <MetricCard
                        label="Memory used"
                        value={formatPercent(metrics.memory?.used_percent)}
                        detail={`${formatBytes(metrics.memory?.available_bytes)} available`}
                    />

                    <MetricCard
                        label="Disk used"
                        value={formatPercent(metrics.disk?.used_percent)}
                        detail={`${formatBytes(metrics.disk?.free_bytes)} free · ${metrics.disk?.path ?? "/"}`}
                    />

                    <MetricCard
                        label="Processes"
                        value={String(metrics.processes?.total ?? "—")}
                        detail={`${metrics.processes?.running ?? "—"} running`}
                    />
                </section>

                <section className="section-heading history-heading">
                    <div>
                        <p className="eyebrow">TRENDS</p>
                        <h3>Resource usage over time</h3>
                    </div>

                    <div className="range-picker" aria-label="History time range">
                        {RANGES.map((range) => (
                            <button
                                key={range.hours}
                                type="button"
                                className={
                                    rangeHours === range.hours ? "range-active" : ""
                                }
                                aria-pressed={rangeHours === range.hours}
                                onClick={() => setRangeHours(range.hours)}
                            >
                                {range.label}
                            </button>
                        ))}
                    </div>
                </section>

                <section className="charts-grid">
                    <HistoryChart
                        title="CPU usage"
                        color="#7db5ff"
                        points={cpuPoints}
                    />

                    <HistoryChart
                        title="Memory usage"
                        color="#7bd8a5"
                        points={memoryPoints}
                    />

                    <HistoryChart
                        title="Disk usage"
                        color="#f2bb77"
                        points={diskPoints}
                    />
                </section>

                <section className="section-heading diagnostics-section">
                    <div>
                        <p className="eyebrow">INVENTORY</p>
                        <h3>Connected servers ({snapshots.length})</h3>
                    </div>
                    <span className="muted small">
              Latest snapshot per agent
            </span>
                </section>

                <section className="host-list">
                    {snapshots.map((snapshot) => {
                        const hostStatus = hostStatuses.find(
                            (host) => host.agent_id === snapshot.agent_id,
                        );

                        const status = hostStatus?.status ?? "unknown";

                        return (
                            <article
                                className="host-row"
                                key={snapshot.agent_id}
                            >
                                <div className="host-icon">⌘</div>

                                <div className="host-info">
                                    <strong>{snapshot.hostname}</strong>
                                    <span>{snapshot.agent_id}</span>
                                    <small>{snapshot.platform}</small>
                                </div>

                                <div className="host-meta">
                    <span className="host-health">
                      <span className="status-dot"/>
                        {status}
                    </span>
                                    <span className="muted small">
                      Uptime {formatUptime(snapshot.uptime_seconds)}
                    </span>
                                    <span className="muted small">
                      Seen {formatTime(snapshot.observed_at)}
                    </span>
                                </div>
                            </article>
                        );
                    })}
                </section>
            </>
        )}

        <footer>
            <span>Open source · Apache-2.0 · Self-hosted first</span>
            <span>
          {lastChecked
              ? `Last checked ${lastChecked.toLocaleTimeString()}`
              : "Waiting for first response"}
        </span>
        </footer>
    </main>
)
    ;
}
