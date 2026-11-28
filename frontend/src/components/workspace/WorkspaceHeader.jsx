import React from "react";
import { ArrowLeft, RefreshCw, AlertTriangle, CheckCircle2, Upload } from "lucide-react";

export function WorkspaceHeader({
  project,
  hasGitHub,
  canSync,
  syncStatus,
  syncMsg,
  onSync,
  onOpenImportChats,
  onBack,
  metrics,
  activeTab,
  setActiveTab,
}) {
  const TABS = [
    { id: "graph", label: "Architecture & Decision Graph" },
    { id: "timeline", label: "Timeline & Commits" },
  ];

  return (
    <header
      style={{
        background: "var(--bg-surface)",
        borderBottom: "1px solid var(--border-subtle)",
        padding: "0 24px",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "12px", padding: "12px 0 10px", flexWrap: "wrap" }}>
        <button
          type="button"
          onClick={onBack}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "6px",
            padding: "5px 10px",
            borderRadius: "4px",
            border: "1px solid var(--border-subtle)",
            background: "transparent",
            color: "var(--text-secondary)",
            fontSize: "13px",
            cursor: "pointer",
          }}
        >
          <ArrowLeft size={14} />
          Projects
        </button>

        <div style={{ flex: 1, minWidth: "180px" }}>
          <div style={{ fontSize: "17px", fontWeight: 700 }}>{project.project_name}</div>
          {project.repository_url && (
            <div className="font-mono" style={{ fontSize: "11px", color: "var(--text-muted)", wordBreak: "break-all" }}>
              {project.repository_url}
            </div>
          )}
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
          {project.repository_url && !hasGitHub && (
            <span style={{ display: "inline-flex", alignItems: "center", gap: "4px", fontSize: "12px", color: "#f59e0b" }}>
              <AlertTriangle size={13} />
              GitHub not linked
            </span>
          )}
          {syncStatus === "syncing" && (
            <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>Syncing commits…</span>
          )}
          {syncStatus === "done" && syncMsg && (
            <span style={{ display: "inline-flex", alignItems: "center", gap: "4px", fontSize: "12px", color: "#10b981" }}>
              <CheckCircle2 size={13} />
              {syncMsg}
            </span>
          )}
          {syncStatus === "error" && syncMsg && (
            <span style={{ fontSize: "12px", color: "#f87171" }}>{syncMsg}</span>
          )}

          <button
            type="button"
            onClick={onOpenImportChats}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              padding: "6px 12px",
              borderRadius: "5px",
              border: "none",
              background: "var(--color-primary)",
              color: "#fff",
              fontSize: "12px",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            <Upload size={13} />
            Import AI Chats
          </button>

          {canSync && (
            <button
              type="button"
              onClick={onSync}
              disabled={syncStatus === "syncing"}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "5px",
                padding: "6px 12px",
                borderRadius: "5px",
                border: "1px solid var(--border-strong)",
                background: "var(--bg-surface-elevated)",
                color: "var(--text-main)",
                fontSize: "12px",
                fontWeight: 600,
                cursor: syncStatus === "syncing" ? "not-allowed" : "pointer",
              }}
            >
              <RefreshCw size={12} />
              Sync
            </button>
          )}
        </div>
      </div>

      <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", paddingBottom: "10px", alignItems: "center" }}>
        {metrics.map((m) => (
          <span
            key={m.label}
            style={{
              padding: "3px 10px",
              borderRadius: "4px",
              background: "var(--bg-app)",
              border: "1px solid var(--border-subtle)",
              fontSize: "12px",
            }}
          >
            <strong>{m.value}</strong> <span style={{ color: "var(--text-muted)" }}>{m.label}</span>
          </span>
        ))}
      </div>

      <nav aria-label="Workspace sections" style={{ display: "flex", gap: "0", overflowX: "auto" }}>
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            style={{
              padding: "8px 14px",
              border: "none",
              borderBottom: activeTab === tab.id ? "2px solid var(--color-primary)" : "2px solid transparent",
              background: "transparent",
              color: activeTab === tab.id ? "var(--color-primary)" : "var(--text-secondary)",
              fontWeight: activeTab === tab.id ? 600 : 400,
              fontSize: "13px",
              cursor: "pointer",
              whiteSpace: "nowrap",
              marginBottom: "-1px",
            }}
          >
            {tab.label}
          </button>
        ))}
      </nav>
    </header>
  );
}
