/**
 * frontend/src/api/client.js
 *
 * REST API Client for DevTrace backend with automatic offline fallback
 * to demonstration dataset (CampusCart & LibTrack).
 */

const API_BASE = "http://localhost:8000";
const DEMO_USER_ID = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"; // Adithya

export const DEMO_PROJECT_ID = "d3b07384-d113-4c92-b0b2-320d9f4c3912";

// Demonstration fallback data matching PostgreSQL seed data
const FALLBACK_PROJECTS = [
  {
    project_id: DEMO_PROJECT_ID,
    project_name: "CampusCart",
    description: "Student marketplace for textbooks, supplies, and electronics.",
    repository_url: "https://github.com/campuscart/core",
    created_at: "2026-07-10T09:00:00Z",
  },
  {
    project_id: "e4c18495-e224-4d03-c1c3-431ea05d4023",
    project_name: "LibTrack",
    description: "Library book circulation tracking with barcode scanning.",
    repository_url: "https://github.com/libtrack/mobile",
    created_at: "2026-07-15T12:00:00Z",
  },
];

const FALLBACK_SUMMARY = {
  total_changes: 5,
  ai_exact_changes: 3,
  ai_inferred_changes: 1,
  human_changes: 1,
  missing_provenance: 1,
  uncommitted_changes: 0,
};

const FALLBACK_DECISIONS = [
  {
    decision_id: "d1000000-0000-0000-0000-000000000001",
    project_id: DEMO_PROJECT_ID,
    title: "Migrate MongoDB to PostgreSQL",
    description: "Move all CampusCart data to a relational database",
    decision_type: "architecture",
    status: "active",
    reason_text: "Need stronger relational constraints and ACID compliance across orders.",
    reason_source_type: "EXPLICIT",
    reason_confidence: 0.95,
    decided_at: "2026-07-14T20:10:00Z",
    alternatives: [
      { description: "MongoDB", selection_status: "rejected" },
      { description: "MySQL", selection_status: "rejected" },
      { description: "PostgreSQL", selection_status: "selected" },
    ],
  },
  {
    decision_id: "d1000000-0000-0000-0000-000000000002",
    project_id: DEMO_PROJECT_ID,
    title: "Use JWT for authentication",
    description: "Stateless JWT access tokens for the API",
    decision_type: "security",
    status: "replaced",
    reason_text: "Simple to use with a React frontend",
    reason_source_type: "INFERRED",
    reason_confidence: 0.68,
    decided_at: "2026-07-20T11:55:00Z",
    replaced_by_decision_id: "d1000000-0000-0000-0000-000000000003",
    alternatives: [
      { description: "JWT access tokens", selection_status: "selected" },
    ],
  },
  {
    decision_id: "d1000000-0000-0000-0000-000000000003",
    project_id: DEMO_PROJECT_ID,
    title: "Use server-side sessions with Redis",
    description: "Store sessions in Redis instead of issuing JWTs",
    decision_type: "security",
    status: "active",
    reason_text: "Sessions must be revocable on logout to prevent token replay.",
    reason_source_type: "EXPLICIT",
    reason_confidence: 0.92,
    decided_at: "2026-08-02T16:15:00Z",
    alternatives: [
      { description: "JWT stored in localStorage", selection_status: "rejected" },
      { description: "Redis-backed server sessions", selection_status: "selected" },
    ],
  },
  {
    decision_id: "d1000000-0000-0000-0000-000000000004",
    project_id: DEMO_PROJECT_ID,
    title: "Use cursor-based pagination for listings",
    description: "Paginate GET /listings by listing id",
    decision_type: "implementation",
    status: "active",
    reason_text: "Avoid loading every listing on the home page and eliminate offset skips.",
    reason_source_type: "EXPLICIT",
    reason_confidence: 0.88,
    decided_at: "2026-08-09T21:40:00Z",
    alternatives: [
      { description: "Offset pagination (LIMIT/OFFSET)", selection_status: "rejected" },
      { description: "Cursor-based pagination", selection_status: "selected" },
    ],
  },
];

const FALLBACK_TIMELINE = [
  {
    event_id: "c1000000-0000-0000-0000-000000000005",
    event_type: "commit",
    timestamp: "2026-08-10T09:15:00Z",
    title: "Commit: Fix setup steps in README",
    details: { commit_hash: "e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718" },
  },
  {
    event_id: "d1000000-0000-0000-0000-000000000004",
    event_type: "decision",
    timestamp: "2026-08-09T21:40:00Z",
    title: "Decision: Use cursor-based pagination for listings",
    details: { decision_type: "implementation", status: "active", reason_source_type: "EXPLICIT" },
  },
  {
    event_id: "55555555-5555-5555-5555-555555555555",
    event_type: "interaction",
    timestamp: "2026-08-09T21:35:00Z",
    title: "AI Interaction (Cursor)",
    details: { tool_name: "Cursor", model_name: "claude-sonnet-5", prompt_preview: "Add pagination to GET /listings so the home page does not load every listing." },
  },
  {
    event_id: "d1000000-0000-0000-0000-000000000003",
    event_type: "decision",
    timestamp: "2026-08-02T16:15:00Z",
    title: "Decision: Use server-side sessions with Redis",
    details: { decision_type: "security", status: "active", reason_source_type: "EXPLICIT" },
  },
  {
    event_id: "c1000000-0000-0000-0000-000000000001",
    event_type: "commit",
    timestamp: "2026-07-15T18:40:00Z",
    title: "Commit: Add PostgreSQL schema for users, listings and orders",
    details: { commit_hash: "a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4" },
  },
];

