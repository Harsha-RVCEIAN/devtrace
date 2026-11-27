/**
 * frontend/src/pages/ProjectWorkspace.jsx
 *
 * Live Project Workspace — opens when a user selects a project.
 * Coordinates GitHub auto-sync, parallel data loading, and workspace tabs.
 */

import React, { useEffect, useRef, useState } from "react";
import {
  fetchCommits,
  fetchCodeChanges,
  fetchDecisions,
  fetchTimeline,
  syncGitHubProject,
} from "../api/client";
import { WorkspaceHeader } from "../components/workspace/WorkspaceHeader";
import { ProvenanceInspector } from "../components/workspace/ProvenanceInspector";
import { DecisionGraphView } from "../components/workspace/DecisionGraphView";
import { ReviewQueue } from "../components/workspace/ReviewQueue";
import { ProjectTimeline } from "../components/workspace/ProjectTimeline";
import { fmtDate } from "../components/workspace/shared";

function OverviewSection({
  project,
  metrics,
  timeline,
  timelineLoading,
  timelineError,
  loadedLimitHit,
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* 5 Summary Metrics */}
      <div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "12px" }}>
          {metrics.map((m) => (
            <div
              key={m.label}
              style={{
                flex: "1 1 150px",
                minWidth: 130,
                background: "var(--bg-surface)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "6px",
                padding: "12px 16px",
              }}
            >
              <div style={{ fontSize: "22px", fontWeight: 700, lineHeight: 1.2 }}>{m.value}</div>
              <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "2px" }}>
                {m.label}
              </div>
              {m.sub && (
                <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "2px" }}>
                  {m.sub}
                </div>
              )}
            </div>
          ))}
        </div>
        {loadedLimitHit && (
          <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "6px" }}>
            Metrics reflect the latest 100 loaded records.
          </div>
        )}
      </div>

      {/* Project Identity */}
      <section
        style={{
          background: "var(--bg-surface)",
          border: "1px solid var(--border-subtle)",
          borderRadius: "8px",
          padding: "16px 20px",
        }}
      >
        <h3 style={{ fontSize: "14px", fontWeight: 600, marginBottom: "10px" }}>Project Details</h3>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "120px 1fr",
            gap: "6px 12px",
            fontSize: "13px",
          }}
        >
          <span style={{ color: "var(--text-secondary)" }}>Name</span>
          <span>{project.project_name}</span>
          {project.description && (
            <>
              <span style={{ color: "var(--text-secondary)" }}>Description</span>
              <span>{project.description}</span>
            </>
          )}
          {project.repository_url && (
            <>
              <span style={{ color: "var(--text-secondary)" }}>Repository</span>
              <a
                href={project.repository_url}
                target="_blank"
                rel="noopener noreferrer"
                style={{ color: "var(--color-primary)", wordBreak: "break-all" }}
              >
                {project.repository_url}
              </a>
            </>
          )}
          <span style={{ color: "var(--text-secondary)" }}>Created</span>
          <span>{fmtDate(project.created_at)}</span>
        </div>
      </section>

      {/* Project Timeline */}
      <section
        style={{
          background: "var(--bg-surface)",
          border: "1px solid var(--border-subtle)",
          borderRadius: "8px",
          padding: "16px 20px",
        }}
      >
        <h3 style={{ fontSize: "14px", fontWeight: 600, marginBottom: "12px" }}>
          Recent Activity &amp; Timeline
        </h3>
        <ProjectTimeline
          timeline={timeline}
          loading={timelineLoading}
          error={timelineError}
          maxItems={20}
        />
      </section>
    </div>
  );
}

