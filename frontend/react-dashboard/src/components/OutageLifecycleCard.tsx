import { Ban, CheckCircle2, RotateCcw } from "lucide-react";
import { useState } from "react";
import type { ActiveOutageRow, OutageEvent } from "../types";
import { formatIstDateTime } from "../utils/date";

interface OutageLifecycleCardProps {
  activeOutages: ActiveOutageRow[];
  isSubmitting: boolean;
  lastUpdatedOutage: OutageEvent | null;
  onCancel: (outageId: string) => void | Promise<void>;
  onRestore: (outageId: string) => void | Promise<void>;
}

export function OutageLifecycleCard({
  activeOutages,
  isSubmitting,
  lastUpdatedOutage,
  onCancel,
  onRestore,
}: OutageLifecycleCardProps) {
  const [outageId, setOutageId] = useState("");
  const normalizedOutageId = outageId.trim();

  function submit(action: "cancel" | "restore") {
    if (!normalizedOutageId) return;
    void (action === "cancel" ? onCancel(normalizedOutageId) : onRestore(normalizedOutageId));
  }

  return (
    <section className="panel outage-lifecycle-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Outage lifecycle</p>
          <h2>Cancel or Restore an Outage</h2>
        </div>
      </div>

      <div className="outage-lifecycle-controls">
        <label className="outage-id-label" htmlFor="lifecycle-outage-id">
          Outage ID
          <input
            id="lifecycle-outage-id"
            list="active-outage-ids"
            value={outageId}
            onChange={(event) => setOutageId(event.target.value)}
            placeholder="e.g. OTG_001"
            disabled={isSubmitting}
          />
        </label>
        <datalist id="active-outage-ids">
          {activeOutages.map((outage) => <option key={outage.outage_id} value={outage.outage_id} />)}
        </datalist>
        <button
          className="secondary-button lifecycle-cancel-button"
          type="button"
          disabled={!normalizedOutageId || isSubmitting}
          onClick={() => submit("cancel")}
        >
          <Ban size={16} /> {isSubmitting ? "Updating..." : "Cancel Outage"}
        </button>
        <button
          className="primary-button lifecycle-restore-button"
          type="button"
          disabled={!normalizedOutageId || isSubmitting}
          onClick={() => submit("restore")}
        >
          <RotateCcw size={16} /> {isSubmitting ? "Updating..." : "Restore Outage"}
        </button>
      </div>

      <p className="lifecycle-help">Choose an active outage ID, then record its cancellation or restoration time through the backend.</p>

      {lastUpdatedOutage && (
        <div className="lifecycle-result" role="status">
          <CheckCircle2 size={18} />
          <span>
            <strong>{lastUpdatedOutage.outage_id}</strong> is {lastUpdatedOutage.status}. {lastUpdatedOutage.cancelled_at
              ? `Cancelled: ${formatIstDateTime(lastUpdatedOutage.cancelled_at)}`
              : `Restored: ${formatIstDateTime(lastUpdatedOutage.actual_end_time)}`}
          </span>
        </div>
      )}
    </section>
  );
}
