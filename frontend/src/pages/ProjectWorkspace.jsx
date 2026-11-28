/**
 * frontend/src/pages/ProjectWorkspace.jsx
 *
 * Live Project Workspace: auto-syncs GitHub commits on open, renders the
 * interactive React Flow File/Module <-> Decision provenance graph, timeline,
 * and batch AI chat import modal.
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
import { ProvenanceGraph } from "../components/workspace/ProvenanceGraph";
import { ProjectTimeline } from "../components/workspace/ProjectTimeline";
import { ImportChatsModal } from "../components/workspace/ImportChatsModal";
import { OriginBadge, fmtDateTime } from "../components/workspace/shared";

const PAGE_SIZE = 100;
const MAX_PAGES = 100;

async function fetchAllPages(fetchPageFn, idKey, isCancelled) {
  const seen = new Set();
  const items = [];
  let offset = 0;

  for (let i = 0; i < MAX_PAGES; i += 1) {
    if (isCancelled()) return items;
    const page = await fetchPageFn({ limit: PAGE_SIZE, offset });
    if (isCancelled() || !Array.isArray(page) || page.length === 0) break;

    let added = 0;
    for (const row of page) {
      const key = row?.[idKey];
      if (key != null && !seen.has(key)) {
        seen.add(key);
        items.push(row);
        added += 1;
      }
    }
    if (page.length < PAGE_SIZE || added === 0) break;
    offset += PAGE_SIZE;
  }

  return items;
}

export function ProjectWorkspace({ project, currentUser, onBack }) {
  const [activeTab, setActiveTab] = useState("graph");
  const [showImportModal, setShowImportModal] = useState(false);

  const [commits, setCommits] = useState([]);
  const [codeChanges, setCodeChanges] = useState([]);
  const [decisions, setDecisions] = useState([]);
  const [timeline, setTimeline] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState(null);

  const [syncStatus, setSyncStatus] = useState(null);
  const [syncMsg, setSyncMsg] = useState(null);
  const syncedProjectRef = useRef(null);

  const hasGitHub = Boolean(currentUser?.linked_providers?.includes("github"));
  const canSync = hasGitHub && Boolean(project?.repository_url);

  const refreshProjectData = async (isCancelled = () => false) => {
    const pid = project.project_id;
    const [c, ch, d, tl] = await Promise.all([
      fetchAllPages(({ limit, offset }) => fetchCommits(pid, { limit, offset }), "commit_id", isCancelled),
      fetchAllPages(({ limit, offset }) => fetchCodeChanges(pid, { limit, offset }), "change_id", isCancelled),
      fetchDecisions(pid),
      fetchTimeline(pid, { limit: 100 }),
    ]);
    if (isCancelled()) return;
    setCommits(c);
    setCodeChanges(ch);
    setDecisions(d);
    setTimeline(tl);
  };

  useEffect(() => {
    if (!project?.project_id) return;
    let cancelled = false;
    setLoading(true);
    setErrorMsg(null);

    refreshProjectData(() => cancelled)
      .catch((err) => {
        if (!cancelled) setErrorMsg(err.message || "Failed to load project workspace.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [project?.project_id]);

  // Auto-sync GitHub commits on workspace open
  useEffect(() => {
    if (!project?.project_id || !canSync) return;
    if (syncedProjectRef.current === project.project_id) return;
    syncedProjectRef.current = project.project_id;

    let cancelled = false;
    setSyncStatus("syncing");
    setSyncMsg(null);

    syncGitHubProject(project.project_id, 20)
      .then(async (res) => {
        if (cancelled) return;
        setSyncStatus("done");
        setSyncMsg(`Synced ${res.synced_commits} new (${res.skipped_commits} skipped)`);
        await refreshProjectData(() => cancelled);
      })
      .catch((err) => {
        if (!cancelled) {
          setSyncStatus("error");
          setSyncMsg(err.message || "Sync failed.");
        }
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
      setSyncMsg(`Synced ${res.synced_commits} new (${res.skipped_commits} skipped)`);
      await refreshProjectData();
    } catch (err) {
      setSyncStatus("error");
      setSyncMsg(err.message || "Sync failed.");
    }
  };

  const handleChangeLinked = (updated) => {
    setCodeChanges((prev) =>
      prev.map((c) => (c.change_id === updated.change_id ? updated : c))
    );
  };

  const handleBatchIngested = async (res) => {
    setSyncStatus("done");
    setSyncMsg(
      `Imported ${res.interactions_count} chat(s) · ${res.staged_decisions.length} decision(s) · ${res.auto_linked_changes.length} linked file(s)`
    );
    await refreshProjectData();
  };

  const aiLinkedCount = codeChanges.filter(
    (c) => c.origin === "ai_exact" || c.origin === "ai_inferred"
  ).length;
  const unlinkedCount = codeChanges.filter((c) => !c.decision && !c.interaction).length;

  const visibleDecisionsCount = decisions.filter((d) => d.status !== "rejected").length;

  const metrics = [
    { label: "Commits", value: commits.length },
    { label: "File Changes", value: codeChanges.length },
    { label: "Decisions", value: visibleDecisionsCount },
    { label: "AI-Linked", value: aiLinkedCount },
    { label: "Unlinked", value: unlinkedCount },
  ];

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", background: "var(--bg-app)" }}>
      <WorkspaceHeader
        project={project}
        hasGitHub={hasGitHub}
        canSync={canSync}
        syncStatus={syncStatus}
        syncMsg={syncMsg}
        onSync={handleManualSync}
        onOpenImportChats={() => setShowImportModal(true)}
        onBack={onBack}
        metrics={metrics}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
      />

      <main style={{ flex: 1, padding: "20px 24px", maxWidth: "1500px", width: "100%", margin: "0 auto" }}>
        {errorMsg && (
          <div style={{ marginBottom: "14px", padding: "10px 14px", borderRadius: "6px", background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)", color: "#f87171", fontSize: "13px" }}>
            {errorMsg}
          </div>
        )}

        {loading ? (
          <div style={{ padding: "40px", textAlign: "center", color: "var(--text-muted)" }}>
            Loading workspace graph...
          </div>
        ) : activeTab === "graph" ? (
          <ProvenanceGraph
            commits={commits}
            codeChanges={codeChanges}
            decisions={decisions}
            onChangeLinked={handleChangeLinked}
          />
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "18px", alignItems: "start" }}>
            <section style={{ background: "var(--bg-surface)", border: "1px solid var(--border-subtle)", borderRadius: "8px", padding: "16px" }}>
              <h3 style={{ fontSize: "14px", fontWeight: 600, marginBottom: "12px" }}>
                Activity Timeline ({timeline.length})
              </h3>
              <ProjectTimeline timeline={timeline} loading={false} error={null} maxItems={60} />
            </section>

            <section style={{ background: "var(--bg-surface)", border: "1px solid var(--border-subtle)", borderRadius: "8px", padding: "16px" }}>
              <h3 style={{ fontSize: "14px", fontWeight: 600, marginBottom: "12px" }}>
                Synced Commits &amp; Files ({commits.length})
              </h3>
              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                {commits.map((c) => {
                  const files = codeChanges.filter((ch) => ch.commit?.commit_id === c.commit_id);
                  return (
                    <div key={c.commit_id} style={{ background: "var(--bg-app)", border: "1px solid var(--border-subtle)", borderRadius: "6px", padding: "10px 12px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", color: "var(--text-muted)" }}>
                        <span className="font-mono">{c.commit_hash?.slice(0, 7)}</span>
                        <span>{fmtDateTime(c.commit_time)}</span>
                      </div>
                      <div style={{ fontSize: "13px", fontWeight: 600, marginTop: "3px" }}>{c.message}</div>
                      {files.length > 0 && (
                        <div style={{ display: "flex", flexDirection: "column", gap: "4px", marginTop: "8px" }}>
                          {files.map((f) => (
                            <div key={f.change_id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "11px" }}>
                              <span className="font-mono" style={{ color: "var(--text-secondary)" }}>{f.file_path}</span>
                              <OriginBadge origin={f.origin} />
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </section>
          </div>
        )}
      </main>

      {showImportModal && (
        <ImportChatsModal
          projectId={project.project_id}
          onClose={() => setShowImportModal(false)}
          onIngested={handleBatchIngested}
        />
      )}
    </div>
  );
}
