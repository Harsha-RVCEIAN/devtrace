import React, { useState } from "react";
import {
  GitCommit,
  GitBranch,
  ArrowRight,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Sparkles,
  Layers,
  Shield,
  Database,
  Cpu,
  Server,
  CornerDownRight,
  Check,
  ChevronRight,
  Info,
} from "lucide-react";

const CATEGORY_META = {
  architecture: {
    label: "Database & Architecture",
    icon: Database,
    color: "#38bdf8",
    bg: "rgba(56, 189, 248, 0.1)",
  },
  security: {
    label: "Security & Authentication",
    icon: Shield,
    color: "#f59e0b",
    bg: "rgba(245, 158, 11, 0.1)",
  },
  implementation: {
    label: "API & Data Access",
    icon: Cpu,
    color: "#10b981",
    bg: "rgba(16, 185, 129, 0.1)",
  },
  infrastructure: {
    label: "Infrastructure & Platform",
    icon: Server,
    color: "#818cf8",
    bg: "rgba(129, 140, 248, 0.1)",
  },
};

export function DecisionGraph({ decisions = [], onSelectDecision }) {
  const [selectedId, setSelectedId] = useState(
    decisions.length > 0 ? decisions[0].decision_id : null
  );
  const [categoryFilter, setCategoryFilter] = useState("all");

  const selectedDecision = decisions.find((d) => d.decision_id === selectedId) || decisions[0];

  // Group decisions by architectural domain/category
  const categories = ["architecture", "security", "implementation", "infrastructure"];

  const filteredDecisions = decisions.filter((d) => {
    if (categoryFilter === "all") return true;
    return d.decision_type === categoryFilter;
  });

  // Find replacement relationships
  const decisionMap = new Map(decisions.map((d) => [d.decision_id, d]));

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* Category Filter Pills */}
      <div style={{ display: "flex", gap: "8px", alignItems: "center", flexWrap: "wrap" }}>
        <button
          onClick={() => setCategoryFilter("all")}
          style={{
            padding: "5px 12px",
            borderRadius: "4px",
            fontSize: "12px",
            fontWeight: 500,
            cursor: "pointer",
            background: categoryFilter === "all" ? "var(--border-strong)" : "var(--bg-surface)",
            color: categoryFilter === "all" ? "#fff" : "var(--text-secondary)",
            border: "1px solid var(--border-subtle)",
          }}
        >
          All Domains ({decisions.length})
        </button>
        {categories.map((catKey) => {
          const meta = CATEGORY_META[catKey] || { label: catKey, color: "#9ca3af" };
          const count = decisions.filter((d) => d.decision_type === catKey).length;
          if (count === 0) return null;
          const isActive = categoryFilter === catKey;
          return (
            <button
              key={catKey}
              onClick={() => setCategoryFilter(catKey)}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                padding: "5px 12px",
                borderRadius: "4px",
                fontSize: "12px",
                fontWeight: 500,
                cursor: "pointer",
                background: isActive ? meta.color + "22" : "var(--bg-surface)",
                color: isActive ? meta.color : "var(--text-secondary)",
                border: `1px solid ${isActive ? meta.color + "55" : "var(--border-subtle)"}`,
              }}
            >
              <meta.icon size={13} color={meta.color} />
              {meta.label} ({count})
            </button>
          );
        })}
      </div>

      {/* Main Graph Grid: Node Canvas on Left, Active Inspector on Right */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1.35fr 0.9fr",
          gap: "20px",
          alignItems: "start",
        }}
      >
        {/* Left Column: Visual Decision Graph Canvas */}
        <div
          style={{
            background: "var(--bg-surface)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "6px",
            padding: "20px",
            display: "flex",
            flexDirection: "column",
            gap: "24px",
          }}
        >
          {/* Header of Canvas */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <GitBranch size={16} color="var(--color-primary)" />
              <span style={{ fontSize: "13px", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--text-muted)" }}>
                Architectural Decision DAG & Lineage Flow
              </span>
            </div>
            <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
              Click any node to inspect lineage & alternatives
            </span>
          </div>

          {/* Render category tracks or clusters */}
          {categories.map((catKey) => {
            const catDecisions = filteredDecisions.filter((d) => d.decision_type === catKey);
            if (catDecisions.length === 0) return null;
            const meta = CATEGORY_META[catKey] || { label: catKey, color: "#9ca3af", icon: Layers };
            const Icon = meta.icon;

            // Separate into replaced ancestors vs active/proposed leaves to show replacement flow
            const replacedDecisions = catDecisions.filter((d) => d.status === "replaced");
            const activeOrProposed = catDecisions.filter((d) => d.status !== "replaced");

            return (
              <div
                key={catKey}
                style={{
                  background: "var(--bg-app)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "6px",
                  padding: "16px",
                }}
              >
                {/* Domain Track Header */}
                <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "14px" }}>
                  <div
                    style={{
                      width: "24px",
                      height: "24px",
                      borderRadius: "4px",
                      background: meta.bg,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                  >
                    <Icon size={14} color={meta.color} />
                  </div>
                  <span style={{ fontSize: "13px", fontWeight: 600, color: "var(--text-main)" }}>
                    {meta.label}
                  </span>
                </div>

                {/* Nodes & Lineage Chains */}
                <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                  {/* Case 1: Pairs with Replacement Lineage */}
                  {replacedDecisions.map((oldDec) => {
                    const replacement = oldDec.replaced_by_decision_id
                      ? decisionMap.get(oldDec.replaced_by_decision_id)
                      : null;

                    return (
                      <div
                        key={oldDec.decision_id}
                        style={{
                          background: "var(--bg-surface)",
                          border: "1px solid var(--border-subtle)",
                          borderRadius: "6px",
                          padding: "14px",
                        }}
                      >
                        {/* Old Superseded Node */}
                        <DecisionNodeCard
                          decision={oldDec}
                          isSelected={selectedId === oldDec.decision_id}
                          onClick={() => setSelectedId(oldDec.decision_id)}
                        />

                        {/* Visual Superseding Connector Edge */}
                        <div
                          style={{
                            margin: "10px 0 10px 24px",
                            paddingLeft: "16px",
                            borderLeft: "2px dashed var(--color-ai-inferred)",
                            display: "flex",
                            alignItems: "center",
                            gap: "8px",
                            color: "var(--color-ai-inferred)",
                            fontSize: "11px",
                            fontFamily: "var(--font-mono)",
                          }}
                        >
                          <CornerDownRight size={14} />
                          <span>SUPERSEDED & REPLACED BY</span>
                        </div>

                        {/* Active Replacement Node */}
                        {replacement && (
                          <div style={{ paddingLeft: "24px" }}>
                            <DecisionNodeCard
                              decision={replacement}
                              isSelected={selectedId === replacement.decision_id}
                              onClick={() => setSelectedId(replacement.decision_id)}
                              highlightActive
                            />
                          </div>
                        )}
                      </div>
                    );
                  })}

                  {/* Case 2: Decisions without replacement chains (Independent Roots) */}
                  {activeOrProposed
                    .filter((d) => !replacedDecisions.some((old) => old.replaced_by_decision_id === d.decision_id))
                    .map((dec) => (
                      <DecisionNodeCard
                        key={dec.decision_id}
                        decision={dec}
                        isSelected={selectedId === dec.decision_id}
                        onClick={() => setSelectedId(dec.decision_id)}
                      />
                    ))}
                </div>
              </div>
            );
          })}
        </div>

        {/* Right Column: Deep-Dive Decision Inspector Panel */}
        {selectedDecision && (
          <div
            style={{
              background: "var(--bg-surface)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "6px",
              padding: "20px",
              position: "sticky",
              top: "20px",
            }}
          >
            {/* Inspector Header */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "12px" }}>
              <div>
                <span
                  style={{
                    fontSize: "11px",
                    fontWeight: 600,
                    textTransform: "uppercase",
                    letterSpacing: "0.05em",
                    color: "var(--text-muted)",
                    display: "block",
                    marginBottom: "4px",
                  }}
                >
                  Decision Inspector
                </span>
                <h3 style={{ fontSize: "16px", fontWeight: 700, color: "var(--text-main)" }}>
                  {selectedDecision.title}
                </h3>
              </div>
              <span
                className={`badge ${
                  selectedDecision.status === "active"
                    ? "badge-active"
                    : selectedDecision.status === "replaced"
                    ? "badge-replaced"
                    : "badge-proposed"
                }`}
              >
                {selectedDecision.status}
              </span>
            </div>

            <p style={{ color: "var(--text-secondary)", fontSize: "13px", marginBottom: "16px" }}>
              {selectedDecision.description}
            </p>

            {/* Architectural Rationale & Causal Justification */}
            <div
              style={{
                background: "var(--bg-app)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "4px",
                padding: "12px",
                marginBottom: "16px",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                <span style={{ fontSize: "11px", fontWeight: 600, color: "var(--color-primary)", textTransform: "uppercase" }}>
                  Extracted Causal Rationale
                </span>
                <span
                  className="font-mono"
                  style={{
                    fontSize: "11px",
                    color:
                      selectedDecision.reason_source_type === "EXPLICIT"
                        ? "var(--color-human)"
                        : "var(--color-ai-inferred)",
                  }}
                >
                  {selectedDecision.reason_source_type}{" "}
                  {selectedDecision.reason_confidence
                    ? `(${(selectedDecision.reason_confidence * 100).toFixed(0)}% conf)`
                    : ""}
                </span>
              </div>
              <p style={{ fontSize: "12px", color: "var(--text-main)", fontStyle: "italic", lineHeight: 1.5 }}>
                "{selectedDecision.reason_text || "No rationale provided in transcript."}"
              </p>
            </div>

            {/* Evaluated Alternatives Sub-Tree */}
            <div style={{ marginBottom: "16px" }}>
              <span
                style={{
                  display: "block",
                  fontSize: "11px",
                  fontWeight: 600,
                  color: "var(--text-muted)",
                  textTransform: "uppercase",
                  marginBottom: "8px",
                }}
              >
                Evaluated Alternatives & Trade-Offs
              </span>

              {selectedDecision.alternatives && selectedDecision.alternatives.length > 0 ? (
                <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  {selectedDecision.alternatives.map((alt, idx) => {
                    const isSelected = alt.selection_status === "selected";
                    return (
                      <div
                        key={idx}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          padding: "8px 12px",
                          borderRadius: "4px",
                          background: isSelected ? "rgba(16, 185, 129, 0.08)" : "var(--bg-app)",
                          border: `1px solid ${
                            isSelected ? "rgba(16, 185, 129, 0.25)" : "var(--border-subtle)"
                          }`,
                        }}
                      >
                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          {isSelected ? (
                            <CheckCircle2 size={14} color="#34d399" />
                          ) : (
                            <XCircle size={14} color="#f87171" />
                          )}
                          <span
                            style={{
                              fontSize: "12px",
                              fontWeight: isSelected ? 600 : 400,
                              color: isSelected ? "#34d399" : "var(--text-secondary)",
                              textDecoration: !isSelected ? "line-through" : "none",
                            }}
                          >
                            {alt.description}
                          </span>
                        </div>
                        <span
                          className="font-mono"
                          style={{
                            fontSize: "10px",
                            textTransform: "uppercase",
                            color: isSelected ? "#34d399" : "#f87171",
                          }}
                        >
                          {alt.selection_status}
                        </span>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div style={{ fontSize: "12px", color: "var(--text-muted)", fontStyle: "italic" }}>
                  No alternate options recorded for this decision.
                </div>
              )}
            </div>

            {/* Relational Metadata & Invariants */}
            <div
              style={{
                borderTop: "1px solid var(--border-subtle)",
                paddingTop: "12px",
                display: "flex",
                flexDirection: "column",
                gap: "6px",
                fontSize: "11px",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--text-muted)" }}>Decision ID</span>
                <span className="font-mono" style={{ color: "var(--text-secondary)" }}>
                  {selectedDecision.decision_id.slice(0, 16)}...
                </span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--text-muted)" }}>Decided At</span>
                <span className="font-mono" style={{ color: "var(--text-secondary)" }}>
                  {selectedDecision.decided_at
                    ? new Date(selectedDecision.decided_at).toLocaleString()
                    : "Not finalized"}
                </span>
              </div>
              {selectedDecision.replaced_by_decision_id && (
                <div style={{ display: "flex", justifyContent: "space-between", color: "var(--color-ai-inferred)" }}>
                  <span>Superseded By</span>
                  <span className="font-mono">
                    {selectedDecision.replaced_by_decision_id.slice(0, 16)}...
                  </span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Individual Node Card inside the Decision Graph Canvas
 */
function DecisionNodeCard({ decision, isSelected, onClick, highlightActive = false }) {
  const isReplaced = decision.status === "replaced";
  const isActive = decision.status === "active";
  const isProposed = decision.status === "proposed";

  return (
    <div
      onClick={onClick}
      style={{
        background: isSelected
          ? "var(--bg-surface-elevated)"
          : "var(--bg-surface)",
        border: `1px solid ${
          isSelected
            ? "var(--color-primary)"
            : highlightActive
            ? "rgba(16, 185, 129, 0.4)"
            : "var(--border-subtle)"
        }`,
        borderRadius: "6px",
        padding: "12px 16px",
        cursor: "pointer",
        transition: "all 0.15s ease",
        boxShadow: isSelected ? "0 0 0 1px var(--color-primary)" : "none",
        opacity: isReplaced ? 0.75 : 1,
      }}
    >
      {/* Top Row: Title, Status, and Options Count */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span
            style={{
              fontSize: "14px",
              fontWeight: 600,
              color: isReplaced ? "var(--text-secondary)" : "var(--text-main)",
              textDecoration: isReplaced ? "line-through" : "none",
            }}
          >
            {decision.title}
          </span>
          <span
            className={`badge ${
              isActive ? "badge-active" : isReplaced ? "badge-replaced" : "badge-proposed"
            }`}
          >
            {decision.status}
          </span>
        </div>

        <ChevronRight
          size={14}
          color={isSelected ? "var(--color-primary)" : "var(--text-muted)"}
        />
      </div>

      {/* Description Snippet */}
      <p style={{ color: "var(--text-secondary)", fontSize: "12px", marginBottom: "8px" }}>
        {decision.description}
      </p>

      {/* Evaluated Alternatives Pills Inline */}
      {decision.alternatives && decision.alternatives.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginTop: "8px" }}>
          {decision.alternatives.map((alt, idx) => {
            const isSel = alt.selection_status === "selected";
            return (
              <span
                key={idx}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "4px",
                  fontSize: "10px",
                  fontWeight: 500,
                  padding: "2px 6px",
                  borderRadius: "3px",
                  background: isSel ? "rgba(16, 185, 129, 0.1)" : "rgba(239, 68, 68, 0.08)",
                  color: isSel ? "#34d399" : "#f87171",
                  border: `1px solid ${isSel ? "rgba(16, 185, 129, 0.25)" : "rgba(239, 68, 68, 0.2)"}`,
                }}
              >
                {isSel ? <Check size={10} /> : <span style={{ fontSize: "9px" }}>✕</span>}
                {alt.description}
              </span>
            );
          })}
        </div>
      )}
    </div>
  );
}
