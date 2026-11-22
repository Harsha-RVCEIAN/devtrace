import React from "react";
import { Database, GitCommit, Shield, Cpu, AlertTriangle, CheckCircle2 } from "lucide-react";
import { DecisionCard } from "../components/DecisionCard";

export function Dashboard({ project, summary, decisions }) {
  const total = summary.total_changes || 1;
  const aiRatio = (((summary.ai_exact_changes + summary.ai_inferred_changes) / total) * 100).toFixed(0);

  return (
    <div style={{ maxWidth: "1200px", margin: "0 auto", padding: "24px" }}>
      {/* Project Banner */}
      <div style={{
        background: "var(--bg-surface)",
        border: "1px solid var(--border-subtle)",
        borderRadius: "8px",
        padding: "20px 24px",
        marginBottom: "24px",
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <h1 style={{ fontSize: "20px", fontWeight: 700, marginBottom: "4px" }}>
              {project?.project_name || "CampusCart"}
            </h1>
            <p style={{ color: "var(--text-secondary)", fontSize: "13px", maxWidth: "700px" }}>
              {project?.description}
            </p>
          </div>
          <a
            href={project?.repository_url}
            target="_blank"
            rel="noreferrer"
            className="font-mono"
            style={{ fontSize: "12px", color: "var(--color-primary)", textDecoration: "none" }}
          >
            {project?.repository_url}
          </a>
        </div>
      </div>

      {/* Relational Metric Cards */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
        gap: "16px",
        marginBottom: "24px",
      }}>
        {/* Total Changes */}
        <div style={{ background: "var(--bg-surface)", border: "1px solid var(--border-subtle)", borderRadius: "6px", padding: "16px" }}>
          <span style={{ fontSize: "11px", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase" }}>Total Code Changes</span>
          <div style={{ fontSize: "28px", fontWeight: 700, marginTop: "4px" }}>{summary.total_changes}</div>
          <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>Across all project commits</span>
        </div>

        {/* AI Exact */}
        <div style={{ background: "var(--bg-surface)", border: "1px solid var(--border-subtle)", borderRadius: "6px", padding: "16px" }}>
          <span style={{ fontSize: "11px", fontWeight: 600, color: "var(--color-ai-exact)", textTransform: "uppercase" }}>AI Exact Changes</span>
          <div style={{ fontSize: "28px", fontWeight: 700, marginTop: "4px", color: "var(--color-ai-exact)" }}>{summary.ai_exact_changes}</div>
          <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>Verified IDE telemetry</span>
        </div>

        {/* AI Inferred */}
        <div style={{ background: "var(--bg-surface)", border: "1px solid var(--border-subtle)", borderRadius: "6px", padding: "16px" }}>
          <span style={{ fontSize: "11px", fontWeight: 600, color: "var(--color-ai-inferred)", textTransform: "uppercase" }}>AI Inferred Changes</span>
          <div style={{ fontSize: "28px", fontWeight: 700, marginTop: "4px", color: "var(--color-ai-inferred)" }}>{summary.ai_inferred_changes}</div>
          <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>Diff heuristic overlap (&ge;40%)</span>
        </div>

        {/* Human Authored */}
        <div style={{ background: "var(--bg-surface)", border: "1px solid var(--border-subtle)", borderRadius: "6px", padding: "16px" }}>
          <span style={{ fontSize: "11px", fontWeight: 600, color: "var(--color-human)", textTransform: "uppercase" }}>Human Authored</span>
          <div style={{ fontSize: "28px", fontWeight: 700, marginTop: "4px", color: "var(--color-human)" }}>{summary.human_changes}</div>
          <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>Developer direct commits</span>
        </div>

        {/* Missing Provenance (Alert) */}
        <div style={{ background: "var(--bg-surface)", border: "1px solid rgba(239, 68, 68, 0.3)", borderRadius: "6px", padding: "16px" }}>
          <span style={{ fontSize: "11px", fontWeight: 600, color: "var(--color-danger)", textTransform: "uppercase" }}>Unattributed Changes</span>
          <div style={{ fontSize: "28px", fontWeight: 700, marginTop: "4px", color: "var(--color-danger)" }}>{summary.missing_provenance}</div>
          <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>No AI or Decision link</span>
        </div>
      </div>

      {/* Provenance Distribution Bar */}
      <div style={{
        background: "var(--bg-surface)",
        border: "1px solid var(--border-subtle)",
        borderRadius: "6px",
        padding: "18px 20px",
        marginBottom: "24px",
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
          <span style={{ fontWeight: 600, fontSize: "13px" }}>Codebase Provenance Distribution</span>
          <span className="font-mono" style={{ fontSize: "12px", color: "var(--color-ai-exact)" }}>
            {aiRatio}% AI-Assisted / {100 - aiRatio}% Human
          </span>
        </div>

        {/* Multi-segment Progress Bar */}
        <div style={{ width: "100%", height: "10px", background: "var(--bg-app)", borderRadius: "5px", overflow: "hidden", display: "flex" }}>
          <div style={{ width: `${(summary.ai_exact_changes / total) * 100}%`, background: "var(--color-ai-exact)" }} title="ai_exact" />
          <div style={{ width: `${(summary.ai_inferred_changes / total) * 100}%`, background: "var(--color-ai-inferred)" }} title="ai_inferred" />
          <div style={{ width: `${(summary.human_changes / total) * 100}%`, background: "var(--color-human)" }} title="human" />
        </div>

        <div style={{ display: "flex", gap: "20px", marginTop: "12px", fontSize: "11px", color: "var(--text-muted)" }}>
          <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span style={{ width: "8px", height: "8px", borderRadius: "2px", background: "var(--color-ai-exact)" }} /> ai_exact ({summary.ai_exact_changes})
          </span>
          <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span style={{ width: "8px", height: "8px", borderRadius: "2px", background: "var(--color-ai-inferred)" }} /> ai_inferred ({summary.ai_inferred_changes})
          </span>
          <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span style={{ width: "8px", height: "8px", borderRadius: "2px", background: "var(--color-human)" }} /> human ({summary.human_changes})
          </span>
        </div>
      </div>

      {/* Stored Function Call Card */}
      <div style={{
        background: "var(--bg-surface)",
        border: "1px solid var(--border-subtle)",
        borderRadius: "6px",
        padding: "16px 20px",
        marginBottom: "24px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <Database size={18} color="var(--color-primary)" />
          <div>
            <span style={{ fontWeight: 600, fontSize: "13px" }}>PostgreSQL Stored Function Active</span>
            <div className="font-mono" style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "2px" }}>
              SELECT * FROM get_project_provenance_summary('{project?.project_id}');
            </div>
          </div>
        </div>
        <span className="badge" style={{ background: "rgba(16, 185, 129, 0.1)", color: "#34d399" }}>
          STABLE · SQL Executed
        </span>
      </div>

      {/* Recent Decisions Section */}
      <div>
        <h2 style={{ fontSize: "16px", fontWeight: 600, marginBottom: "14px" }}>Active Engineering Decisions</h2>
        {decisions.slice(0, 3).map((d) => (
          <DecisionCard key={d.decision_id} decision={d} />
        ))}
      </div>
    </div>
  );
}
