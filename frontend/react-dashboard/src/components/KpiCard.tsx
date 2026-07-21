import type { ReactNode } from "react";

interface KpiCardProps {
  title: string;
  value: number | string;
  caption: string;
  icon: ReactNode;
  tone?: "default" | "critical" | "success" | "warning";
}

export function KpiCard({ title, value, caption, icon, tone = "default" }: KpiCardProps) {
  return (
    <article className={`kpi-card kpi-card-${tone}`}>
      <div className="kpi-card-header">
        <span className="kpi-icon">{icon}</span>
        <span>{title}</span>
      </div>
      <strong>{value}</strong>
      <p>{caption}</p>
    </article>
  );
}
