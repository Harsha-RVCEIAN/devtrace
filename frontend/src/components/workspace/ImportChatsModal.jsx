import React, { useState } from "react";
import { Upload, Sparkles, X, FileText, Zap } from "lucide-react";
import { ingestTranscriptBatch } from "../../api/client";

const TEST_CONVERSATIONS = [
  {
    tool_name: "ChatGPT",
    model_name: "gpt-4o",
    turns: [
      {
        prompt:
          "For CampusCart auth in app/auth/session_store.py, should we stick with JWT in localStorage or switch to Redis server sessions or cookie-based signed tokens?",
        response:
          "JWT in localStorage is vulnerable to XSS and hard to revoke on logout. Redis server sessions with HttpOnly cookies let you invalidate sessions immediately.",
      },
      {
        prompt:
          "Yeah true, let's drop JWT and use Redis server sessions instead because users must be logged out immediately when they revoke a device.",
        response:
          "Makes sense. Storing sessions in Redis with an HttpOnly cookie handles immediate revocation cleanly.",
      },
    ],
  },
  {
    tool_name: "Claude",
    model_name: "claude-3.5-sonnet",
    turns: [
      {
        prompt:
          "We are starting the schema in app/db/order_models.py. Should we use MongoDB or PostgreSQL or DynamoDB?",
        response:
          "PostgreSQL gives you ACID transactions and foreign keys that prevent orphan orders.",
      },
      {
        prompt:
          "Agreed, let's go with PostgreSQL rather than MongoDB since we need strong ACID transactions and foreign key constraints.",
        response: "Great choice for relational order integrity.",
      },
    ],
  },
  {
    tool_name: "Cursor",
    model_name: "claude-3.5-sonnet",
    turns: [
      {
        prompt:
          "GET /listings in app/api/listings.py is slowing down past page 50. Should we keep OFFSET pagination or move to cursor-based pagination?",
        response:
          "OFFSET scans all preceding rows on deep pages and can duplicate items.",
      },
      {
        prompt:
          "Okay, let's use cursor-based pagination instead of OFFSET pagination because deep pages are scanning too many rows.",
        response: "Cursor pagination keyed on (created_at, listing_id) keeps latency constant.",
      },
    ],
  },
  {
    tool_name: "ChatGPT",
    model_name: "gpt-4o-mini",
    turns: [
      {
        prompt:
          "Wait why is uvicorn throwing Address already in use on port 8000 when I start the server?",
        response:
          "Another process is already bound to port 8000. Start uvicorn with --port 8001.",
      },
      {
        prompt: "Oh nice, killed the old process and updated the typo in README.md.",
        response: "Glad that fixed it!",
      },
    ],
  },
];

