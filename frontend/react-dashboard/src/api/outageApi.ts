import { downloadFile, getJson, postJson, uploadFile } from "./client";
import type {
  ActiveOutageRow,
  AffectedCustomer,
  DashboardSummary,
  IngestionStatus,
  NotificationRecord,
  NotificationType,
  OutageEvent,
  ProcessingResult,
  UploadResult,
} from "../types";

export const outageApi = {
  getSummary(): Promise<DashboardSummary> {
    return getJson<DashboardSummary>("/dashboard/summary");
  },

  getActiveOutageRows(): Promise<ActiveOutageRow[]> {
    return getJson<ActiveOutageRow[]>("/dashboard/active-outages");
  },

  getActiveOutages(): Promise<OutageEvent[]> {
    return getJson<OutageEvent[]>("/outages/active");
  },

  getIngestionStatus(): Promise<IngestionStatus> {
    return getJson<IngestionStatus>("/uploads/ingestion-status");
  },

  getAffectedCustomers(outageId: string): Promise<AffectedCustomer[]> {
    return getJson<AffectedCustomer[]>(`/outages/${encodeURIComponent(outageId)}/affected-customers`);
  },

  processPlannedOutage(outageId: string, notificationType: NotificationType): Promise<ProcessingResult> {
    const params = new URLSearchParams({ notification_type: notificationType });
    return postJson<ProcessingResult>(`/outages/${encodeURIComponent(outageId)}/process-planned?${params.toString()}`);
  },

  processPlannedBatch(): Promise<ProcessingResult[]> {
    return postJson<ProcessingResult[]>("/outages/batch/process-planned");
  },

  cancelOutage(outageId: string): Promise<OutageEvent> {
    return postJson<OutageEvent>(`/outages/${encodeURIComponent(outageId)}/cancel`);
  },

  restoreOutage(outageId: string): Promise<OutageEvent> {
    return postJson<OutageEvent>(`/outages/${encodeURIComponent(outageId)}/restore`);
  },

  listNotifications(outageId?: string): Promise<NotificationRecord[]> {
    const params = new URLSearchParams({ limit: "200" });
    if (outageId) {
      params.set("outage_id", outageId);
    }
    return getJson<NotificationRecord[]>(`/notifications?${params.toString()}`);
  },

  uploadData(file: File): Promise<UploadResult> {
    return uploadFile<UploadResult>("/uploads/outage-data", file);
  },

  downloadLatestRebasedFile(): Promise<void> {
    return downloadFile("/uploads/rebased-file", "rebased_outage_data.xlsx");
  },
};
