import React from "react";
import { Database, GitCommit, Shield, Cpu, Activity, Sparkles, Terminal } from "lucide-react";

export function Navbar({ activeTab, setActiveTab, projects, currentProject, setCurrentProject }) {
  const navItems = [
    { id: "overview", label: "Overview", icon: Activity },
    { id: "decisions", label: "Decisions", icon: Shield },
    { id: "timeline", label: "Timeline", icon: GitCommit },
    { id: "provenance", label: "Provenance Inspector", icon: Database },
    { id: "nlp", label: "NLP Studio", icon: Sparkles },
  ];

  return (
    <header style={{
      borderBottom: "1px solid var(--border-subtle)",
      background: "var(--bg-surface)",
      padding: "0 24px",
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      height: "56px",
      position: "sticky",
      top: 0,
      zIndex: 100,
    }}>
      {/* Brand & Project Selector */}
      <div style={{ display: "flex", alignItems: "center", gap: "20px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px", fontWeight: 700, fontSize: "16px", letterSpacing: "-0.02em" }}>
          <div style={{ background: "var(--color-primary)", padding: "4px 6px", borderRadius: "4px", display: "flex", alignItems: "center" }}>
            <Terminal size={16} color="#fff" />
          </div>
          <span>DevTrace</span>
          <span style={{ fontSize: "11px", fontWeight: 500, color: "var(--text-muted)", marginLeft: "4px" }}>DBMS Lab</span>
        </div>

        <div style={{ height: "20px", width: "1px", background: "var(--border-subtle)" }} />

        {/* Project Selector */}
        <select
          value={currentProject?.project_id || ""}
          onChange={(e) => {
            const p = projects.find(proj => proj.project_id === e.target.value);
            if (p) setCurrentProject(p);
          }}
          style={{
            background: "var(--bg-app)",
            color: "var(--text-main)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "4px",
            padding: "4px 10px",
            fontSize: "12px",
            fontWeight: 500,
            cursor: "pointer",
          }}
        >
          {projects.map(p => (
            <option key={p.project_id} value={p.project_id}>
              {p.project_name}
            </option>
          ))}
        </select>
      </div>

      {/* Navigation Tabs */}
      <nav style={{ display: "flex", gap: "4px" }}>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                padding: "6px 14px",
                borderRadius: "4px",
                border: "none",
                background: isActive ? "var(--bg-surface-elevated)" : "transparent",
                color: isActive ? "var(--text-main)" : "var(--text-secondary)",
                fontWeight: isActive ? 600 : 500,
                fontSize: "13px",
                cursor: "pointer",
                transition: "all 0.15s ease",
              }}
            >
              <Icon size={14} color={isActive ? "var(--color-primary)" : "var(--text-muted)"} />
              {item.label}
            </button>
          );
        })}
      </nav>

      {/* Status indicator */}
      <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "11px", color: "var(--text-muted)" }}>
        <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#10b981", display: "inline-block" }} />
        <span className="font-mono">PostgreSQL 16 · Online</span>
      </div>
    </header>
  );
}
