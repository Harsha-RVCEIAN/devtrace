/**
 * frontend/src/api/client.js
 *
 * REST API Client for DevTrace backend using HTTP-only session cookies.
 */

export const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8001";

async function apiFetch(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    headers: {
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...(options.headers || {}),
    },
    ...options,
  });

  if (res.status === 204) {
    return null;
  }

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.detail || `Server returned error ${res.status}`);
    err.status = res.status;
    throw err;
  }
  return data;
}

export function getGitHubLoginUrl() {
  return `${API_BASE}/auth/github/login`;
}

export function getGoogleLoginUrl() {
  return `${API_BASE}/auth/google/login`;
}

export async function fetchCurrentUser() {
  try {
    return await apiFetch("/auth/me");
  } catch (err) {
    if (err.status === 401) return null;
    throw err;
  }
}

export async function loginWithEmail(email, password) {
  return apiFetch("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function registerWithEmail(name, email, password) {
  return apiFetch("/auth/register", {
    method: "POST",
    body: JSON.stringify({ name, email, password }),
  });
}

export async function logout() {
  return apiFetch("/auth/logout", { method: "POST" });
}

export async function fetchProjects() {
  return apiFetch("/projects");
}

export async function fetchGitHubRepos() {
  return apiFetch("/github/repos");
}

export async function importGitHubRepo(repo, syncLimit = 20) {
  return apiFetch("/github/import", {
    method: "POST",
    body: JSON.stringify({ repo, sync_limit: syncLimit }),
  });
}

export async function syncGitHubProject(projectId, limit = 20) {
  return apiFetch(`/github/projects/${projectId}/sync`, {
    method: "POST",
    body: JSON.stringify({ limit }),
  });
}

export async function inviteProjectMember(projectId, identifier, role = "member") {
  return apiFetch(`/github/projects/${projectId}/members`, {
    method: "POST",
    body: JSON.stringify({ identifier, role }),
  });
}

export async function extractCandidatesFromTurns(turns, engine = "rules", projectId = null) {
  return apiFetch("/nlp/extract-candidates", {
    method: "POST",
    body: JSON.stringify({
      turns,
      engine,
      project_id: projectId || undefined,
    }),
  });
}

// --- Workspace API ---

export async function fetchCommits(projectId, { limit = 50, offset = 0 } = {}) {
  return apiFetch(`/projects/${projectId}/commits?limit=${limit}&offset=${offset}`);
}

export async function fetchCodeChanges(projectId, { missing_provenance_only = false, limit = 50, offset = 0 } = {}) {
  return apiFetch(
    `/projects/${projectId}/code-changes?missing_provenance_only=${missing_provenance_only}&limit=${limit}&offset=${offset}`
  );
}

export async function fetchProvenance(changeId) {
  return apiFetch(`/changes/${changeId}/provenance`);
}

export async function linkDecisionToChange(changeId, decisionId) {
  return apiFetch(`/changes/${changeId}`, {
    method: "PATCH",
    body: JSON.stringify({ decision_id: decisionId }),
  });
}

export async function fetchAlternatives(decisionId) {
  return apiFetch(`/decisions/${decisionId}/alternatives`);
}

export async function fetchEvidence(decisionId) {
  return apiFetch(`/decisions/${decisionId}/evidence`);
}

export async function updateDecisionStatus(decisionId, status) {
  return apiFetch(`/decisions/${decisionId}`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

export async function fetchTimeline(projectId, { limit = 100 } = {}) {
  return apiFetch(`/projects/${projectId}/timeline?limit=${limit}`);
}

export async function fetchDecisions(projectId) {
  return apiFetch(`/projects/${projectId}/decisions`);
}

export async function ingestTranscript(payload) {
  return apiFetch("/interactions/ingest", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function ingestTranscriptBatch(payload) {
  return apiFetch("/interactions/ingest-batch", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