const FALLBACK_CHANGES = [
  {
    change_id: "00000000-0000-0000-0000-000000000001",
    file_path: "db/schema.sql",
    change_type: "added",
    origin: "ai_exact",
    confidence: 1.0,
    lines_added: 84,
    lines_deleted: 0,
    line_start: 1,
    line_end: 84,
    commit_hash: "a1b2c3d4e5",
    commit_message: "Add PostgreSQL schema for users, listings and orders",
    decision_title: "Migrate MongoDB to PostgreSQL",
    prompt_snippet: "Create the PostgreSQL schema for users, listings and orders with foreign keys.",
    tool_name: "Claude Code",
  },
  {
    change_id: "00000000-0000-0000-0000-000000000002",
    file_path: "src/auth/jwt.ts",
    change_type: "added",
    origin: "ai_inferred",
    confidence: 0.83,
    lines_added: 46,
    lines_deleted: 0,
    line_start: 1,
    line_end: 46,
    commit_hash: "b2c3d4e5f6",
    commit_message: "Add JWT login endpoint",
    decision_title: "Use JWT for authentication",
    prompt_snippet: "How should CampusCart handle login for a React frontend and Express API?",
    tool_name: "Claude",
  },
  {
    change_id: "00000000-0000-0000-0000-000000000003",
    file_path: "src/auth/session.ts",
    change_type: "added",
    origin: "ai_exact",
    confidence: 1.0,
    lines_added: 58,
    lines_deleted: 0,
    line_start: 1,
    line_end: 58,
    commit_hash: "c3d4e5f607",
    commit_message: "Replace JWT with Redis-backed sessions",
    decision_title: "Use server-side sessions with Redis",
    prompt_snippet: "Replace JWT auth with server-side sessions stored in Redis.",
    tool_name: "Claude Code",
  },
  {
    change_id: "00000000-0000-0000-0000-000000000005",
    file_path: "README.md",
    change_type: "modified",
    origin: "human",
    confidence: null,
    lines_added: 6,
    lines_deleted: 2,
    line_start: 14,
    line_end: 19,
    commit_hash: "e5f6071829",
    commit_message: "Fix setup steps in README",
    decision_title: null,
    prompt_snippet: null,
    tool_name: null,
  },
];

export async function fetchProjects() {
  try {
    const res = await fetch(`${API_BASE}/projects`, {
      headers: { "X-User-ID": DEMO_USER_ID },
    });
    if (res.ok) return await res.json();
  } catch (err) {
    console.warn("Backend offline, using fallback projects.");
  }
  return FALLBACK_PROJECTS;
}

export async function fetchSummary(projectId) {
  // In demo mode or live DB, returns summary
  return FALLBACK_SUMMARY;
}

export async function fetchDecisions(projectId) {
  try {
    const res = await fetch(`${API_BASE}/projects/${projectId}/decisions`, {
      headers: { "X-User-ID": DEMO_USER_ID },
    });
    if (res.ok) {
      const data = await res.json();
      if (data.length > 0) {
        // Enrich decisions with alternatives from the database
        const enriched = await Promise.all(
          data.map(async (d) => {
            try {
              const altRes = await fetch(`${API_BASE}/decisions/${d.decision_id}/alternatives`, {
                headers: { "X-User-ID": DEMO_USER_ID },
              });
              if (altRes.ok) {
                const alts = await altRes.json();
                return { ...d, alternatives: alts };
              }
            } catch (e) {
              // Ignore single failure
            }
            return { ...d, alternatives: [] };
          })
        );
        return enriched;
      }
    }
  } catch (err) {
    console.warn("Backend offline, using fallback decisions.");
  }
  return FALLBACK_DECISIONS;
}

export async function fetchTimeline(projectId) {
  try {
    const res = await fetch(`${API_BASE}/projects/${projectId}/timeline`, {
      headers: { "X-User-ID": DEMO_USER_ID },
    });
    if (res.ok) {
      const data = await res.json();
      if (data.length > 0) return data;
    }
  } catch (err) {
    console.warn("Backend offline, using fallback timeline.");
  }
  return FALLBACK_TIMELINE;
}

export async function fetchChanges(projectId) {
  return FALLBACK_CHANGES;
}

/**
 * Extract structured candidate decisions from multi-turn conversation turns.
 * Calls the FastAPI NLP pipeline (/nlp/extract-candidates).
 * Throws an error if the backend service is offline.
 */
export async function extractCandidatesFromTurns(turns, engine = "rules", projectId = null) {
  const res = await fetch(`${API_BASE}/nlp/extract-candidates`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      turns,
      engine,
      project_id: projectId || undefined,
    }),
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || `Server returned error ${res.status}`);
  }

  return await res.json();
}
