import React, { useState } from "react";
import { GitCommit, MessageSquare, Shield, Terminal, ArrowRight } from "lucide-react";

export function Provenance({ changes }) {
  const [selectedChange, setSelectedChange] = useState(changes[0] || null);

  return (
    <div style={{ maxWidth: "1200px", margin: "0 auto", padding: "24px" }}>
      {/* Header */}
      <div style={{ marginBottom: "20px" }}>
        <h1 style={{ fontSize: "20px", fontWeight: 700, marginBottom: "4px" }}>
          Line-Level Code Provenance Inspector
        </h1>
        <p style={{ color: "var(--text-secondary)", fontSize: "13px" }}>
          Trace any committed file change back to the exact Git commit, AI prompt, assistant model, and architectural decision.
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1.2fr", gap: "20px", alignItems: "start" }}>
        {/* Left: Code Changes Table */}
        <div style={{
          background: "var(--bg-surface)",
          border: "1px solid var(--border-subtle)",
          borderRadius: "6px",
          overflow: "hidden",
        }}>
          <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--border-subtle)", fontWeight: 600, fontSize: "13px" }}>
            Committed Code Changes
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
                      <span className={`badge ${
                        c.origin === "ai_exact" ? "badge-exact" : c.origin === "ai_inferred" ? "badge-inferred" : "badge-human"
                      }`}>
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
          <div style={{
            background: "var(--bg-surface)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "6px",
            padding: "20px",
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px", paddingBottom: "12px", borderBottom: "1px solid var(--border-subtle)" }}>
              <div>
                <span className="font-mono" style={{ fontSize: "14px", fontWeight: 600, color: "var(--color-primary)" }}>
                  {selectedChange.file_path}
                </span>
                <span className="font-mono" style={{ fontSize: "12px", color: "var(--text-muted)", marginLeft: "8px" }}>
                  (Lines {selectedChange.line_start} to {selectedChange.line_end})
                </span>
              </div>
              <span className={`badge ${
                selectedChange.origin === "ai_exact" ? "badge-exact" : selectedChange.origin === "ai_inferred" ? "badge-inferred" : "badge-human"
              }`}>
                {selectedChange.origin} {selectedChange.confidence ? `(${(selectedChange.confidence * 100).toFixed(0)}%)` : ""}
              </span>
            </div>

            {/* Trace Step 1: Git Commit */}
            <div style={{ marginBottom: "16px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "11px", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: "4px" }}>
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
              <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "11px", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: "4px" }}>
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
              <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "11px", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: "4px" }}>
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
