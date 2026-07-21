import { BellRing, Eye, Send } from "lucide-react";
import type { ActiveOutageRow, NotificationType } from "../types";
import { formatIstDateTime } from "../utils/date";
import { StatusBadge } from "./StatusBadge";

interface ActiveOutagesTableProps {
  rows: ActiveOutageRow[];
  isProcessing: boolean;
  selectedNotificationType: NotificationType;
  onNotificationTypeChange: (value: NotificationType) => void;
  onViewCustomers: (outageId: string) => void;
  onProcessOutage: (outageId: string) => void;
}

const notificationTypes: NotificationType[] = [
  "Advance Notice",
  "Reminder",
  "Outage Start",
  "Outage Restored",
  "Cancellation Alert",
];

export function ActiveOutagesTable({
  rows,
  isProcessing,
  selectedNotificationType,
  onNotificationTypeChange,
  onViewCustomers,
  onProcessOutage,
}: ActiveOutagesTableProps) {
  return (
    <section className="panel table-panel">
      <div className="panel-heading with-actions">
        <div>
          <p className="eyebrow">Operations</p>
          <h2>Active planned outages</h2>
        </div>
        <label className="select-label">
          Notification type
          <select
            value={selectedNotificationType}
            onChange={(event) => onNotificationTypeChange(event.target.value as NotificationType)}
          >
            {notificationTypes.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Outage ID</th>
              <th>Type</th>
              <th>Status</th>
              <th>Region</th>
              <th>Affected</th>
              <th>Medical</th>
              <th>Sent</th>
              <th>Start</th>
              <th>ETR</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={10} className="empty-cell">
                  Upload data or run migrations to see active outages.
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr key={row.outage_id}>
                  <td className="mono">{row.outage_id}</td>
                  <td>{row.outage_type}</td>
                  <td>
                    <StatusBadge label={row.status} />
                  </td>
                  <td>{row.region ?? "-"}</td>
                  <td>{row.affected_customers}</td>
                  <td>
                    <span className={row.medical_baseline_customers > 0 ? "medical-chip" : "muted"}>
                      {row.medical_baseline_customers}
                    </span>
                  </td>
                  <td>{row.notifications_sent}</td>
                  <td>{formatIstDateTime(row.start_time)}</td>
                  <td>{formatIstDateTime(row.estimated_end_time)}</td>
                  <td>
                    <div className="row-actions">
                      <button type="button" className="icon-button" onClick={() => onViewCustomers(row.outage_id)}>
                        <Eye size={16} /> Customers
                      </button>
                      <button
                        type="button"
                        className="icon-button primary-action"
                        disabled={isProcessing}
                        onClick={() => onProcessOutage(row.outage_id)}
                      >
                        <Send size={16} /> Process
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="table-footer-note">
        <BellRing size={16} /> Medical Baseline customers are prioritized by backend customer mapping.
      </div>
    </section>
  );
}
