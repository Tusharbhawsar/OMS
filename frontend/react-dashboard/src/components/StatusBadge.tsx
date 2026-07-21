interface StatusBadgeProps {
  label: string;
}

const statusClassMap: Record<string, string> = {
  Active: "badge badge-danger",
  Scheduled: "badge badge-warning",
  Restored: "badge badge-success",
  Cancelled: "badge badge-muted",
  Delivered: "badge badge-success",
  Sent: "badge badge-info",
  Failed: "badge badge-danger",
};

export function StatusBadge({ label }: StatusBadgeProps) {
  const className = statusClassMap[label] ?? "badge badge-muted";
  return <span className={className}>{label}</span>;
}
