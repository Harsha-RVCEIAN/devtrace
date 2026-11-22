import React, { useState } from "react";
import { DecisionCard } from "../components/DecisionCard";
import { Filter, Search } from "lucide-react";

export function Decisions({ decisions }) {
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
    <div style={{ maxWidth: "1200px", margin: "0 auto", padding: "24px" }}>
      {/* Page Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
        <div>
          <h1 style={{ fontSize: "20px", fontWeight: 700, marginBottom: "4px" }}>
            Engineering Decisions Registry
          </h1>
          <p style={{ color: "var(--text-secondary)", fontSize: "13px" }}>
            Immutable relational audit trail of architectural choices, evaluated alternatives, and causal justifications.
          </p>
        </div>

        {/* Filter Controls */}
        <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
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
                width: "240px",
              }}
            />
            <Search size={14} color="var(--text-muted)" style={{ position: "absolute", left: "10px", top: "8px" }} />
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
            <option value="active">Active</option>
            <option value="replaced">Replaced</option>
            <option value="proposed">Proposed</option>
          </select>
        </div>
      </div>

      {/* Decision Cards List */}
      <div>
        {filteredDecisions.length === 0 ? (
          <div style={{ padding: "40px", textAlign: "center", color: "var(--text-muted)", background: "var(--bg-surface)", borderRadius: "6px" }}>
            No decisions match the selected filter.
          </div>
        ) : (
          filteredDecisions.map((d) => (
            <DecisionCard key={d.decision_id} decision={d} />
          ))
        )}
      </div>
    </div>
  );
}
