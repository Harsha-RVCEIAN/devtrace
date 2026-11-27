import React, { useRef, useState } from "react";
import { GitBranch } from "lucide-react";
import { fetchAlternatives, fetchEvidence } from "../../api/client";
import { SectionEmpty, SectionError, SectionLoading, fmtDate, statusColor } from "./shared";
import { ProjectTimeline } from "./ProjectTimeline";

export function DecisionGraphView({
  decisions,
  decisionsLoading,
  decisionsError,
  timeline,
  timelineLoading,
  timelineError,
}) {
  const [selectedDecision, setSelectedDecision] = useState(null);
  const [alts, setAlts] = useState(null);
  const [evidence, setEvidence] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState(null);

  // Cache alternatives and evidence per decision_id
  const cacheRef = useRef({});
  const decById = Object.fromEntries(decisions.map((d) => [d.decision_id, d]));

  const handleSelectDecision = async (d) => {
    setSelectedDecision(d);
    setDetailError(null);

    const cached = cacheRef.current[d.decision_id];
    if (cached) {
      setAlts(cached.alts);
      setEvidence(cached.evidence);
      setDetailLoading(false);
      return;
    }

    setAlts(null);
    setEvidence(null);
    setDetailLoading(true);
    try {
      const [altsRes, evRes] = await Promise.allSettled([
        fetchAlternatives(d.decision_id),
        fetchEvidence(d.decision_id),
      ]);
      const loadedAlts = altsRes.status === "fulfilled" ? altsRes.value : [];
      const loadedEv = evRes.status === "fulfilled" ? evRes.value : [];
      if (altsRes.status === "rejected" && evRes.status === "rejected") {
        setDetailError("Failed to load decision alternatives and evidence.");
      } else {
        cacheRef.current[d.decision_id] = { alts: loadedAlts, evidence: loadedEv };
      }
      setAlts(loadedAlts);
      setEvidence(loadedEv);
    } catch (err) {
      setDetailError(err.message || "Failed to load decision details.");
    } finally {
      setDetailLoading(false);
    }
  };

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 360px), 1fr))",
        gap: "16px",
        alignItems: "start",
      }}
    >
      {/* Left: Decision Graph */}
      <section
        style={{
          background: "var(--bg-surface)",
          border: "1px solid var(--border-subtle)",
          borderRadius: "8px",
          padding: "14px 16px",
        }}
      >
        <h3
          style={{
            fontSize: "12px",
            fontWeight: 600,
            marginBottom: "10px",
            color: "var(--text-secondary)",
            textTransform: "uppercase",
            letterSpacing: "0.05em",
            display: "flex",
            alignItems: "center",
            gap: "6px",
          }}
        >
          <GitBranch size={13} />
          Decision Graph ({decisions.length})
        </h3>
        {decisionsLoading ? (
          <SectionLoading label="Loading decisions…" />
        ) : decisionsError ? (
          <SectionError message={decisionsError} />
        ) : decisions.length === 0 ? (
          <SectionEmpty label="No decisions recorded yet." />
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "4px", maxHeight: "420px", overflowY: "auto" }}>
            {decisions.map((d) => {
              const replacer = d.replaced_by_decision_id ? decById[d.replaced_by_decision_id] : null;
              return (
                <button
                  key={d.decision_id}
                  type="button"
                  onClick={() => handleSelectDecision(d)}
                  style={{
                    textAlign: "left",
                    padding: "8px 10px",
                    borderRadius: "4px",
                    border: "1px solid transparent",
                    background: selectedDecision?.decision_id === d.decision_id ? "rgba(99,102,241,0.1)" : "transparent",
                    borderColor: selectedDecision?.decision_id === d.decision_id ? "rgba(99,102,241,0.3)" : "transparent",
                    cursor: "pointer",
                    color: "var(--text-main)",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <span
                      aria-hidden="true"
                      style={{
                        display: "inline-block",
                        width: 8,
                        height: 8,
                        borderRadius: "50%",
                        background: statusColor(d.status),
                        flexShrink: 0,
                      }}
                    />
                    <span
                      style={{
                        fontSize: "13px",
                        fontWeight: 500,
                        flex: 1,
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {d.title}
                    </span>
                    <span style={{ fontSize: "11px", color: statusColor(d.status), fontWeight: 600 }}>
                      {d.status}
                    </span>
                  </div>
                  <div style={{ fontSize: "11px", color: "var(--text-muted)", marginLeft: "16px", marginTop: "2px" }}>
                    {d.decision_type}
                  </div>
                  {replacer && (
                    <div style={{ fontSize: "11px", color: "var(--text-muted)", marginLeft: "16px", marginTop: "2px" }}>
                      → replaced by: <em>{replacer.title}</em>
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        )}
      </section>

      {/* Right: Decision detail + Timeline */}
      <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
        <section
          style={{
            background: "var(--bg-surface)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "8px",
            padding: "14px 16px",
          }}
        >
          <h3
            style={{
              fontSize: "12px",
              fontWeight: 600,
              marginBottom: "10px",
              color: "var(--text-secondary)",
              textTransform: "uppercase",
              letterSpacing: "0.05em",
            }}
          >
            Decision Detail
          </h3>
          {!selectedDecision ? (
            <div style={{ color: "var(--text-muted)", fontSize: "13px" }}>
              Select a decision to inspect its alternatives and evidence.
            </div>
          ) : detailLoading ? (
            <SectionLoading label="Loading decision details…" />
          ) : detailError ? (
            <SectionError message={detailError} />
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              <div>
                <div style={{ fontSize: "15px", fontWeight: 700 }}>{selectedDecision.title}</div>
                <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "4px" }}>
                  {selectedDecision.description}
                </div>
                {selectedDecision.reason_text && (
                  <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "4px", fontStyle: "italic" }}>
                    Rationale: {selectedDecision.reason_text}
                  </div>
                )}
                <div style={{ display: "flex", gap: "8px", marginTop: "6px", flexWrap: "wrap" }}>
                  <span style={{ fontSize: "11px", color: statusColor(selectedDecision.status), fontWeight: 600 }}>
                    {selectedDecision.status}
                  </span>
                  <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                    {selectedDecision.decision_type}
                  </span>
                  {selectedDecision.decided_at && (
                    <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                      {fmtDate(selectedDecision.decided_at)}
                    </span>
                  )}
                </div>
              </div>

              <div>
                <div style={{ fontSize: "11px", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: "5px" }}>
                  Alternatives
                </div>
                {alts && alts.length > 0 ? (
                  <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                    {alts.map((a) => (
                      <div
                        key={a.alternative_id}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "8px",
                          padding: "5px 8px",
                          borderRadius: "4px",
                          background: "var(--bg-app)",
                          border: "1px solid var(--border-subtle)",
                        }}
                      >
                        <span style={{ fontSize: "12px", flex: 1 }}>{a.description}</span>
                        <span
                          style={{
                            fontSize: "11px",
                            color: a.selection_status === "selected" ? "#10b981" : a.selection_status === "rejected" ? "#ef4444" : "var(--text-muted)",
                            fontWeight: 600,
                          }}
                        >
                          {a.selection_status}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={{ fontSize: "12px", color: "var(--text-muted)", fontStyle: "italic" }}>
                    No alternatives available.
                  </div>
                )}
              </div>

              <div>
                <div style={{ fontSize: "11px", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: "5px" }}>
                  Evidence
                </div>
                {evidence && evidence.length > 0 ? (
                  <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                    {evidence.map((e) => (
                      <div
                        key={e.evidence_id}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "8px",
                          padding: "5px 8px",
                          borderRadius: "4px",
                          background: "var(--bg-app)",
                          border: "1px solid var(--border-subtle)",
                        }}
                      >
                        <span style={{ fontSize: "11px", color: "var(--text-muted)", fontWeight: 600 }}>
                          {e.evidence_type}
                        </span>
                        <span
                          style={{
                            fontSize: "12px",
                            flex: 1,
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                          }}
                        >
                          {e.source_reference}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={{ fontSize: "12px", color: "var(--text-muted)", fontStyle: "italic" }}>
                    No evidence available.
                  </div>
                )}
              </div>
            </div>
          )}
        </section>

        <section
          style={{
            background: "var(--bg-surface)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "8px",
            padding: "14px 16px",
          }}
        >
          <h3
            style={{
              fontSize: "12px",
              fontWeight: 600,
              marginBottom: "10px",
              color: "var(--text-secondary)",
              textTransform: "uppercase",
              letterSpacing: "0.05em",
            }}
          >
            Project Timeline
          </h3>
          <ProjectTimeline
            timeline={timeline}
            loading={timelineLoading}
            error={timelineError}
            maxItems={30}
            maxHeight="260px"
          />
        </section>
      </div>
    </div>
  );
}
