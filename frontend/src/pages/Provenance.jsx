import React, { useState } from "react";
import { GitCommit, MessageSquare, Shield, Terminal, ArrowRight, FileCode, CheckCircle2 } from "lucide-react";

export function Provenance({ changes = [] }) {
  const [selectedChange, setSelectedChange] = useState(changes[0] || null);

  return (
    <div style={{ maxWidth: "1280px", margin: "0 auto", padding: "24px" }}>
      {/* Header */}
      <div style={{ marginBottom: "20px" }}>
        <h1 style={{ fontSize: "20px", fontWeight: 700, marginBottom: "4px" }}>
          Line-Level Code Provenance & Lineage Map
        </h1>
        <p style={{ color: "var(--text-secondary)", fontSize: "13px" }}>
          Trace any committed file change back to the exact Git commit, AI prompt, assistant model, and architectural decision.
        </p>
      </div>

      {/* Visual Lineage Pipeline Map (Breadcrumb Ribbon) */}
      {selectedChange && (
        <div
          style={{
            background: "var(--bg-surface)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "6px",
            padding: "16px 20px",
            marginBottom: "20px",
            display: "flex",
            alignItems: "center",
            gap: "12px",
            overflowX: "auto",
          }}
        >
          {/* Node 1: Decision */}
          <div
            style={{
              flex: 1,
              minWidth: "200px",
              background: "var(--bg-app)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "4px",
              padding: "10px 14px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "4px" }}>
              <Shield size={13} color="var(--color-human)" />
              <span style={{ fontSize: "10px", fontWeight: 600, textTransform: "uppercase", color: "var(--text-muted)" }}>
                Architectural Decision
              </span>
            </div>
            <div style={{ fontSize: "12px", fontWeight: 600, color: selectedChange.decision_title ? "var(--text-main)" : "var(--color-danger)" }}>
              {selectedChange.decision_title || "Unattributed"}
            </div>
          </div>

          <ArrowRight size={16} color="var(--border-strong)" style={{ flexShrink: 0 }} />

          {/* Node 2: AI Interaction */}
          <div
            style={{
              flex: 1,
              minWidth: "200px",
              background: "var(--bg-app)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "4px",
              padding: "10px 14px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "4px" }}>
              <MessageSquare size={13} color="var(--color-primary)" />
              <span style={{ fontSize: "10px", fontWeight: 600, textTransform: "uppercase", color: "var(--text-muted)" }}>
                Generating AI Session
              </span>
            </div>
            <div style={{ fontSize: "12px", fontWeight: 500, color: "var(--text-main)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {selectedChange.tool_name ? `${selectedChange.tool_name}: "${selectedChange.prompt_snippet}"` : "Human Author (Direct commit)"}
            </div>
          </div>

          <ArrowRight size={16} color="var(--border-strong)" style={{ flexShrink: 0 }} />

          {/* Node 3: Git Commit */}
          <div
            style={{
              flex: 1,
              minWidth: "200px",
              background: "var(--bg-app)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "4px",
              padding: "10px 14px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "4px" }}>
              <GitCommit size={13} color="var(--color-ai-exact)" />
              <span style={{ fontSize: "10px", fontWeight: 600, textTransform: "uppercase", color: "var(--text-muted)" }}>
                Git Commit
              </span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span className="font-mono" style={{ fontSize: "11px", color: "var(--color-ai-exact)" }}>
                {selectedChange.commit_hash}
              </span>
              <span style={{ fontSize: "12px", color: "var(--text-secondary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {selectedChange.commit_message}
              </span>
            </div>
          </div>

          <ArrowRight size={16} color="var(--border-strong)" style={{ flexShrink: 0 }} />

          {/* Node 4: File Diff Lines */}
          <div
            style={{
              flex: 1,
              minWidth: "200px",
              background: "var(--bg-app)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "4px",
              padding: "10px 14px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "4px" }}>
              <FileCode size={13} color="#34d399" />
              <span style={{ fontSize: "10px", fontWeight: 600, textTransform: "uppercase", color: "var(--text-muted)" }}>
                Changed File Lines
              </span>
            </div>
            <div className="font-mono" style={{ fontSize: "12px", color: "#34d399" }}>
              {selectedChange.file_path} (L{selectedChange.line_start}-{selectedChange.line_end})
            </div>
          </div>
        </div>
      )}

      {/* Main Grid: Code Changes Table & Deep-Dive Provenance Graph Inspector */}
      <div style={{ display: "grid", gridTemplateColumns: "1.1fr 1fr", gap: "20px", alignItems: "start" }}>
        {/* Left: Code Changes Table */}
        <div
          style={{
            background: "var(--bg-surface)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "6px",
            overflow: "hidden",
          }}
        >
          <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--border-subtle)", fontWeight: 600, fontSize: "13px" }}>
            Committed Code Changes ({changes.length})
          </div>
          <table className="data-table">
            <thead>
              <tr>
                <th>File Path</th>
                <th>Lines</th>
                <th>Origin</th>
                <th>Lines Added</th>
              </tr>
            </thead>
            <tbody>
              {changes.map((c) => {
                const isSelected = selectedChange?.change_id === c.change_id;
                return (
                  <tr
                    key={c.change_id}
                    onClick={() => setSelectedChange(c)}
                    style={{
                      cursor: "pointer",
                      background: isSelected ? "var(--bg-surface-elevated)" : "transparent",
                    }}
                  >
                    <td className="font-mono" style={{ fontSize: "12px", fontWeight: 500 }}>
                      {c.file_path}
                    </td>
                    <td className="font-mono" style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                      L{c.line_start}-{c.line_end}
                    </td>
                    <td>
                      <span
                        className={`badge ${
                          c.origin === "ai_exact"
                            ? "badge-exact"
                            : c.origin === "ai_inferred"
                            ? "badge-inferred"
                            : "badge-human"
                        }`}
                      >
                        {c.origin}
                      </span>
                    </td>
                    <td className="font-mono" style={{ fontSize: "12px", color: "#34d399" }}>
                      +{c.lines_added}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Right: Detailed Provenance Graph Inspector ("Explain this line") */}
        {selectedChange ? (
          <div
            style={{
              background: "var(--bg-surface)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "6px",
              padding: "20px",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: "16px",
                paddingBottom: "12px",
                borderBottom: "1px solid var(--border-subtle)",
              }}
            >
              <div>
                <span className="font-mono" style={{ fontSize: "14px", fontWeight: 600, color: "var(--color-primary)" }}>
                  {selectedChange.file_path}
                </span>
                <span className="font-mono" style={{ fontSize: "12px", color: "var(--text-muted)", marginLeft: "8px" }}>
                  (Lines {selectedChange.line_start} to {selectedChange.line_end})
                </span>
              </div>
              <span
                className={`badge ${
                  selectedChange.origin === "ai_exact"
                    ? "badge-exact"
                    : selectedChange.origin === "ai_inferred"
                    ? "badge-inferred"
                    : "badge-human"
                }`}
              >
                {selectedChange.origin}{" "}
                {selectedChange.confidence ? `(${(selectedChange.confidence * 100).toFixed(0)}%)` : ""}
              </span>
            </div>

            {/* Trace Step 1: Git Commit */}
            <div style={{ marginBottom: "16px" }}>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                  fontSize: "11px",
                  fontWeight: 600,
                  color: "var(--text-muted)",
                  textTransform: "uppercase",
                  marginBottom: "4px",
                }}
              >
                <GitCommit size={12} /> Git Commit
              </div>
              <div style={{ background: "var(--bg-app)", border: "1px solid var(--border-subtle)", borderRadius: "4px", padding: "10px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "2px" }}>
                  <span className="font-mono" style={{ color: "var(--color-ai-exact)", fontSize: "12px" }}>
                    {selectedChange.commit_hash}
                  </span>
                  <span style={{ fontSize: "13px", fontWeight: 500 }}>{selectedChange.commit_message}</span>
                </div>
              </div>
            </div>

            {/* Trace Step 2: AI Interaction & Prompt */}
            <div style={{ marginBottom: "16px" }}>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                  fontSize: "11px",
                  fontWeight: 600,
                  color: "var(--text-muted)",
                  textTransform: "uppercase",
                  marginBottom: "4px",
                }}
              >
                <MessageSquare size={12} /> Generating AI Interaction
              </div>
              <div style={{ background: "var(--bg-app)", border: "1px solid var(--border-subtle)", borderRadius: "4px", padding: "10px" }}>
                {selectedChange.prompt_snippet ? (
                  <>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                      <span className="badge" style={{ background: "rgba(129, 140, 248, 0.15)", color: "#818cf8" }}>
                        {selectedChange.tool_name}
                      </span>
                    </div>
                    <p style={{ fontSize: "12px", color: "var(--text-main)", fontStyle: "italic" }}>
                      "{selectedChange.prompt_snippet}"
                    </p>
                  </>
                ) : (
                  <span style={{ fontSize: "12px", color: "var(--color-human)" }}>
                    No AI Interaction — Human authored code change.
                  </span>
                )}
              </div>
            </div>

            {/* Trace Step 3: Linked Engineering Decision */}
            <div>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                  fontSize: "11px",
                  fontWeight: 600,
                  color: "var(--text-muted)",
                  textTransform: "uppercase",
                  marginBottom: "4px",
                }}
              >
                <Shield size={12} /> Implementing Decision
              </div>
              <div style={{ background: "var(--bg-app)", border: "1px solid var(--border-subtle)", borderRadius: "4px", padding: "10px" }}>
                {selectedChange.decision_title ? (
                  <span style={{ fontSize: "13px", fontWeight: 600, color: "#34d399" }}>
                    {selectedChange.decision_title}
                  </span>
                ) : (
                  <span style={{ fontSize: "12px", color: "var(--color-danger)" }}>
                    Unattributed — No linked decision recorded.
                  </span>
                )}
              </div>
            </div>
          </div>
        ) : (
          <div style={{ padding: "40px", color: "var(--text-muted)", textAlign: "center" }}>
            Select a code change to inspect its relational provenance chain.
          </div>
        )}
      </div>
    </div>
  );
}
