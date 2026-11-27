import React, { useState } from "react";
import { GitCommit, FileCode2 } from "lucide-react";
import { fetchProvenance, linkDecisionToChange } from "../../api/client";
import { OriginBadge, SectionEmpty, SectionError, SectionLoading, fmtDateTime, statusColor } from "./shared";

export function ProvenanceInspector({
  commits,
  codeChanges,
  decisions,
  commitsLoading,
  commitsError,
  changesLoading,
  changesError,
  onChangeLinked,
}) {
  const [selectedCommit, setSelectedCommit] = useState(null);
  const [selectedChange, setSelectedChange] = useState(null);
  const [provenance, setProvenance] = useState(null);
  const [provLoading, setProvLoading] = useState(false);
  const [provError, setProvError] = useState(null);
  const [linkDecision, setLinkDecision] = useState("");
  const [confirmOverwrite, setConfirmOverwrite] = useState(false);
  const [linking, setLinking] = useState(false);
  const [linkMsg, setLinkMsg] = useState(null);

  // Only offer active decisions from the current project
  const activeDecisions = decisions.filter((d) => d.status === "active");

  const commitChanges = selectedCommit
    ? codeChanges.filter(
        (c) =>
          c.commit?.commit_id === selectedCommit.commit_id ||
          c.commit?.commit_hash === selectedCommit.commit_hash
      )
    : [];

  const handleSelectChange = async (change) => {
    setSelectedChange(change);
    setProvenance(null);
    setProvError(null);
    setLinkDecision(change.decision?.decision_id || "");
    setConfirmOverwrite(false);
    setLinkMsg(null);
    setProvLoading(true);
    try {
      const p = await fetchProvenance(change.change_id);
      setProvenance(p);
      setLinkDecision(p.decision?.decision_id || "");
    } catch (err) {
      setProvError(err.message || "Failed to load provenance.");
    } finally {
      setProvLoading(false);
    }
  };

  const existingDecisionId = provenance?.decision?.decision_id || "";
  const isOverwritingExisting =
    Boolean(existingDecisionId) && linkDecision !== existingDecisionId;

  const handleLink = async () => {
    if (!selectedChange) return;
    if (isOverwritingExisting && !confirmOverwrite) {
      setConfirmOverwrite(true);
      return;
    }
    setLinking(true);
    setLinkMsg(null);
    try {
      const updated = await linkDecisionToChange(selectedChange.change_id, linkDecision || null);
      setProvenance(updated);
      setConfirmOverwrite(false);
      setLinkMsg({ ok: true, text: "Decision link saved." });
      if (onChangeLinked) onChangeLinked(updated);
    } catch (err) {
      setLinkMsg({ ok: false, text: err.message || "Failed to update decision link." });
    } finally {
      setLinking(false);
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
      {/* Left: Commits -> File Changes */}
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
              display: "flex",
              alignItems: "center",
              gap: "6px",
            }}
          >
            <GitCommit size={13} />
            Commits ({commits.length})
          </h3>
          {commitsLoading ? (
            <SectionLoading label="Loading commits…" />
          ) : commitsError ? (
            <SectionError message={commitsError} />
          ) : commits.length === 0 ? (
            <SectionEmpty label="No commits found." />
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "2px", maxHeight: "280px", overflowY: "auto" }}>
              {commits.map((c) => (
                <button
                  key={c.commit_id}
                  type="button"
                  onClick={() => {
                    setSelectedCommit(c);
                    setSelectedChange(null);
                    setProvenance(null);
                    setLinkMsg(null);
                    setConfirmOverwrite(false);
                  }}
                  style={{
                    textAlign: "left",
                    padding: "7px 10px",
                    borderRadius: "4px",
                    border: "1px solid transparent",
                    background: selectedCommit?.commit_id === c.commit_id ? "rgba(99,102,241,0.1)" : "transparent",
                    borderColor: selectedCommit?.commit_id === c.commit_id ? "rgba(99,102,241,0.3)" : "transparent",
                    cursor: "pointer",
                    color: "var(--text-main)",
                  }}
                >
                  <div style={{ fontSize: "12px", fontFamily: "monospace", color: "var(--text-muted)" }}>
                    {c.commit_hash?.slice(0, 7)}
                  </div>
                  <div style={{ fontSize: "13px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {c.message}
                  </div>
                  <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>{fmtDateTime(c.commit_time)}</div>
                </button>
              ))}
            </div>
          )}
        </section>

        {selectedCommit && (
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
              <FileCode2 size={13} />
              File Changes — {selectedCommit.commit_hash?.slice(0, 7)}
            </h3>
            {changesLoading ? (
              <SectionLoading label="Loading file changes…" />
            ) : changesError ? (
              <SectionError message={changesError} />
            ) : commitChanges.length === 0 ? (
              <SectionEmpty label="No file changes recorded for this commit." />
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "2px", maxHeight: "240px", overflowY: "auto" }}>
                {commitChanges.map((ch) => (
                  <button
                    key={ch.change_id}
                    type="button"
                    onClick={() => handleSelectChange(ch)}
                    style={{
                      textAlign: "left",
                      padding: "7px 10px",
                      borderRadius: "4px",
                      border: "1px solid transparent",
                      background: selectedChange?.change_id === ch.change_id ? "rgba(99,102,241,0.08)" : "transparent",
                      borderColor: selectedChange?.change_id === ch.change_id ? "rgba(99,102,241,0.25)" : "transparent",
                      cursor: "pointer",
                      color: "var(--text-main)",
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                      flexWrap: "wrap",
                    }}
                  >
                    <span
                      style={{
                        fontFamily: "monospace",
                        fontSize: "12px",
                        flex: 1,
                        minWidth: "120px",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {ch.file_path}
                    </span>
                    <OriginBadge origin={ch.origin} />
                    <span style={{ fontSize: "11px", color: ch.decision ? "#10b981" : "var(--text-muted)" }}>
                      {ch.decision ? "Decision linked" : "No decision"}
                    </span>
                    {ch.interaction && (
                      <span style={{ fontSize: "11px", color: "#6366f1" }}>AI interaction</span>
                    )}
                  </button>
                ))}
              </div>
            )}
          </section>
        )}
      </div>

      {/* Right: Provenance detail */}
      <section
        style={{
          background: "var(--bg-surface)",
          border: "1px solid var(--border-subtle)",
          borderRadius: "8px",
          padding: "14px 16px",
          minHeight: "220px",
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
          Provenance Detail
        </h3>
        {!selectedChange ? (
          <div style={{ color: "var(--text-muted)", fontSize: "13px" }}>
            Select a commit and a file change to inspect its provenance.
          </div>
        ) : provLoading ? (
          <SectionLoading label="Loading provenance…" />
        ) : provError ? (
          <SectionError message={provError} />
        ) : provenance ? (
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            <div>
              <div style={{ fontFamily: "monospace", fontSize: "13px", fontWeight: 600, wordBreak: "break-all" }}>
                {provenance.file_path}
              </div>
              <div style={{ display: "flex", gap: "8px", marginTop: "6px", flexWrap: "wrap", alignItems: "center" }}>
                <OriginBadge origin={provenance.origin} />
                <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>{provenance.change_type}</span>
                {provenance.lines_added != null && (
                  <span style={{ fontSize: "12px", color: "#10b981" }}>+{provenance.lines_added}</span>
                )}
                {provenance.lines_deleted != null && (
                  <span style={{ fontSize: "12px", color: "#ef4444" }}>−{provenance.lines_deleted}</span>
                )}
                {provenance.confidence != null && (
                  <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                    conf: {(provenance.confidence * 100).toFixed(0)}%
                  </span>
                )}
              </div>
            </div>

            {provenance.commit ? (
              <div style={{ padding: "8px 10px", borderRadius: "5px", background: "var(--bg-app)", border: "1px solid var(--border-subtle)" }}>
                <div style={{ fontSize: "11px", fontWeight: 600, color: "var(--text-muted)", marginBottom: "3px", textTransform: "uppercase", letterSpacing: "0.04em" }}>
                  Commit
                </div>
                <div style={{ fontFamily: "monospace", fontSize: "12px" }}>{provenance.commit.commit_hash?.slice(0, 7)}</div>
                <div style={{ fontSize: "12px", color: "var(--text-secondary)" }}>{provenance.commit.message}</div>
                <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>{fmtDateTime(provenance.commit.commit_time)}</div>
              </div>
            ) : (
              <div style={{ fontSize: "12px", color: "var(--text-muted)", fontStyle: "italic" }}>
                Commit information not available.
              </div>
            )}

            {provenance.interaction ? (
              <div style={{ padding: "8px 10px", borderRadius: "5px", background: "var(--bg-app)", border: "1px solid var(--border-subtle)" }}>
                <div style={{ fontSize: "11px", fontWeight: 600, color: "var(--text-muted)", marginBottom: "3px", textTransform: "uppercase", letterSpacing: "0.04em" }}>
                  AI Interaction
                </div>
                <div style={{ fontSize: "12px" }}>
                  {provenance.interaction.tool_name}
                  {provenance.interaction.model_name ? ` / ${provenance.interaction.model_name}` : ""}
                </div>
                <div
                  style={{
                    fontSize: "12px",
                    color: "var(--text-secondary)",
                    marginTop: "3px",
                    overflow: "hidden",
                    display: "-webkit-box",
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: "vertical",
                  }}
                >
                  {provenance.interaction.prompt}
                </div>
              </div>
            ) : (
              <div style={{ fontSize: "12px", color: "var(--text-muted)", fontStyle: "italic" }}>
                No AI interaction linked.
              </div>
            )}

            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <div style={{ fontSize: "11px", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.04em" }}>
                Engineering Decision
              </div>
              {provenance.decision ? (
                <div style={{ padding: "8px 10px", borderRadius: "5px", background: "var(--bg-app)", border: "1px solid var(--border-subtle)" }}>
                  <div style={{ fontSize: "13px", fontWeight: 600 }}>{provenance.decision.title}</div>
                  <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "2px" }}>
                    {provenance.decision.description}
                  </div>
                  <div style={{ marginTop: "4px" }}>
                    <span style={{ fontSize: "11px", color: statusColor(provenance.decision.status), fontWeight: 600 }}>
                      {provenance.decision.status}
                    </span>
                  </div>
                </div>
              ) : (
                <div style={{ fontSize: "12px", color: "var(--text-muted)", fontStyle: "italic" }}>
                  No linked decision.
                </div>
              )}

              {/* Active-decision linking control */}
              <div style={{ display: "flex", gap: "6px", alignItems: "center", flexWrap: "wrap" }}>
                <select
                  aria-label="Select active decision to link"
                  value={linkDecision}
                  onChange={(e) => {
                    setLinkDecision(e.target.value);
                    setConfirmOverwrite(false);
                    setLinkMsg(null);
                  }}
                  style={{
                    flex: 1,
                    minWidth: "160px",
                    padding: "5px 8px",
                    borderRadius: "4px",
                    border: "1px solid var(--border-subtle)",
                    background: "var(--bg-app)",
                    color: "var(--text-main)",
                    fontSize: "12px",
                  }}
                >
                  <option value="">— No decision —</option>
                  {activeDecisions.map((d) => (
                    <option key={d.decision_id} value={d.decision_id}>
                      {d.title}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={handleLink}
                  disabled={linking || linkDecision === existingDecisionId}
                  style={{
                    padding: "5px 12px",
                    borderRadius: "4px",
                    border: "none",
                    background: confirmOverwrite ? "#f59e0b" : "var(--color-primary)",
                    color: "#fff",
                    fontSize: "12px",
                    fontWeight: 600,
                    cursor: linking || linkDecision === existingDecisionId ? "not-allowed" : "pointer",
                    opacity: linking || linkDecision === existingDecisionId ? 0.6 : 1,
                  }}
                >
                  {linking ? "Saving…" : confirmOverwrite ? "Confirm Replace" : "Link Decision"}
                </button>
              </div>
              {confirmOverwrite && (
                <div style={{ fontSize: "11px", color: "#f59e0b" }}>
                  This change already has a linked decision. Click &ldquo;Confirm Replace&rdquo; to update it.
                </div>
              )}
              {activeDecisions.length === 0 && (
                <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                  No active decisions available to link. Approve a proposed decision in the Review Queue first.
                </div>
              )}
              {linkMsg && (
                <div style={{ fontSize: "12px", color: linkMsg.ok ? "#10b981" : "#f87171" }}>
                  {linkMsg.text}
                </div>
              )}
            </div>
          </div>
        ) : null}
      </section>
    </div>
  );
}
