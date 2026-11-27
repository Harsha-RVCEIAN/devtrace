import React, { useEffect, useState } from "react";
import { FolderGit2, Github, Lock, Globe, RefreshCw, UserPlus, Plus } from "lucide-react";
import {
  fetchGitHubRepos,
  fetchProjects,
  getGitHubLoginUrl,
  importGitHubRepo,
  inviteProjectMember,
  syncGitHubProject,
} from "../api/client";

export function Projects({ user }) {
  const [projects, setProjects] = useState([]);
  const [repos, setRepos] = useState([]);
  const [repoUrlInput, setRepoUrlInput] = useState("");
  const [inviteInputs, setInviteInputs] = useState({});
  const [statusMessage, setStatusMessage] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);
  const [busyId, setBusyId] = useState(null);

  const hasGitHub = user?.linked_providers?.includes("github");

  const loadData = async () => {
    setErrorMessage(null);
    try {
      const projs = await fetchProjects();
      setProjects(projs);
      if (hasGitHub) {
        const ghRepos = await fetchGitHubRepos();
        setRepos(ghRepos);
      }
    } catch (err) {
      setErrorMessage(err.message || "Failed to load projects.");
    }
  };

  useEffect(() => {
    loadData();
  }, [hasGitHub]);

  const handleImport = async (repoSlug) => {
    if (!repoSlug.trim()) return;
    setBusyId(repoSlug);
    setErrorMessage(null);
    setStatusMessage(null);
    try {
      const res = await importGitHubRepo(repoSlug.trim(), 20);
      setStatusMessage(
        `Imported ${res.project_name} (${res.membership_mode}): synced ${res.synced_commits} commits, ${res.total_changes} file changes.`
      );
      setRepoUrlInput("");
      await loadData();
    } catch (err) {
      setErrorMessage(err.message || "Import failed.");
    } finally {
      setBusyId(null);
    }
  };

  const handleSync = async (projectId) => {
    setBusyId(projectId);
    setErrorMessage(null);
    setStatusMessage(null);
    try {
      const res = await syncGitHubProject(projectId, 20);
      setStatusMessage(
        `Sync complete: ${res.synced_commits} new commits (${res.skipped_commits} already present), ${res.total_changes} file changes.`
      );
    } catch (err) {
      setErrorMessage(err.message || "Sync failed.");
    } finally {
      setBusyId(null);
    }
  };

  const handleInvite = async (projectId) => {
    const identifier = (inviteInputs[projectId] || "").trim();
    if (!identifier) return;
    setBusyId(`invite-${projectId}`);
    setErrorMessage(null);
    setStatusMessage(null);
    try {
      const res = await inviteProjectMember(projectId, identifier);
      setStatusMessage(`Added ${res.name} (${res.email}) as ${res.role}.`);
      setInviteInputs((prev) => ({ ...prev, [projectId]: "" }));
    } catch (err) {
      setErrorMessage(err.message || "Invite failed.");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div style={{ maxWidth: "1200px", margin: "0 auto", padding: "24px", display: "flex", flexDirection: "column", gap: "24px" }}>
      <div>
        <h1 style={{ fontSize: "20px", fontWeight: 700, marginBottom: "4px" }}>
          Projects & GitHub Sync
        </h1>
        <p style={{ color: "var(--text-secondary)", fontSize: "13px" }}>
          Import your own repositories, collaborator repositories, or any public GitHub URL to track commits and provenance.
        </p>
      </div>

      {statusMessage && (
        <div style={{ padding: "10px 14px", borderRadius: "6px", background: "rgba(16, 185, 129, 0.1)", border: "1px solid rgba(16, 185, 129, 0.3)", color: "#34d399", fontSize: "13px" }}>
          {statusMessage}
        </div>
      )}
      {errorMessage && (
        <div style={{ padding: "10px 14px", borderRadius: "6px", background: "rgba(239, 68, 68, 0.1)", border: "1px solid rgba(239, 68, 68, 0.3)", color: "#f87171", fontSize: "13px" }}>
          {errorMessage}
        </div>
      )}

      {/* Connected Projects */}
      <section style={{ background: "var(--bg-surface)", border: "1px solid var(--border-subtle)", borderRadius: "8px", padding: "20px" }}>
        <h2 style={{ fontSize: "15px", fontWeight: 600, marginBottom: "14px", display: "flex", alignItems: "center", gap: "8px" }}>
          <FolderGit2 size={16} color="var(--color-primary)" />
          Your DevTrace Projects ({projects.length})
        </h2>

        {projects.length === 0 ? (
          <div style={{ color: "var(--text-muted)", fontSize: "13px" }}>
            No projects imported yet. Connect a GitHub repository below.
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            {projects.map((p) => (
              <div
                key={p.project_id}
                style={{
                  background: "var(--bg-app)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "6px",
                  padding: "14px 16px",
                  display: "flex",
                  flexWrap: "wrap",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: "12px",
                }}
              >
                <div>
                  <div style={{ fontWeight: 600, fontSize: "14px" }}>{p.project_name}</div>
                  {p.repository_url && (
                    <div className="font-mono" style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "2px" }}>
                      {p.repository_url}
                    </div>
                  )}
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                  <input
                    type="text"
                    placeholder="Invite email or GitHub handle"
                    value={inviteInputs[p.project_id] || ""}
                    onChange={(e) =>
                      setInviteInputs((prev) => ({ ...prev, [p.project_id]: e.target.value }))
                    }
                    style={{
                      padding: "6px 10px",
                      borderRadius: "4px",
                      border: "1px solid var(--border-subtle)",
                      background: "var(--bg-surface)",
                      color: "var(--text-main)",
                      fontSize: "12px",
                      width: "210px",
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => handleInvite(p.project_id)}
                    disabled={busyId === `invite-${p.project_id}`}
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "5px",
                      padding: "6px 10px",
                      borderRadius: "4px",
                      border: "1px solid var(--border-subtle)",
                      background: "var(--bg-surface-elevated)",
                      color: "var(--text-main)",
                      fontSize: "12px",
                      cursor: "pointer",
                    }}
                  >
                    <UserPlus size={13} />
                    Invite
                  </button>

                  {p.repository_url && hasGitHub && (
                    <button
                      type="button"
                      onClick={() => handleSync(p.project_id)}
                      disabled={busyId === p.project_id}
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "5px",
                        padding: "6px 12px",
                        borderRadius: "4px",
                        border: "none",
                        background: "var(--color-primary)",
                        color: "#fff",
                        fontSize: "12px",
                        fontWeight: 600,
                        cursor: "pointer",
                      }}
                    >
                      <RefreshCw size={13} />
                      {busyId === p.project_id ? "Syncing..." : "Sync Commits"}
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* GitHub Repo Picker */}
      <section style={{ background: "var(--bg-surface)", border: "1px solid var(--border-subtle)", borderRadius: "8px", padding: "20px" }}>
        <h2 style={{ fontSize: "15px", fontWeight: 600, marginBottom: "14px", display: "flex", alignItems: "center", gap: "8px" }}>
          <Github size={16} />
          Import from GitHub
        </h2>

        {!hasGitHub ? (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "12px", flexWrap: "wrap" }}>
            <span style={{ color: "var(--text-secondary)", fontSize: "13px" }}>
              Connect your GitHub account to list and auto-pull your public and private repositories.
            </span>
            <a
              href={getGitHubLoginUrl()}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                padding: "8px 14px",
                borderRadius: "6px",
                background: "#f3f4f6",
                color: "#0c0e14",
                fontWeight: 600,
                fontSize: "13px",
                textDecoration: "none",
              }}
            >
              <Github size={15} />
              Connect GitHub
            </a>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            {/* Paste any owner/repo or URL */}
            <div style={{ display: "flex", gap: "8px" }}>
              <input
                type="text"
                placeholder="Paste any owner/repo or https://github.com/owner/repo"
                value={repoUrlInput}
                onChange={(e) => setRepoUrlInput(e.target.value)}
                style={{
                  flex: 1,
                  padding: "8px 12px",
                  borderRadius: "6px",
                  border: "1px solid var(--border-subtle)",
                  background: "var(--bg-app)",
                  color: "var(--text-main)",
                  fontSize: "13px",
                }}
              />
              <button
                type="button"
                onClick={() => handleImport(repoUrlInput)}
                disabled={!repoUrlInput.trim() || busyId === repoUrlInput.trim()}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  padding: "8px 14px",
                  borderRadius: "6px",
                  border: "none",
                  background: "var(--color-primary)",
                  color: "#fff",
                  fontWeight: 600,
                  fontSize: "13px",
                  cursor: "pointer",
                }}
              >
                <Plus size={14} />
                Import URL
              </button>
            </div>

            {/* List of user/collaborator repos */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: "10px" }}>
              {repos.map((r) => (
                <div
                  key={r.full_name}
                  style={{
                    background: "var(--bg-app)",
                    border: "1px solid var(--border-subtle)",
                    borderRadius: "6px",
                    padding: "12px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: "10px",
                  }}
                >
                  <div style={{ minWidth: 0 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "6px", fontWeight: 600, fontSize: "13px" }}>
                      {r.private ? <Lock size={12} color="#f59e0b" /> : <Globe size={12} color="#10b981" />}
                      <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {r.full_name}
                      </span>
                    </div>
                    <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "2px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {r.description || r.default_branch}
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleImport(r.full_name)}
                    disabled={busyId === r.full_name}
                    style={{
                      padding: "5px 10px",
                      borderRadius: "4px",
                      border: "1px solid var(--border-strong)",
                      background: "var(--bg-surface-elevated)",
                      color: "var(--text-main)",
                      fontSize: "12px",
                      cursor: "pointer",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {busyId === r.full_name ? "Importing..." : "Import"}
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
