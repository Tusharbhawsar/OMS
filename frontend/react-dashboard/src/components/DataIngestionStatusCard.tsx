import { CheckCircle2, Database, RefreshCcw, ServerCog } from "lucide-react";
import type { DashboardSummary, IngestionStatus } from "../types";

interface DataIngestionStatusCardProps {
  summary: DashboardSummary;
  ingestionStatus: IngestionStatus | null;
  isRefreshing: boolean;
  onRefresh: () => void | Promise<void>;
}

export function DataIngestionStatusCard({
  summary,
  ingestionStatus,
  isRefreshing,
  onRefresh,
}: DataIngestionStatusCardProps) {
  const totalRecords = ingestionStatus?.total_records ?? summary.total_outages;
  const activeRecords = ingestionStatus?.active_records ?? summary.active_outages;
  const source = ingestionStatus?.source ?? "Backend System Feed";
  const statusLabel = ingestionStatus?.status ?? (totalRecords > 0 ? "Healthy" : "Waiting for feed");
  const hasOutageData = totalRecords > 0;
  const statusTone = hasOutageData ? "success" : "muted";

  return (
    <section className="panel ingestion-panel">
      <div className="panel-heading with-actions">
        <div>
          <p className="eyebrow">Data Ingestion</p>
          <h1>Backend system feed</h1>
        </div>
        <button className="secondary-button" type="button" disabled={isRefreshing} onClick={onRefresh}>
          <RefreshCcw size={16} /> {isRefreshing ? "Refreshing..." : "Refresh Status"}
        </button>
      </div>

      <div className="ingestion-overview">
        <div className={`ingestion-status ingestion-status-${statusTone}`}>
          <span className="ingestion-icon">
            {hasOutageData ? <CheckCircle2 size={22} /> : <ServerCog size={22} />}
          </span>
          <div>
            <strong>{statusLabel}</strong>
            <span>Outage records are ingested by backend services.</span>
          </div>
        </div>

        <div className="ingestion-metrics">
          <div>
          <span>Total Records</span>
            <strong>{totalRecords}</strong>
          </div>
          <div>
            <span>Active Feed Rows</span>
            <strong>{activeRecords}</strong>
          </div>
          <div>
            <span>Source</span>
            <strong>{source}</strong>
          </div>
        </div>
      </div>

      <div className="ingestion-pipeline" aria-label="Backend ingestion pipeline">
        {/* <div>
          <Database size={16} />
          <span>ADMS / SCADA / outage source</span>
        </div>
        <div>
          <ServerCog size={16} />
          <span>Backend validation and normalization</span>
        </div>
        <div>
          <CheckCircle2 size={16} />
          <span>Dashboard reads processed outage data</span>
        </div> */}
      </div>
    </section>
  );
}
