import React, { useState } from "react";
import {
  Sparkles,
  Plus,
  Trash2,
  CheckCircle2,
  XCircle,
  HelpCircle,
  AlertCircle,
  Shield,
  Bot,
  User,
  Quote,
  Cpu,
} from "lucide-react";
import { extractCandidatesFromTurns } from "../api/client";

export function CandidateStudio({ projectId }) {
  const [turns, setTurns] = useState([
    {
      id: 1,
      prompt:
        "how do we secure our website? JWT? or redis session based auth, or mutual TLS?\nok i feel like session based auth is the best here",
      response:
        "Definitely! it has a simpler lifecycle and safer browser storage. creating the files now...",
    },
  ]);
  const [engine, setEngine] = useState("rules"); // "rules" | "llm" | "auto"
  const [extractionResult, setExtractionResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);

  const handleAddTurn = () => {
    setTurns((prev) => [
      ...prev,
      { id: Date.now(), prompt: "", response: "" },
    ]);
  };

  const handleRemoveTurn = (idToRemove) => {
    if (turns.length <= 1) return;
    setTurns((prev) => prev.filter((t) => t.id !== idToRemove));
  };

  const handleUpdateTurn = (id, field, value) => {
    setTurns((prev) =>
      prev.map((t) => (t.id === id ? { ...t, [field]: value } : t))
    );
  };

  const handleExtract = async () => {
    setLoading(true);
    setErrorMessage(null);
    try {
      const cleanTurns = turns.map((t) => ({
        prompt: t.prompt.trim(),
        response: t.response.trim(),
      }));
      const res = await extractCandidatesFromTurns(cleanTurns, engine, projectId);
      setExtractionResult(res);
    } catch (err) {
      setErrorMessage(err.message || "Failed to communicate with NLP extraction endpoint.");
      setExtractionResult(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: "1380px", margin: "0 auto", padding: "24px" }}>
      {/* Header */}
      <div style={{ marginBottom: "24px" }}>
        <h1 style={{ fontSize: "20px", fontWeight: 700, marginBottom: "4px" }}>
          NLP Multi-Turn Candidate Extraction Studio
        </h1>
        <p style={{ color: "var(--text-secondary)", fontSize: "13px" }}>
          Extract architectural choices, evaluated alternatives, and causal rationale across multi-turn developer and AI dialogues.
          Candidate decisions are strictly staged as{" "}
          <span className="font-mono" style={{ color: "var(--color-primary)" }}>
            status='proposed'
          </span>{" "}
          awaiting human developer review.
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: "24px", alignItems: "start" }}>
        {/* Left Column: Multi-Turn Conversation Editor */}
        <div
          style={{
            background: "var(--bg-surface)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "6px",
            padding: "20px",
            display: "flex",
            flexDirection: "column",
            gap: "20px",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h2 style={{ fontSize: "14px", fontWeight: 600 }}>Conversation Transcript Turns ({turns.length})</h2>

            {/* Engine Picker */}
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 600 }}>
                Engine:
              </span>
              <select
                value={engine}
                onChange={(e) => setEngine(e.target.value)}
                style={{
                  background: "var(--bg-app)",
                  border: "1px solid var(--border-subtle)",
                  color: "var(--text-main)",
                  fontSize: "12px",
                  padding: "4px 8px",
                  borderRadius: "4px",
                  cursor: "pointer",
                }}
              >
                <option value="rules">Rules (Deterministic & Fast)</option>
                <option value="llm">Local LLM (Ollama llama3)</option>
                <option value="auto">Auto (LLM with Rules fallback)</option>
              </select>
            </div>
          </div>

          {/* List of Turns */}
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            {turns.map((turn, index) => (
              <div
                key={turn.id}
                style={{
                  background: "var(--bg-app)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "6px",
                  padding: "16px",
                  position: "relative",
                }}
              >
                {/* Turn Header */}
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: "12px",
                    borderBottom: "1px solid var(--border-subtle)",
                    paddingBottom: "8px",
                  }}
                >
                  <span
                    className="font-mono"
                    style={{ fontSize: "11px", fontWeight: 600, color: "var(--color-primary)", textTransform: "uppercase" }}
                  >
                    Turn {index + 1}
                  </span>
                  {turns.length > 1 && (
                    <button
                      onClick={() => handleRemoveTurn(turn.id)}
                      title="Delete Turn"
                      style={{
                        background: "transparent",
                        border: "none",
                        color: "var(--text-muted)",
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                      }}
                    >
                      <Trash2 size={14} />
                    </button>
                  )}
                </div>

                {/* Developer Prompt */}
                <div style={{ marginBottom: "12px" }}>
                  <label
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "6px",
                      fontSize: "11px",
                      fontWeight: 600,
                      color: "var(--text-muted)",
                      textTransform: "uppercase",
                      marginBottom: "6px",
                    }}
                  >
                    <User size={12} /> Developer Prompt
                  </label>
                  <textarea
                    rows={3}
                    value={turn.prompt}
                    onChange={(e) => handleUpdateTurn(turn.id, "prompt", e.target.value)}
                    placeholder="e.g. Which database should we use, PostgreSQL or MongoDB?"
                    className="font-mono"
                    style={{
                      width: "100%",
                      background: "var(--bg-surface)",
                      border: "1px solid var(--border-subtle)",
                      borderRadius: "4px",
                      padding: "8px 10px",
                      color: "var(--text-main)",
                      fontSize: "12px",
                      lineHeight: 1.5,
                      resize: "vertical",
                    }}
                  />
                </div>

                {/* AI Assistant Response */}
                <div>
                  <label
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "6px",
                      fontSize: "11px",
                      fontWeight: 600,
                      color: "var(--text-muted)",
                      textTransform: "uppercase",
                      marginBottom: "6px",
                    }}
                  >
                    <Bot size={12} /> AI Assistant Response
                  </label>
                  <textarea
                    rows={3}
                    value={turn.response}
                    onChange={(e) => handleUpdateTurn(turn.id, "response", e.target.value)}
                    placeholder="e.g. We recommend PostgreSQL because ACID compliance protects checkout transactions..."
                    className="font-mono"
                    style={{
                      width: "100%",
                      background: "var(--bg-surface)",
                      border: "1px solid var(--border-subtle)",
                      borderRadius: "4px",
                      padding: "8px 10px",
                      color: "var(--text-main)",
                      fontSize: "12px",
                      lineHeight: 1.5,
                      resize: "vertical",
                    }}
                  />
                </div>
              </div>
            ))}
          </div>

          {/* Add Turn Button */}
          <button
            onClick={handleAddTurn}
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "6px",
              padding: "8px 14px",
              background: "var(--bg-surface-elevated)",
              border: "1px dashed var(--border-strong)",
              borderRadius: "4px",
              color: "var(--text-secondary)",
              fontSize: "12px",
              fontWeight: 500,
              cursor: "pointer",
            }}
          >
            <Plus size={14} /> Add Conversation Turn
          </button>

          {/* Run Extraction Button */}
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
            {loading ? "Analyzing Conversation..." : "Run Multi-Turn Extraction Pipeline"}
          </button>
        </div>

        {/* Right Column: Proposed Candidate Decisions Output */}
        <div
          style={{
            background: "var(--bg-surface)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "6px",
            padding: "20px",
            display: "flex",
            flexDirection: "column",
            gap: "16px",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h2 style={{ fontSize: "14px", fontWeight: 600 }}>Extracted Decisions</h2>
            {extractionResult && (
              <span className="badge badge-exact">
                Engine: {extractionResult.engine_used} ({extractionResult.candidates.length} found)
              </span>
            )}
          </div>

          {/* Error Alert */}
          {errorMessage && (
            <div
              style={{
                display: "flex",
                gap: "10px",
                background: "rgba(239, 68, 68, 0.1)",
                border: "1px solid rgba(239, 68, 68, 0.3)",
                borderRadius: "4px",
                padding: "12px 14px",
                fontSize: "12px",
                color: "#f87171",
              }}
            >
              <AlertCircle size={16} style={{ flexShrink: 0, marginTop: "2px" }} />
              <div>
                <strong>Extraction Failed:</strong> {errorMessage}
              </div>
            </div>
          )}

          {/* Warnings Banner */}
          {extractionResult && extractionResult.warnings && extractionResult.warnings.length > 0 && (
            <div
              style={{
                background: "rgba(245, 158, 11, 0.1)",
                border: "1px solid rgba(245, 158, 11, 0.3)",
                borderRadius: "4px",
                padding: "10px 14px",
                fontSize: "12px",
                color: "#fbbf24",
              }}
            >
              {extractionResult.warnings.map((w, idx) => (
                <div key={idx}>⚠️ {w}</div>
              ))}
            </div>
          )}

          {/* Extracted Candidates List */}
          {extractionResult ? (
            extractionResult.candidates.length > 0 ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                {extractionResult.candidates.map((cand, cIdx) => (
                  <div
                    key={cIdx}
                    style={{
                      background: "var(--bg-app)",
                      border: "1px solid var(--border-subtle)",
                      borderRadius: "6px",
                      padding: "16px",
                    }}
                  >
                    {/* Header */}
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <span style={{ fontSize: "15px", fontWeight: 700, color: "var(--text-main)" }}>
                          {cand.title}
                        </span>
                        <span className="badge badge-proposed">{cand.status}</span>
                        <span className="badge" style={{ background: "var(--bg-surface-elevated)", color: "var(--text-secondary)" }}>
                          {cand.decision_type}
                        </span>
                      </div>
                      <span className="font-mono" style={{ fontSize: "11px", color: "var(--color-human)" }}>
                        {(cand.confidence * 100).toFixed(0)}% conf
                      </span>
                    </div>

                    <p style={{ color: "var(--text-secondary)", fontSize: "12px", marginBottom: "12px" }}>
                      {cand.description}
                    </p>

                    {/* Extracted Rationale */}
                    <div
                      style={{
                        background: "rgba(99, 102, 241, 0.08)",
                        border: "1px solid rgba(99, 102, 241, 0.2)",
                        borderRadius: "4px",
                        padding: "10px",
                        marginBottom: "12px",
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                        <span style={{ fontSize: "10px", fontWeight: 600, color: "var(--color-primary)", textTransform: "uppercase" }}>
                          Causal Rationale
                        </span>
                        <span
                          className="font-mono"
                          style={{
                            fontSize: "10px",
                            color: cand.reason_source_type === "EXPLICIT" ? "var(--color-human)" : "var(--color-ai-inferred)",
                          }}
                        >
                          {cand.reason_source_type} ({(cand.reason_confidence * 100).toFixed(0)}% conf)
                        </span>
                      </div>
                      <div style={{ fontSize: "12px", fontStyle: "italic", color: "var(--text-main)" }}>
                        "{cand.reason_text || "No explicit justification identified in transcript."}"
                      </div>
                    </div>

                    {/* Alternatives */}
                    {cand.alternatives && cand.alternatives.length > 0 && (
                      <div style={{ marginBottom: "12px" }}>
                        <span style={{ fontSize: "10px", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", display: "block", marginBottom: "6px" }}>
                          Evaluated Alternatives
                        </span>
                        <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                          {cand.alternatives.map((alt, aIdx) => {
                            const isSel = alt.selection_status === "selected";
                            const isRej = alt.selection_status === "rejected";
                            return (
                              <span
                                key={aIdx}
                                style={{
                                  display: "inline-flex",
                                  alignItems: "center",
                                  gap: "5px",
                                  padding: "3px 8px",
                                  borderRadius: "4px",
                                  fontSize: "11px",
                                  fontWeight: 500,
                                  background: isSel
                                    ? "rgba(16, 185, 129, 0.1)"
                                    : isRej
                                    ? "rgba(239, 68, 68, 0.08)"
                                    : "rgba(107, 114, 128, 0.1)",
                                  color: isSel ? "#34d399" : isRej ? "#f87171" : "var(--text-secondary)",
                                  border: `1px solid ${
                                    isSel
                                      ? "rgba(16, 185, 129, 0.25)"
                                      : isRej
                                      ? "rgba(239, 68, 68, 0.2)"
                                      : "var(--border-subtle)"
                                  }`,
                                  textDecoration: isRej ? "line-through" : "none",
                                }}
                              >
                                {isSel ? <CheckCircle2 size={12} /> : isRej ? <XCircle size={12} /> : <HelpCircle size={12} />}
                                {alt.description}
                              </span>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    {/* Verbatim Evidence Trail */}
                    {cand.evidence && cand.evidence.length > 0 && (
                      <div style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: "10px" }}>
                        <span style={{ fontSize: "10px", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", display: "block", marginBottom: "6px" }}>
                          Cited Transcript Evidence ({cand.evidence.length})
                        </span>
                        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                          {cand.evidence.map((ev, eIdx) => (
                            <div
                              key={eIdx}
                              style={{
                                display: "flex",
                                alignItems: "baseline",
                                gap: "6px",
                                fontSize: "11px",
                                color: "var(--text-secondary)",
                              }}
                            >
                              <span
                                className="font-mono"
                                style={{
                                  fontSize: "9px",
                                  textTransform: "uppercase",
                                  color: "var(--color-primary)",
                                  background: "var(--bg-surface)",
                                  padding: "1px 4px",
                                  borderRadius: "2px",
                                }}
                              >
                                {ev.role}
                              </span>
                              <span style={{ fontStyle: "italic", flex: 1 }}>"{ev.quote}"</span>
                              <span className="font-mono" style={{ fontSize: "10px", color: "var(--text-muted)", whiteSpace: "nowrap" }}>
                                Turn {ev.turn} · {ev.speaker}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ padding: "40px", textAlign: "center", color: "var(--text-muted)" }}>
                No engineering decisions detected in this transcript. (Casual questions and syntax debugging queries correctly yield 0 candidates).
              </div>
            )
          ) : (
            <div style={{ padding: "40px", textAlign: "center", color: "var(--text-muted)" }}>
              Click "Run Multi-Turn Extraction Pipeline" to extract decisions and evidence from the conversation on the left.
            </div>
          )}

          {/* DBMS Invariant Note */}
          <div
            style={{
              display: "flex",
              gap: "10px",
              background: "rgba(245, 158, 11, 0.08)",
              border: "1px solid rgba(245, 158, 11, 0.25)",
              borderRadius: "4px",
              padding: "10px 14px",
              fontSize: "12px",
              color: "#fbbf24",
              marginTop: "auto",
            }}
          >
            <AlertCircle size={16} style={{ flexShrink: 0, marginTop: "2px" }} />
            <span>
              <strong>DBMS Integrity Invariant:</strong> Proposed candidate records require developer approval before insertion into authoritative DECISION table.
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
