import React from "react";
import { Shield, ArrowRight, CheckCircle2, XCircle, HelpCircle } from "lucide-react";

export function DecisionCard({ decision }) {
  const isReplaced = decision.status === "replaced";
  const isActive = decision.status === "active";
  const isProposed = decision.status === "proposed";

  return (
    <div style={{
      background: "var(--bg-surface)",
      border: "1px solid var(--border-subtle)",
      borderRadius: "6px",
      padding: "16px 20px",
      marginBottom: "12px",
      opacity: isReplaced ? 0.75 : 1,
    }}>
      {/* Top Header */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "16px", marginBottom: "8px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "4px" }}>
            <span style={{ fontWeight: 600, fontSize: "15px", color: isReplaced ? "var(--text-secondary)" : "var(--text-main)" }}>
              {decision.title}
            </span>
            <span className={`badge ${isActive ? "badge-active" : isReplaced ? "badge-replaced" : "badge-proposed"}`}>
              {decision.status}
            </span>
            <span className="badge" style={{ background: "var(--bg-surface-elevated)", color: "var(--text-secondary)" }}>
              {decision.decision_type}
            </span>
          </div>
          <p style={{ color: "var(--text-secondary)", fontSize: "13px" }}>
            {decision.description}
          </p>
        </div>

        <span className="font-mono" style={{ fontSize: "11px", color: "var(--text-muted)", whiteSpace: "nowrap" }}>
          {new Date(decision.decided_at).toLocaleDateString()}
        </span>
      </div>

      {/* Rationale & Source Confidence */}
      {decision.reason_text && (
        <div style={{
          background: "var(--bg-app)",
          border: "1px solid var(--border-subtle)",
          borderRadius: "4px",
          padding: "10px 14px",
          margin: "12px 0",
          fontSize: "12px",
        }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "4px" }}>
            <span style={{ fontSize: "11px", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase" }}>
              Architectural Rationale
            </span>
            <span className="font-mono" style={{ fontSize: "11px", color: decision.reason_source_type === "EXPLICIT" ? "var(--color-human)" : "var(--color-ai-inferred)" }}>
              {decision.reason_source_type} ({(decision.reason_confidence * 100).toFixed(0)}% conf)
            </span>
          </div>
          <p style={{ color: "var(--text-main)", fontStyle: "italic" }}>
            "{decision.reason_text}"
          </p>
        </div>
      )}

      {/* Evaluated Alternatives */}
      {decision.alternatives && decision.alternatives.length > 0 && (
        <div style={{ marginTop: "10px" }}>
          <span style={{ fontSize: "11px", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", display: "block", marginBottom: "6px" }}>
            Evaluated Alternatives
          </span>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
            {decision.alternatives.map((alt, idx) => {
              const isSelected = alt.selection_status === "selected";
              const isRejected = alt.selection_status === "rejected";
              return (
                <span
                  key={idx}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "6px",
                    padding: "3px 8px",
                    borderRadius: "4px",
                    fontSize: "11px",
                    fontWeight: 500,
                    background: isSelected ? "rgba(16, 185, 129, 0.1)" : "rgba(239, 68, 68, 0.08)",
                    color: isSelected ? "#34d399" : "#f87171",
                    border: `1px solid ${isSelected ? "rgba(16, 185, 129, 0.25)" : "rgba(239, 68, 68, 0.2)"}`,
                    textDecoration: isRejected ? "line-through" : "none",
                  }}
                >
                  {isSelected ? <CheckCircle2 size={12} /> : <XCircle size={12} />}
                  {alt.description}
                </span>
              );
            })}
          </div>
        </div>
      )}

      {/* Replacement Link (Recursive Lineage) */}
      {decision.replaced_by_decision_id && (
        <div style={{
          marginTop: "12px",
          display: "flex",
          alignItems: "center",
          gap: "8px",
          fontSize: "12px",
          color: "var(--color-ai-inferred)",
        }}>
          <ArrowRight size={14} />
          <span>Superseded by later engineering decision:</span>
          <span className="font-mono" style={{ textDecoration: "underline" }}>
            {decision.replaced_by_decision_id.slice(0, 16)}...
          </span>
        </div>
      )}
    </div>
  );
}
