import React from "react";

export function fmtDateTime(dt) {
  if (!dt) return "—";
  return new Date(dt).toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function fmtDate(dt) {
  if (!dt) return "—";
  return new Date(dt).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function statusColor(s) {
  if (s === "active") return "#10b981";
  if (s === "proposed") return "#f59e0b";
  if (s === "replaced") return "#6b7280";
  if (s === "rejected") return "#ef4444";
  return "var(--text-muted)";
}

export function OriginBadge({ origin }) {
  const map = {
    ai_exact: { label: "AI exact", color: "#6366f1" },
    ai_inferred: { label: "AI inferred", color: "#8b5cf6" },
    human: { label: "Human", color: "#10b981" },
  };
  const v = map[origin] || { label: origin || "unknown", color: "var(--text-muted)" };
  return (
    <span
      style={{
        display: "inline-block",
        padding: "1px 7px",
        borderRadius: "10px",
        fontSize: "11px",
        fontWeight: 600,
        background: `${v.color}22`,
        color: v.color,
        border: `1px solid ${v.color}44`,
        whiteSpace: "nowrap",
      }}
    >
      {v.label}
    </span>
  );
}

export function SectionError({ message }) {
  return (
    <div
      role="alert"
      style={{
        padding: "10px 14px",
        borderRadius: "6px",
        background: "rgba(239,68,68,0.08)",
        border: "1px solid rgba(239,68,68,0.25)",
        color: "#f87171",
        fontSize: "13px",
      }}
    >
      {message}
    </div>
  );
}

export function SectionLoading({ label = "Loading…" }) {
  return <div style={{ color: "var(--text-muted)", fontSize: "13px", padding: "12px 0" }}>{label}</div>;
}

export function SectionEmpty({ label = "No data." }) {
  return <div style={{ color: "var(--text-muted)", fontSize: "13px", padding: "12px 0" }}>{label}</div>;
}
