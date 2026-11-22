import React from "react";
import { GitCommit, Shield, Cpu, MessageSquare } from "lucide-react";

export function Timeline({ events }) {
  if (!events || events.length === 0) {
    return <div style={{ color: "var(--text-muted)", padding: "24px 0" }}>No timeline events recorded yet.</div>;
  }

  const getEventIcon = (type) => {
    switch (type) {
      case "commit":
        return <GitCommit size={14} color="#38bdf8" />;
      case "decision":
        return <Shield size={14} color="#10b981" />;
      case "interaction":
        return <MessageSquare size={14} color="#818cf8" />;
      default:
        return <Cpu size={14} color="#9ca3af" />;
    }
  };

  return (
    <div style={{ position: "relative", paddingLeft: "24px" }}>
      {/* Vertical timeline spine */}
      <div style={{
        position: "absolute",
        left: "7px",
        top: "8px",
        bottom: "8px",
        width: "2px",
        background: "var(--border-subtle)",
      }} />

      {events.map((ev, idx) => (
        <div key={ev.event_id || idx} style={{ position: "relative", marginBottom: "20px" }}>
          {/* Node marker */}
          <div style={{
            position: "absolute",
            left: "-24px",
            top: "2px",
            width: "16px",
            height: "16px",
            borderRadius: "50%",
            background: "var(--bg-surface)",
            border: "1px solid var(--border-strong)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}>
            {getEventIcon(ev.event_type)}
          </div>

          {/* Event Content */}
          <div style={{
            background: "var(--bg-surface)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "6px",
            padding: "12px 16px",
          }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "4px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <span style={{ fontWeight: 600, fontSize: "14px" }}>{ev.title}</span>
                <span className="badge" style={{ background: "var(--bg-app)", color: "var(--text-muted)" }}>
                  {ev.event_type}
                </span>
              </div>
              <span className="font-mono" style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                {new Date(ev.timestamp).toLocaleString()}
              </span>
            </div>

            {/* Event Specific Metadata */}
            {ev.details && (
              <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "6px" }}>
                {ev.details.commit_hash && (
                  <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                    <span className="font-mono" style={{ color: "var(--color-ai-exact)", background: "rgba(56, 189, 248, 0.1)", padding: "1px 6px", borderRadius: "3px" }}>
                      {ev.details.commit_hash.slice(0, 10)}
                    </span>
                    <span>{ev.details.message}</span>
                  </div>
                )}

                {ev.details.prompt_preview && (
                  <div style={{ fontStyle: "italic", color: "var(--text-main)" }}>
                    "{ev.details.prompt_preview}"
                  </div>
                )}

                {ev.details.decision_type && (
                  <div style={{ display: "flex", gap: "8px", marginTop: "4px" }}>
                    <span>Type: <strong>{ev.details.decision_type}</strong></span>
                    <span>Status: <strong>{ev.details.status}</strong></span>
                    <span>Rationale: <strong>{ev.details.reason_source_type}</strong></span>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
