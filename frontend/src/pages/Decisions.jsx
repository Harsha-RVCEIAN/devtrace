import React, { useState } from "react";
import { DecisionCard } from "../components/DecisionCard";
import { DecisionGraph } from "../components/DecisionGraph";
import { Filter, Search, GitBranch, ListFilter, LayoutGrid } from "lucide-react";

export function Decisions({ decisions = [] }) {
  const [viewMode, setViewMode] = useState("graph"); // "graph" | "list"
  const [statusFilter, setStatusFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");

  const filteredDecisions = decisions.filter((d) => {
    const matchesStatus = statusFilter === "all" || d.status === statusFilter;
    const matchesSearch =
      d.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      d.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (d.reason_text && d.reason_text.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesStatus && matchesSearch;
  });

  return (
    <div style={{ maxWidth: "1280px", margin: "0 auto", padding: "24px" }}>
      {/* Page Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          marginBottom: "24px",
          flexWrap: "wrap",
          gap: "16px",
        }}
      >
        <div>
          <h1 style={{ fontSize: "20px", fontWeight: 700, marginBottom: "4px" }}>
            Architecture Decision Graph & Registry
          </h1>
          <p style={{ color: "var(--text-secondary)", fontSize: "13px" }}>
            Relational DAG of architectural decisions, evaluated alternatives, and causal justifications with superseding lineage.
          </p>
        </div>

        {/* View Toggle & Filter Controls */}
        <div style={{ display: "flex", gap: "12px", alignItems: "center", flexWrap: "wrap" }}>
          {/* View Mode Toggle */}
          <div
            style={{
              display: "flex",
              background: "var(--bg-surface)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "4px",
              padding: "2px",
            }}
          >
            <button
              onClick={() => setViewMode("graph")}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                padding: "6px 12px",
                borderRadius: "3px",
                fontSize: "12px",
                fontWeight: 600,
                cursor: "pointer",
                background: viewMode === "graph" ? "var(--bg-surface-elevated)" : "transparent",
                color: viewMode === "graph" ? "var(--color-primary)" : "var(--text-secondary)",
                border: "none",
              }}
            >
              <GitBranch size={13} />
              Architecture DAG
            </button>
            <button
              onClick={() => setViewMode("list")}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                padding: "6px 12px",
                borderRadius: "3px",
                fontSize: "12px",
                fontWeight: 600,
                cursor: "pointer",
                background: viewMode === "list" ? "var(--bg-surface-elevated)" : "transparent",
                color: viewMode === "list" ? "var(--color-primary)" : "var(--text-secondary)",
                border: "none",
              }}
            >
              <LayoutGrid size={13} />
              List / Cards
            </button>
          </div>

          {/* Search Input */}
          <div style={{ position: "relative" }}>
            <input
              type="text"
              placeholder="Search decisions or reasons..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                background: "var(--bg-surface)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "4px",
                padding: "6px 12px 6px 30px",
                color: "var(--text-main)",
                fontSize: "12px",
                width: "220px",
              }}
            />
            <Search
              size={14}
              color="var(--text-muted)"
              style={{ position: "absolute", left: "10px", top: "8px" }}
            />
          </div>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            style={{
              background: "var(--bg-surface)",
              color: "var(--text-main)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "4px",
              padding: "6px 10px",
              fontSize: "12px",
              cursor: "pointer",
            }}
          >
            <option value="all">All Statuses</option>
            <option value="active">Active Only</option>
            <option value="replaced">Superseded / Replaced</option>
            <option value="proposed">Proposed Candidates</option>
          </select>
        </div>
      </div>

      {/* Main View Area */}
      {filteredDecisions.length === 0 ? (
        <div
          style={{
            padding: "48px",
            textAlign: "center",
            color: "var(--text-muted)",
            background: "var(--bg-surface)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "6px",
          }}
        >
          No architectural decisions match your query or filters.
        </div>
      ) : viewMode === "graph" ? (
        <DecisionGraph decisions={filteredDecisions} />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          {filteredDecisions.map((d) => (
            <DecisionCard key={d.decision_id} decision={d} />
          ))}
        </div>
      )}
    </div>
  );
}
