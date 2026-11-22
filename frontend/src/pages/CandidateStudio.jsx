import React, { useState } from "react";
import { Sparkles, ArrowRight, CheckCircle2, XCircle, Shield, AlertCircle } from "lucide-react";
import { extractCandidateFromText } from "../api/client";

export function CandidateStudio({ projectId }) {
  const [prompt, setPrompt] = useState(
    "We previously evaluated several database options:\n- PostgreSQL\n- MySQL\n- SQLite\n- MongoDB\n\nok let's use sqlite since it's a simple db"
  );
  const [response, setResponse] = useState(
    "Understood. Configuring SQLite as the embedded relational engine with SQLAlchemy."
  );
  const [candidate, setCandidate] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleExtract = async () => {
    setLoading(true);
    try {
      const res = await extractCandidateFromText(prompt, response, projectId);
      setCandidate(res);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: "1200px", margin: "0 auto", padding: "24px" }}>
      {/* Header */}
      <div style={{ marginBottom: "20px" }}>
        <h1 style={{ fontSize: "20px", fontWeight: 700, marginBottom: "4px" }}>
          NLP Candidate Extraction Studio
        </h1>
        <p style={{ color: "var(--text-secondary)", fontSize: "13px" }}>
          Test the rule-based NLP extraction pipeline on raw developer & AI conversation transcripts.
          Candidate decisions are strictly staged as <span className="font-mono" style={{ color: "var(--color-primary)" }}>status='proposed'</span> awaiting developer approval.
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.1fr 1fr", gap: "24px" }}>
        {/* Left: Input Transcripts */}
        <div style={{
          background: "var(--bg-surface)",
          border: "1px solid var(--border-subtle)",
          borderRadius: "6px",
          padding: "20px",
        }}>
          <h2 style={{ fontSize: "14px", fontWeight: 600, marginBottom: "12px" }}>Conversation Transcript Inputs</h2>

          {/* Prompt */}
          <div style={{ marginBottom: "16px" }}>
            <label style={{ display: "block", fontSize: "11px", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: "6px" }}>
              Developer Prompt / Preamble
            </label>
            <textarea
              rows={6}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              className="font-mono"
              style={{
                width: "100%",
                background: "var(--bg-app)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "4px",
                padding: "10px",
                color: "var(--text-main)",
                fontSize: "12px",
                lineHeight: 1.5,
                resize: "vertical",
              }}
            />
          </div>

          {/* AI Response */}
          <div style={{ marginBottom: "20px" }}>
            <label style={{ display: "block", fontSize: "11px", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: "6px" }}>
              AI Assistant Response
            </label>
            <textarea
              rows={4}
              value={response}
              onChange={(e) => setResponse(e.target.value)}
              className="font-mono"
              style={{
                width: "100%",
                background: "var(--bg-app)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "4px",
                padding: "10px",
                color: "var(--text-main)",
                fontSize: "12px",
                lineHeight: 1.5,
                resize: "vertical",
              }}
            />
          </div>

          {/* Extract Button */}
          <button
            onClick={handleExtract}
            disabled={loading}
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "8px",
              width: "100%",
              padding: "10px 16px",
              background: "var(--color-primary)",
              color: "#fff",
              border: "none",
              borderRadius: "4px",
              fontWeight: 600,
              fontSize: "13px",
              cursor: "pointer",
            }}
          >
            <Sparkles size={16} />
            {loading ? "Analyzing Transcript..." : "Run NLP Extraction Pipeline"}
          </button>
        </div>

        {/* Right: Extracted Candidate Proposal */}
        <div style={{
          background: "var(--bg-surface)",
          border: "1px solid var(--border-subtle)",
          borderRadius: "6px",
          padding: "20px",
        }}>
          <h2 style={{ fontSize: "14px", fontWeight: 600, marginBottom: "12px" }}>Proposed Candidate Decision (DBMS Schema)</h2>

          {candidate ? (
            <div>
              <div style={{
                background: "var(--bg-app)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "6px",
                padding: "16px",
                marginBottom: "16px",
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "6px" }}>
                  <span style={{ fontSize: "16px", fontWeight: 600, color: "var(--text-main)" }}>
                    {candidate.title}
                  </span>
                  <span className="badge badge-proposed">
                    {candidate.status}
                  </span>
                  <span className="badge" style={{ background: "var(--bg-surface-elevated)", color: "var(--text-secondary)" }}>
                    {candidate.decision_type}
                  </span>
                </div>

                <p style={{ color: "var(--text-secondary)", fontSize: "13px", marginBottom: "12px" }}>
                  {candidate.description}
                </p>

                {/* Extracted Rationale */}
                <div style={{ background: "rgba(99, 102, 241, 0.08)", border: "1px solid rgba(99, 102, 241, 0.2)", borderRadius: "4px", padding: "10px", marginBottom: "12px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                    <span style={{ fontSize: "11px", fontWeight: 600, color: "var(--color-primary)", textTransform: "uppercase" }}>
                      Extracted Causal Rationale
                    </span>
                    <span className="font-mono" style={{ fontSize: "11px", color: "var(--color-human)" }}>
                      {candidate.reason_source_type} ({(candidate.reason_confidence * 100).toFixed(0)}% conf)
                    </span>
                  </div>
                  <div style={{ fontSize: "12px", fontStyle: "italic" }}>
                    "{candidate.reason_text}"
                  </div>
                </div>

                {/* Alternatives */}
                <div>
                  <span style={{ fontSize: "11px", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", display: "block", marginBottom: "6px" }}>
                    Candidate Alternatives Resolved
                  </span>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                    {candidate.alternatives.map((alt, idx) => (
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
                          background: alt.selection_status === "selected" ? "rgba(16, 185, 129, 0.1)" : "rgba(239, 68, 68, 0.08)",
                          color: alt.selection_status === "selected" ? "#34d399" : "#f87171",
                          border: `1px solid ${alt.selection_status === "selected" ? "rgba(16, 185, 129, 0.25)" : "rgba(239, 68, 68, 0.2)"}`,
                        }}
                      >
                        {alt.selection_status === "selected" ? <CheckCircle2 size={12} /> : <XCircle size={12} />}
                        {alt.description}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Invariant Alert */}
              <div style={{
                display: "flex",
                gap: "10px",
                background: "rgba(245, 158, 11, 0.08)",
                border: "1px solid rgba(245, 158, 11, 0.25)",
                borderRadius: "4px",
                padding: "10px 14px",
                fontSize: "12px",
                color: "#fbbf24",
              }}>
                <AlertCircle size={16} style={{ flexShrink: 0, marginTop: "2px" }} />
                <span>
                  <strong>DBMS Integrity Invariant:</strong> Proposed candidate records require developer approval before insertion into authoritative DECISION table.
                </span>
              </div>
            </div>
          ) : (
            <div style={{ padding: "40px", textAlign: "center", color: "var(--text-muted)" }}>
              Click "Run NLP Extraction Pipeline" to extract structured candidate decisions from the text above.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
