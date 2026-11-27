import React from "react";
import { SectionEmpty, SectionError, SectionLoading, fmtDateTime } from "./shared";

export function ProjectTimeline({ timeline, loading, error, maxItems = 30, maxHeight }) {
  if (loading) return <SectionLoading label="Loading timeline…" />;
  if (error) return <SectionError message={error} />;
  if (!timeline || timeline.length === 0) return <SectionEmpty label="No timeline events yet." />;

  const items = timeline.slice(0, maxItems);
  return (
    <div style={{ display: "flex", flexDirection: "column", maxHeight, overflowY: maxHeight ? "auto" : "visible" }}>
      {items.map((ev, i) => (
        <div
          key={ev.event_id || i}
          style={{
            display: "flex",
            gap: "12px",
            padding: "8px 0",
            borderBottom: i < items.length - 1 ? "1px solid var(--border-subtle)" : "none",
            alignItems: "flex-start",
          }}
        >
          <div
            aria-hidden="true"
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              marginTop: 5,
              flexShrink: 0,
              background:
                ev.event_type === "commit"
                  ? "#10b981"
                  : ev.event_type === "decision"
                  ? "#6366f1"
                  : "#f59e0b",
            }}
          />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div
              style={{
                fontSize: "13px",
                fontWeight: 500,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {ev.title}
            </div>
            <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "2px" }}>
              {ev.event_type} · {fmtDateTime(ev.timestamp)}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