export function ProjectWorkspace({ project, currentUser, onBack }) {
  const [activeTab, setActiveTab] = useState("overview");

  const [commits, setCommits] = useState([]);
  const [commitsLoading, setCommitsLoading] = useState(true);
  const [commitsError, setCommitsError] = useState(null);

  const [codeChanges, setCodeChanges] = useState([]);
  const [changesLoading, setChangesLoading] = useState(true);
  const [changesError, setChangesError] = useState(null);

  const [decisions, setDecisions] = useState([]);
  const [decisionsLoading, setDecisionsLoading] = useState(true);
  const [decisionsError, setDecisionsError] = useState(null);

  const [timeline, setTimeline] = useState([]);
  const [timelineLoading, setTimelineLoading] = useState(true);
  const [timelineError, setTimelineError] = useState(null);

  const [syncStatus, setSyncStatus] = useState(null);
  const [syncMsg, setSyncMsg] = useState(null);
  const [lastSyncTime, setLastSyncTime] = useState(null);

  // Prevent duplicate auto-sync calls in React StrictMode
  const syncedProjectRef = useRef(null);

  const hasGitHub = Boolean(currentUser?.linked_providers?.includes("github"));
  const canSync = hasGitHub && Boolean(project?.repository_url);

  // Load persisted project data independently
  useEffect(() => {
    if (!project?.project_id) return;
    const projectId = project.project_id;
    let cancelled = false;

    async function loadAll() {
      setCommitsLoading(true);
      setCommitsError(null);
      setChangesLoading(true);
      setChangesError(null);
      setDecisionsLoading(true);
      setDecisionsError(null);
      setTimelineLoading(true);
      setTimelineError(null);

      const [commitsRes, changesRes, decisionsRes, timelineRes] = await Promise.allSettled([
        fetchCommits(projectId, { limit: 100 }),
        fetchCodeChanges(projectId, { limit: 100 }),
        fetchDecisions(projectId),
        fetchTimeline(projectId, { limit: 100 }),
      ]);

      if (cancelled) return;

      if (commitsRes.status === "fulfilled") {
        setCommits(commitsRes.value);
      } else {
        setCommitsError(commitsRes.reason?.message || "Failed to load commits.");
      }
      setCommitsLoading(false);

      if (changesRes.status === "fulfilled") {
        setCodeChanges(changesRes.value);
      } else {
        setChangesError(changesRes.reason?.message || "Failed to load code changes.");
      }
      setChangesLoading(false);

      if (decisionsRes.status === "fulfilled") {
        setDecisions(decisionsRes.value);
      } else {
        setDecisionsError(decisionsRes.reason?.message || "Failed to load decisions.");
      }
      setDecisionsLoading(false);

      if (timelineRes.status === "fulfilled") {
        setTimeline(timelineRes.value);
      } else {
        setTimelineError(timelineRes.reason?.message || "Failed to load timeline.");
      }
      setTimelineLoading(false);
    }

    loadAll();
    return () => {
      cancelled = true;
    };
  }, [project?.project_id]);

  // Automatic GitHub synchronization on workspace open when eligible
  useEffect(() => {
    if (!project?.project_id || !canSync) return;
    if (syncedProjectRef.current === project.project_id) return;
    syncedProjectRef.current = project.project_id;

    let cancelled = false;
    setSyncStatus("syncing");
    setSyncMsg(null);

    syncGitHubProject(project.project_id, 20)
      .then((res) => {
        if (cancelled) return;
        setSyncStatus("done");
        setLastSyncTime(new Date().toISOString());
        setSyncMsg(`Synced ${res.synced_commits} new commit(s), ${res.total_changes} file change(s).`);

        Promise.allSettled([
          fetchCommits(project.project_id, { limit: 100 }),
          fetchCodeChanges(project.project_id, { limit: 100 }),
          fetchTimeline(project.project_id, { limit: 100 }),
        ]).then(([c, ch, tl]) => {
          if (cancelled) return;
          if (c.status === "fulfilled") setCommits(c.value);
          if (ch.status === "fulfilled") setCodeChanges(ch.value);
          if (tl.status === "fulfilled") setTimeline(tl.value);
        });
      })
      .catch((err) => {
        if (cancelled) return;
        setSyncStatus("error");
        setSyncMsg(err.message || "Synchronization failed.");
      });

    return () => {
      cancelled = true;
    };
  }, [project?.project_id, canSync]);

  const handleManualSync = async () => {
    if (!canSync || !project?.project_id) return;
    setSyncStatus("syncing");
    setSyncMsg(null);
    try {
      const res = await syncGitHubProject(project.project_id, 20);
      setSyncStatus("done");
      setLastSyncTime(new Date().toISOString());
      setSyncMsg(`Synced ${res.synced_commits} new commit(s), ${res.total_changes} file change(s).`);
      const [c, ch, tl] = await Promise.allSettled([
        fetchCommits(project.project_id, { limit: 100 }),
        fetchCodeChanges(project.project_id, { limit: 100 }),
        fetchTimeline(project.project_id, { limit: 100 }),
      ]);
      if (c.status === "fulfilled") setCommits(c.value);
      if (ch.status === "fulfilled") setCodeChanges(ch.value);
      if (tl.status === "fulfilled") setTimeline(tl.value);
    } catch (err) {
      setSyncStatus("error");
      setSyncMsg(err.message || "Synchronization failed.");
    }
  };

  const handleDecisionUpdated = (updated) => {
    setDecisions((prev) =>
      prev.map((d) => (d.decision_id === updated.decision_id ? updated : d))
    );
  };

  const handleChangeLinked = (updated) => {
    setCodeChanges((prev) =>
      prev.map((c) => (c.change_id === updated.change_id ? updated : c))
    );
  };

  if (!project?.project_id) {
    return (
      <div style={{ padding: "24px", maxWidth: "800px", margin: "0 auto" }}>
        <p style={{ color: "var(--text-secondary)", fontSize: "14px", marginBottom: "12px" }}>
          Invalid or missing project selection.
        </p>
        <button
          type="button"
          onClick={onBack}
          style={{
            padding: "6px 12px",
            borderRadius: "4px",
            border: "1px solid var(--border-subtle)",
            background: "transparent",
            color: "var(--text-main)",
            cursor: "pointer",
          }}
        >
          ← Back to Projects
        </button>
      </div>
    );
  }

  // Exact 5 required metrics calculated from actual API data
  const aiAttributed = codeChanges.filter(
    (c) => c.origin === "ai_exact" || c.origin === "ai_inferred"
  ).length;
  const humanAttributed = codeChanges.filter((c) => c.origin === "human").length;
  const unlinked = codeChanges.filter((c) => !c.decision && !c.interaction).length;
  const proposedCount = decisions.filter((d) => d.status === "proposed").length;
  const loadedLimitHit = commits.length >= 100 || codeChanges.length >= 100;

  const metrics = [
    { label: "Total Commits", value: commits.length },
    { label: "Total File Changes", value: codeChanges.length },
    { label: "AI-Attributed", value: aiAttributed, sub: "ai_exact + ai_inferred" },
    { label: "Human", value: humanAttributed, sub: "origin = human" },
    { label: "Unlinked", value: unlinked, sub: "no decision or interaction" },
  ];

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", background: "var(--bg-app)" }}>
      <WorkspaceHeader
        project={project}
        hasGitHub={hasGitHub}
        canSync={canSync}
        syncStatus={syncStatus}
        syncMsg={syncMsg}
        lastSyncTime={lastSyncTime}
        onSync={handleManualSync}
        onBack={onBack}
        metrics={metrics}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        proposedCount={proposedCount}
      />

      <main style={{ flex: 1, padding: "24px", maxWidth: "1400px", width: "100%", margin: "0 auto", boxSizing: "border-box" }}>
        {activeTab === "overview" && (
          <OverviewSection
            project={project}
            metrics={metrics}
            timeline={timeline}
            timelineLoading={timelineLoading}
            timelineError={timelineError}
            loadedLimitHit={loadedLimitHit}
          />
        )}
        {activeTab === "provenance" && (
          <ProvenanceInspector
            commits={commits}
            codeChanges={codeChanges}
            decisions={decisions}
            commitsLoading={commitsLoading}
            commitsError={commitsError}
            changesLoading={changesLoading}
            changesError={changesError}
            onChangeLinked={handleChangeLinked}
          />
        )}
        {activeTab === "graph" && (
          <DecisionGraphView
            decisions={decisions}
            decisionsLoading={decisionsLoading}
            decisionsError={decisionsError}
            timeline={timeline}
            timelineLoading={timelineLoading}
            timelineError={timelineError}
          />
        )}
        {activeTab === "review" && (
          <ReviewQueue
            decisions={decisions}
            decisionsLoading={decisionsLoading}
            decisionsError={decisionsError}
            onDecisionUpdated={handleDecisionUpdated}
          />
        )}
      </main>
    </div>
  );
}
