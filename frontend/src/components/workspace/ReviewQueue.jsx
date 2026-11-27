import React, { useState } from "react";
import { Check, X } from "lucide-react";
import { updateDecisionStatus } from "../../api/client";
import { SectionEmpty, SectionError, SectionLoading, fmtDate } from "./shared";

export function ReviewQueue({
  decisions,
  decisionsLoading,
  decisionsError,
  onDecisionUpdated,
}) {
  const proposed = decisions.filter((d) => d.status === "proposed");
  const [busy, setBusy] = useState({});
  const [msgs, setMsgs] = useState({});

  const handleAction = async (decision, newStatus) => {
    setBusy((p) => ({ ...p, [decision.decision_id]: newStatus }));
    setMsgs((p) => ({ ...p, [decision.decision_id]: null }));
    try {
      const updated = await updateDecisionStatus(decision.decision_id, newStatus);
      setMsgs((p) => ({
        ...p,
        [decision.decision_id]: { ok: true, text: `Decision ${newStatus}.` },
      }));
      if (onDecisionUpdated) onDecisionUpdated(updated);
    } catch (err) {
      setMsgs((p) => ({
        ...p,
        [decision.decision_id]: {
          ok: false,
          text: err.message || `Decision ${newStatus === "active" ? "approval" : "rejection"} failed.`,
        },
      }));
    } finally {
      setBusy((p) => ({ ...p, [decision.decision_id]: null }));
    }
  };

  if (decisionsLoading) {
    return (
      <section style={{ background: "var(--bg-surface)", border: "1px solid var(--border-subtle)", borderRadius: "8px", padding: "24px" }}>
        <SectionLoading label="Loading proposed decisions…" />
      </section>
    );
  }

  if (decisionsError) {
    return <SectionError message={decisionsError} />;
  }

  if (proposed.length === 0) {
    return (
      <section style={{ background: "var(--bg-surface)", border: "1px solid var(--border-subtle)", borderRadius: "8px", padding: "24px" }}>
        <SectionEmpty label="No proposed decisions require review." />
      </section>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
      <div style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "4px" }}>
        {proposed.length} proposed decision{proposed.length !== 1 ? "s" : ""} awaiting human review.
      </div>
      {proposed.map((d) => (
        <div
          key={d.decision_id}
          style={{
            background: "var(--bg-surface)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "8px",
            padding: "14px 16px",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "12px", flexWrap: "wrap" }}>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: "14px", fontWeight: 600 }}>{d.title}</div>
              <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "3px" }}>
                {d.description}
              </div>
              {d.reason_text && (
                <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "3px", fontStyle: "italic" }}>
                  Rationale: {d.reason_text}
                </div>
              )}
              <div style={{ display: "flex", gap: "8px", marginTop: "6px", flexWrap: "wrap" }}>
                <span style={{ fontSize: "11px", color: "#f59e0b", fontWeight: 600 }}>status: {d.status}</span>
                <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>{d.decision_type}</span>
                {d.decided_at && (
                  <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>{fmtDate(d.decided_at)}</span>
                )}
                {d.reason_confidence != null && (
                  <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                    conf: {(d.reason_confidence * 100).toFixed(0)}%
                  </span>
                )}
              </div>
            </div>

            <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
              <button
                type="button"
                onClick={() => handleAction(d, "active")}
                disabled={!!busy[d.decision_id]}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "4px",
                  padding: "5px 12px",
                  borderRadius: "4px",
                  border: "none",
                  background: busy[d.decision_id] === "active" ? "#059669" : "#10b981",
                  color: "#fff",
                  fontSize: "12px",
                  fontWeight: 600,
                  cursor: busy[d.decision_id] ? "not-allowed" : "pointer",
                  opacity: busy[d.decision_id] && busy[d.decision_id] !== "active" ? 0.5 : 1,
                }}
              >
                <Check size={13} />
                {busy[d.decision_id] === "active" ? "Approving…" : "Approve"}
              </button>
              <button
                type="button"
                onClick={() => handleAction(d, "rejected")}
                disabled={!!busy[d.decision_id]}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "4px",
                  padding: "5px 12px",
                  borderRadius: "4px",
                  border: "1px solid rgba(239,68,68,0.4)",
                  background: "transparent",
                  color: "#f87171",
                  fontSize: "12px",
                  fontWeight: 600,
                  cursor: busy[d.decision_id] ? "not-allowed" : "pointer",
                  opacity: busy[d.decision_id] && busy[d.decision_id] !== "rejected" ? 0.5 : 1,
                }}
              >
                <X size={13} />
                {busy[d.decision_id] === "rejected" ? "Rejecting…" : "Reject"}
              </button>
            </div>
          </div>

          {msgs[d.decision_id] && (
            <div style={{ marginTop: "6px", fontSize: "12px", color: msgs[d.decision_id].ok ? "#10b981" : "#f87171" }}>
              {msgs[d.decision_id].text}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
