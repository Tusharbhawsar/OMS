export interface ApiResponse<T> {
  status_code: number;
  message: string;
  data: T;
}

export interface DashboardSummary {
  active_outages: number;
  scheduled_pending: number;
  cancelled_outages: number;
  completed_outages: number;
  next_scheduled_outage_id: string | null;
  next_scheduled_start: string | null;
  seconds_until_next_scheduled: number | null;
  total_outages: number;
  affected_customers: number;
  medical_baseline_pending: number;
  notifications_sent: number;
  notifications_delivered: number;
  notifications_failed: number;
  delivery_rate_percent: number;
}

export interface ActiveOutageRow {
  outage_id: string;
  outage_type: string;
  status: string;
  region: string | null;
  affected_customers: number;
  medical_baseline_customers: number;
  notifications_sent: number;
  start_time: string | null;
  estimated_end_time: string | null;
}

export interface OutageEvent {
  outage_id: string;
  outage_type: string;
  status: string;
  start_time: string | null;
  estimated_end_time: string | null;
  actual_end_time: string | null;
  etr_predicted_by_ml: boolean;
  cancellation_flag: boolean;
  created_at: string;
}

export interface AffectedCustomer {
  customer_id: string;
  full_name: string;
  email: string | null;
  phone: string | null;
  channel_name: string;
  customer_type: string;
  priority: number;
  is_medical_baseline: boolean;
  service_point_id: string;
  circuit_id: string;
  transformer_id: string;
}

export interface NotificationRecord {
  notification_id: string;
  outage_id: string;
  customer_id: string;
  notification_type: string;
  channel_id: string;
  status: string;
  sent_at: string | null;
  delivered_at: string | null;
  message_content: string;
}

export interface UploadResult {
  file_name: string;
  imported_tables: Record<string, number>;
  skipped_sheets: string[];
}

export interface IngestionStatus {
  status: "Healthy" | "Waiting for feed" | string;
  source: string;
  mode: string;
  total_records: number;
  active_records: number;
  raw_events: number;
  last_received_at: string | null;
}

export interface ProcessingResult {
  outage_id: string;
  notification_type: string;
  affected_customers: number;
  notifications_created: number;
  notifications_delivered: number;
  medical_baseline_customers: number;
  processed_at: string;
}

export type NotificationType =
  | "Advance Notice"
  | "Reminder"
  | "Outage Start"
  | "Outage Restored"
  | "Cancellation Alert";
