import { Activity, AlertTriangle, Bell, Bot, CalendarClock, CheckCircle2, CircleCheckBig, Cpu, Database, Download, Network, Radar, RefreshCcw, Timer, UsersRound, XCircle, Zap } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { outageApi } from "./api/outageApi";
import { formatIstDateTime } from "./utils/date";
import { ActiveOutagesTable } from "./components/ActiveOutagesTable";
import { AffectedCustomersPanel } from "./components/AffectedCustomersPanel";
import { BrandHeader } from "./components/BrandHeader";
// import { DataIngestionStatusCard } from "./components/DataIngestionStatusCard";
import { ErrorBanner } from "./components/ErrorBanner";
import { KpiCard } from "./components/KpiCard";
import { NotificationsPanel } from "./components/NotificationsPanel";
import { OutageLifecycleCard } from "./components/OutageLifecycleCard";
import type {
  ActiveOutageRow,
  AffectedCustomer,
  DashboardSummary,
  IngestionStatus,
  NotificationRecord,
  NotificationType,
  OutageEvent,
  ProcessingResult,
} from "./types";

const emptySummary: DashboardSummary = {
  active_outages: 0,
  scheduled_pending: 0,
  cancelled_outages: 0,
  completed_outages: 0,
  next_scheduled_outage_id: null,
  next_scheduled_start: null,
  seconds_until_next_scheduled: null,
  total_outages: 0,
  affected_customers: 0,
  medical_baseline_pending: 0,
  notifications_sent: 0,
  notifications_delivered: 0,
  notifications_failed: 0,
  delivery_rate_percent: 0,
};

function formatCountdown(totalSeconds: number): string {
  if (totalSeconds <= 0) {
    return "Starting now";
  }
  const days = Math.floor(totalSeconds / 86400);
  const hours = Math.floor((totalSeconds % 86400) / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  const parts: string[] = [];
  if (days) parts.push(`${days}d`);
  if (hours || days) parts.push(`${hours}h`);
  if (minutes || hours || days) parts.push(`${minutes}m`);
  parts.push(`${seconds}s`);
  return parts.join(" ");
}

function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return "Something went wrong. Please check the backend logs.";
}