export function ImportChatsModal({ projectId, onClose, onIngested }) {
  const [rawText, setRawText] = useState("");
  const [fileName, setFileName] = useState("");
  const [toolName, setToolName] = useState("AI Chat");
  const [engine, setEngine] = useState("rules");
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

  const handleFileChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setFileName(file.name);
    setRawText(await file.text());
    setErrorMsg(null);
  };

  const runBatch = async (payload) => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const res = await ingestTranscriptBatch({
        project_id: projectId,
        engine,
        auto_link: true,
        auto_approve: true,
        ...payload,
      });
      if (onIngested) onIngested(res);
      onClose();
    } catch (err) {
      setErrorMsg(err.message || "Failed to import AI chats.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.65)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "20px",
        zIndex: 1000,
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget && !loading) onClose();
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: "620px",
          background: "var(--bg-surface)",
          border: "1px solid var(--border-strong)",
          borderRadius: "10px",
          padding: "22px",
          display: "flex",
          flexDirection: "column",
          gap: "14px",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <h2 style={{ fontSize: "16px", fontWeight: 700 }}>Import AI Conversations</h2>
            <p style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "2px" }}>
              Upload a full ChatGPT export (<code>conversations.json</code>), JSON array, or Markdown transcript—decisions are auto-extracted and linked to matching repository files.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={loading}
            style={{ background: "transparent", border: "none", color: "var(--text-muted)", cursor: "pointer" }}
          >
            <X size={18} />
          </button>
        </div>

        {/* One-click batch import for testing */}
        <div
          style={{
            padding: "12px",
            borderRadius: "6px",
            background: "rgba(99,102,241,0.08)",
            border: "1px solid rgba(99,102,241,0.28)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "10px",
            flexWrap: "wrap",
          }}
        >
          <div style={{ fontSize: "12px" }}>
            <div style={{ fontWeight: 600, color: "var(--text-main)" }}>Testing on CampusCart?</div>
            <div style={{ color: "var(--text-secondary)" }}>
              Batch-import all 4 realistic test chats (Auth, DB, Pagination, + Debugging noise) at once.
            </div>
          </div>
          <button
            type="button"
            disabled={loading}
            onClick={() => runBatch({ conversations: TEST_CONVERSATIONS })}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              padding: "7px 12px",
              borderRadius: "5px",
              border: "none",
              background: "var(--color-primary)",
              color: "#fff",
              fontSize: "12px",
              fontWeight: 600,
              cursor: loading ? "wait" : "pointer",
            }}
          >
            <Zap size={13} />
            {loading ? "Importing..." : "Auto-Import Test Chats"}
          </button>
        </div>

        <div style={{ display: "flex", gap: "10px", alignItems: "center", flexWrap: "wrap" }}>
          <label
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              padding: "7px 12px",
              borderRadius: "5px",
              border: "1px solid var(--border-strong)",
              background: "var(--bg-surface-elevated)",
              color: "var(--text-main)",
              fontSize: "12px",
              fontWeight: 500,
              cursor: "pointer",
            }}
          >
            <Upload size={14} />
            Choose .json / .md / .txt
            <input type="file" accept=".json,.md,.txt,.log" onChange={handleFileChange} style={{ display: "none" }} />
          </label>
          {fileName && (
            <span style={{ display: "inline-flex", alignItems: "center", gap: "5px", fontSize: "12px", color: "#10b981" }}>
              <FileText size={13} />
              {fileName}
            </span>
          )}
          <div style={{ marginLeft: "auto", display: "flex", gap: "8px" }}>
            <input
              type="text"
              value={toolName}
              onChange={(e) => setToolName(e.target.value)}
              placeholder="Tool name"
              style={{ width: "110px", padding: "6px 8px", borderRadius: "4px", border: "1px solid var(--border-subtle)", background: "var(--bg-app)", color: "var(--text-main)", fontSize: "12px" }}
            />
            <select
              value={engine}
              onChange={(e) => setEngine(e.target.value)}
              style={{ padding: "6px 8px", borderRadius: "4px", border: "1px solid var(--border-subtle)", background: "var(--bg-app)", color: "var(--text-main)", fontSize: "12px" }}
            >
              <option value="rules">Rules</option>
              <option value="llm">Ollama LLM</option>
              <option value="auto">Auto</option>
            </select>
          </div>
        </div>

        <textarea
          rows={9}
          value={rawText}
          onChange={(e) => setRawText(e.target.value)}
          placeholder={"Or paste ChatGPT conversations.json / Markdown (separate multiple chats with ---):\n\nUser: Should we use PostgreSQL or MongoDB?\nAssistant: PostgreSQL gives ACID transactions.\nUser: Let's go with PostgreSQL."}
          className="font-mono"
          style={{
            width: "100%",
            background: "var(--bg-app)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "6px",
            padding: "10px",
            color: "var(--text-main)",
            fontSize: "12px",
            resize: "vertical",
          }}
        />

        {errorMsg && (
          <div style={{ padding: "8px 10px", borderRadius: "5px", background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)", color: "#f87171", fontSize: "12px" }}>
            {errorMsg}
          </div>
        )}

        <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px" }}>
          <button
            type="button"
            onClick={onClose}
            disabled={loading}
            style={{ padding: "8px 14px", borderRadius: "5px", border: "1px solid var(--border-subtle)", background: "transparent", color: "var(--text-secondary)", fontSize: "12px", cursor: "pointer" }}
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={loading || !rawText.trim()}
            onClick={() => runBatch({ raw_text: rawText, tool_name: toolName })}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              padding: "8px 16px",
              borderRadius: "5px",
              border: "none",
              background: "var(--color-primary)",
              color: "#fff",
              fontSize: "12px",
              fontWeight: 600,
              cursor: loading || !rawText.trim() ? "not-allowed" : "pointer",
              opacity: loading || !rawText.trim() ? 0.6 : 1,
            }}
          >
            <Sparkles size={13} />
            {loading ? "Processing..." : "Upload & Update Graph"}
          </button>
        </div>
      </div>
    </div>
  );
}
