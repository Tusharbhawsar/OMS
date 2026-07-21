import { useEffect, useState } from "react";
import type { NotificationRecord } from "../types";
import { formatIstDateTime } from "../utils/date";
import { StatusBadge } from "./StatusBadge";

interface NotificationsPanelProps {
  notifications: NotificationRecord[];
  outageIdFilter: string;
  onOutageIdFilterChange: (value: string) => void;
  onRefresh: () => void;
  isLoading: boolean;
}

export function NotificationsPanel({
  notifications,
  outageIdFilter,
  onOutageIdFilterChange,
  onRefresh,
  isLoading,
}: NotificationsPanelProps) {
  const [currentPage, setCurrentPage] = useState(1);
  const rowsPerPage = 10;

  useEffect(() => {
    setCurrentPage(1);
  }, [notifications]);

  const totalPages = Math.max(1, Math.ceil(notifications.length / rowsPerPage));
  const startIndex = (currentPage - 1) * rowsPerPage;
  const visibleNotifications = notifications.slice(startIndex, startIndex + rowsPerPage);

  return (
    <section className="panel table-panel">
      <div className="panel-heading with-actions">
        <div>
          <p className="eyebrow">Delivery tracking</p>
          <h2>Notification log</h2>
        </div>
        <div className="filter-actions">
          <input
            value={outageIdFilter}
            onChange={(event) => onOutageIdFilterChange(event.target.value)}
            placeholder="Filter by outage ID"
          />
          <button type="button" className="secondary-button" disabled={isLoading} onClick={onRefresh}>
            {isLoading ? "Loading..." : "Refresh"}
          </button>
        </div>
      </div>

      <div className="table-scroll compact-table">
        <table>
          <thead>
            <tr>
              <th>Notification ID</th>
              <th>Outage</th>
              <th>Customer</th>
              <th>Type</th>
              <th>Channel</th>
              <th>Status</th>
              <th>Sent</th>
              <th>Delivered</th>
              <th>Message</th>
            </tr>
          </thead>
          <tbody>
            {notifications.length === 0 ? (
              <tr>
                <td colSpan={9} className="empty-cell">
                  No notifications found. Process a planned outage to create notifications.
                </td>
              </tr>
            ) : (
              visibleNotifications.map((notification) => (
                <tr key={notification.notification_id}>
                  <td className="mono">{notification.notification_id}</td>
                  <td className="mono">{notification.outage_id}</td>
                  <td className="mono">{notification.customer_id}</td>
                  <td>{notification.notification_type}</td>
                  <td>{notification.channel_id}</td>
                  <td>
                    <StatusBadge label={notification.status} />
                  </td>
                  <td>{formatIstDateTime(notification.sent_at)}</td>
                  <td>{formatIstDateTime(notification.delivered_at)}</td>
                  <td className="message-cell">{notification.message_content}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {notifications.length > rowsPerPage && (
        <div className="pagination-controls">
          <button
            type="button"
            className="secondary-button"
            disabled={currentPage === 1}
            onClick={() => setCurrentPage((p) => p - 1)}
          >
            Previous
          </button>
          <span className="pagination-info">
            Page {currentPage} of {totalPages}
          </span>
          <button
            type="button"
            className="secondary-button"
            disabled={currentPage === totalPages}
            onClick={() => setCurrentPage((p) => p + 1)}
          >
            Next
          </button>
        </div>
      )}
    </section>
  );
}