export default function App() {
  const [summary, setSummary] = useState<DashboardSummary>(emptySummary);
  const [countdown, setCountdown] = useState<number | null>(null);
  const [activeRows, setActiveRows] = useState<ActiveOutageRow[]>([]);
  const [ingestionStatus, setIngestionStatus] = useState<IngestionStatus | null>(null);
  const [notifications, setNotifications] = useState<NotificationRecord[]>([]);
  const [affectedCustomers, setAffectedCustomers] = useState<AffectedCustomer[]>([]);
  const [selectedOutageId, setSelectedOutageId] = useState<string | null>(null);
  const [notificationType, setNotificationType] = useState<NotificationType>("Advance Notice");
  const [notificationFilter, setNotificationFilter] = useState("");
  const [lastResult, setLastResult] = useState<ProcessingResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isCustomerLoading, setIsCustomerLoading] = useState(false);
  const [isNotificationLoading, setIsNotificationLoading] = useState(false);
  const [isDownloadingRebasedFile, setIsDownloadingRebasedFile] = useState(false);
  const [isLifecycleUpdating, setIsLifecycleUpdating] = useState(false);
  const [lastLifecycleOutage, setLastLifecycleOutage] = useState<OutageEvent | null>(null);

  // `silent` background refreshes (used by the auto-poll timer) update the data in
  // place without toggling the loading spinners or flashing the error banner, so the
  // dashboard updates live without UI flicker. A failed silent tick keeps the last
  // good data on screen — the next tick recovers.
  const refreshDashboard = useCallback(async (options?: { silent?: boolean }) => {
    const silent = options?.silent ?? false;
    if (!silent) {
      setIsLoading(true);
      setError(null);
    }
    try {
      const [nextSummary, nextRows, nextIngestionStatus] = await Promise.all([
        outageApi.getSummary(),
        outageApi.getActiveOutageRows(),
        outageApi.getIngestionStatus(),
      ]);
      setSummary(nextSummary);
      setActiveRows(nextRows);
      setIngestionStatus(nextIngestionStatus);
      setError(null);
    } catch (err) {
      if (!silent) {
        setError(getErrorMessage(err));
      }
    } finally {
      if (!silent) {
        setIsLoading(false);
      }
    }
  }, []);

  const refreshNotifications = useCallback(async (options?: { silent?: boolean }) => {
    const silent = options?.silent ?? false;
    if (!silent) {
      setIsNotificationLoading(true);
      setError(null);
    }
    try {
      const nextNotifications = await outageApi.listNotifications(notificationFilter.trim() || undefined);
      setNotifications(nextNotifications);
    } catch (err) {
      if (!silent) {
        setError(getErrorMessage(err));
      }
    } finally {
      if (!silent) {
        setIsNotificationLoading(false);
      }
    }
  }, [notificationFilter]);

  // Initial load, then live auto-refresh every few seconds so the dashboard reflects
  // scheduler-driven changes (status transitions, new notifications) without a manual
  // Refresh click.
  useEffect(() => {
    void refreshDashboard();
    void refreshNotifications();
    const POLL_INTERVAL_MS = 5000;
    const intervalId = window.setInterval(() => {
      void refreshDashboard({ silent: true });
      void refreshNotifications({ silent: true });
    }, POLL_INTERVAL_MS);
    return () => window.clearInterval(intervalId);
  }, [refreshDashboard, refreshNotifications]);

  // Live countdown to the next scheduled outage. Re-seeds from the server on every
  // dashboard refresh, then ticks down locally once per second.
  useEffect(() => {
    setCountdown(summary.seconds_until_next_scheduled);
    if (summary.seconds_until_next_scheduled === null) {
      return;
    }
    const intervalId = window.setInterval(() => {
      setCountdown((current) => (current === null || current <= 0 ? current : current - 1));
    }, 1000);
    return () => window.clearInterval(intervalId);
  }, [summary.seconds_until_next_scheduled]);

  async function handleViewCustomers(outageId: string) {
    setSelectedOutageId(outageId);
    setIsCustomerLoading(true);
    setError(null);
    try {
      const customers = await outageApi.getAffectedCustomers(outageId);
      setAffectedCustomers(customers);
      await refreshDashboard();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsCustomerLoading(false);
    }
  }

  async function handleProcessOutage(outageId: string) {
    setIsProcessing(true);
    setError(null);
    try {
      const result = await outageApi.processPlannedOutage(outageId, notificationType);
      setLastResult(result);
      setNotificationFilter(outageId);
      await refreshDashboard();
      const nextNotifications = await outageApi.listNotifications(outageId);
      setNotifications(nextNotifications);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsProcessing(false);
    }
  }

  async function handleBatchProcess() {
    setIsProcessing(true);
    setError(null);
    try {
      const results = await outageApi.processPlannedBatch();
      setLastResult(results[0] ?? null);
      await refreshDashboard();
      await refreshNotifications();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsProcessing(false);
    }
  }

  async function handleDownloadRebasedFile() {
    setIsDownloadingRebasedFile(true);
    setError(null);
    try {
      await outageApi.downloadLatestRebasedFile();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsDownloadingRebasedFile(false);
    }
  }

  async function handleLifecycleUpdate(outageId: string, action: "cancel" | "restore") {
    setIsLifecycleUpdating(true);
    setError(null);
    try {
      const outage = action === "cancel"
        ? await outageApi.cancelOutage(outageId)
        : await outageApi.restoreOutage(outageId);
      setLastLifecycleOutage(outage);
      setNotificationFilter(outageId);
      await refreshDashboard();
      setNotifications(await outageApi.listNotifications(outageId));
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLifecycleUpdating(false);
    }
  }

  const deliveryCaption = useMemo(() => {
    return `${summary.notifications_delivered}/${summary.notifications_sent} delivered`;
  }, [summary.notifications_delivered, summary.notifications_sent]);

  return (
    <>
    <BrandHeader />
    <main className="app-shell">
      <header className="hero">
        <div>
          {/* <p className="eyebrow">Real-Time Outage Operations System</p> */}
          <h1>Outage Communication System</h1>
          <p>
            Monitor active outages, customer impact, priority notifications, delivery performance, and agent workflow execution in real time.
          </p>
        </div>
        <div className="hero-actions">
          <button className="secondary-button" type="button" disabled={isLoading} onClick={() => refreshDashboard()}>
            <RefreshCcw size={16} /> {isLoading ? "Refreshing..." : "Refresh"}
          </button>
          <button
            className="secondary-button"
            type="button"
            disabled={isDownloadingRebasedFile}
            onClick={handleDownloadRebasedFile}
          >
            <Download size={16} /> {isDownloadingRebasedFile ? "Downloading..." : "Download Rebased File"}
          </button>
          {/* ---------------------- */}
          <button className="primary-button" type="button" disabled={isProcessing} onClick={handleBatchProcess}>
            <Bell size={16} /> {isProcessing ? "Processing..." : "Run Notification Workflow"}
          </button>
        </div>
      </header>

      <ErrorBanner message={error} onDismiss={() => setError(null)} />

      {lastResult && (
        <section className="result-banner">
          <CheckCircle2 size={18} />
          <span>
            Processed <strong>{lastResult.outage_id}</strong>: {lastResult.notifications_created} notifications created,
            {" "}
            {lastResult.medical_baseline_customers} Medical Baseline customers prioritized.
          </span>
        </section>
      )}

      <section className="kpi-grid">
        <KpiCard
          title="Active Outages"
          value={summary.active_outages}
          caption="Power is currently out for customers"
          icon={<Activity size={20} />}
          tone="critical"
        />
        <KpiCard
          title="Scheduled / Pending"
          value={summary.scheduled_pending}
          caption="Planned for the future, not started yet"
          icon={<CalendarClock size={20} />}
        />
        <KpiCard
          title="Next Scheduled Outage"
          value={countdown !== null ? formatCountdown(countdown) : "—"}
          caption={
            summary.next_scheduled_outage_id
              ? `${summary.next_scheduled_outage_id} · ${formatIstDateTime(summary.next_scheduled_start)}`
              : "No upcoming outages"
          }
          icon={<Timer size={20} />}
        />
        <KpiCard
          title="Cancelled Outages"
          value={summary.cancelled_outages}
          caption="Planned work that was called off"
          icon={<XCircle size={20} />}
          tone="warning"
        />
        <KpiCard
          title="Completed Outages"
          value={summary.completed_outages}
          caption={`${summary.total_outages} total outage records`}
          icon={<CircleCheckBig size={20} />}
          tone="success"
        />
        <KpiCard
          title="Affected Customers"
          value={summary.affected_customers}
          caption="Mapped through circuit and transformer"
          icon={<UsersRound size={20} />}
        />
        <KpiCard
          title="Medical Pending"
          value={summary.medical_baseline_pending}
          caption="Highest priority notification segment"
          icon={<AlertTriangle size={20} />}
          tone="warning"
        />
        <KpiCard
          title="Delivery Rate"
          value={`${summary.delivery_rate_percent}%`}
          caption={deliveryCaption}
          icon={<CheckCircle2 size={20} />}
          tone="success"
        />
        <KpiCard
          title="Failed Notifications"
          value={summary.notifications_failed}
          caption="Provider failures"
          icon={<Database size={20} />}
        />
      </section>

      <section className="agent-status-section">
        <div className="section-heading">
          <h2>Agent Workflow</h2>
        </div>
        <div className="agent-grid">
          <div className="agent-card">
            <div className="agent-header">
              <div className="status-indicator active"><Radar size={14} /></div>
              <h3>Outage Detection Agent</h3>
            </div>
            <p>Monitoring ADMS and SCADA events</p>
          </div>
          <div className="agent-card">
            <div className="agent-header">
              <div className="status-indicator active"><Network size={14} /></div>
              <h3>Customer Impact Agent</h3>
            </div>
            <p>Mapping topology to customer meters</p>
          </div>
          <div className="agent-card">
            <div className="agent-header">
              <div className="status-indicator active"><Bot size={14} /></div>
              <h3>Notification Orchestration Agent</h3>
            </div>
            <p>Preparing multi-channel messages</p>
          </div>
          {/* ---------------------------------------------------------------- */}
          {/* <div className="agent-card">
            <div className="agent-header">
              <div className="status-indicator active"><Activity size={14} /></div>
              <h3>Delivery Monitoring Agent</h3>
            </div>
            <p>Tracking delivery receipts and retries</p>
          </div> */}
        </div>
      </section>
      {/* <DataIngestionStatusCard
        summary={summary}
        ingestionStatus={ingestionStatus}
        isRefreshing={isLoading}
        onRefresh={refreshDashboard}
      /> */}

      <OutageLifecycleCard
        activeOutages={activeRows}
        isSubmitting={isLifecycleUpdating}
        lastUpdatedOutage={lastLifecycleOutage}
        onCancel={(outageId) => handleLifecycleUpdate(outageId, "cancel")}
        onRestore={(outageId) => handleLifecycleUpdate(outageId, "restore")}
      />

      <ActiveOutagesTable
        rows={activeRows}
        isProcessing={isProcessing}
        selectedNotificationType={notificationType}
        onNotificationTypeChange={setNotificationType}
        onViewCustomers={handleViewCustomers}
        onProcessOutage={handleProcessOutage}
      />

      <AffectedCustomersPanel
        outageId={selectedOutageId}
        customers={affectedCustomers}
        isLoading={isCustomerLoading}
        onClose={() => {
          setSelectedOutageId(null);
          setAffectedCustomers([]);
        }}
      />

      <NotificationsPanel
        notifications={notifications}
        outageIdFilter={notificationFilter}
        onOutageIdFilterChange={setNotificationFilter}
        onRefresh={refreshNotifications}
        isLoading={isNotificationLoading}
      />
    </main>
    </>
  );
}
