import React from "react";
import { FolderGit2, LogOut, Terminal } from "lucide-react";

export function Navbar({ user, onLogout }) {
  return (
    <header
      style={{
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
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "20px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <div
            style={{
              background: "var(--color-primary)",
              padding: "4px 6px",
              borderRadius: "4px",
              display: "flex",
              alignItems: "center",
            }}
          >
            <Terminal size={16} color="#fff" />
          </div>
          <span style={{ fontWeight: 700, fontSize: "16px", letterSpacing: "-0.02em" }}>
            DevTrace
          </span>
        </div>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "7px",
            padding: "5px 12px",
            borderRadius: "4px",
            background: "var(--bg-surface-elevated)",
            color: "var(--text-main)",
            fontWeight: 600,
            fontSize: "13px",
          }}
        >
          <FolderGit2 size={14} color="var(--color-primary)" />
          Projects
        </div>
      </div>

      {user && (
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          {user.avatar_url && (
            <img
              src={user.avatar_url}
              alt={user.name}
              style={{ width: "26px", height: "26px", borderRadius: "50%" }}
            />
          )}
          <div style={{ fontSize: "12px", textAlign: "right" }}>
            <div style={{ fontWeight: 600, color: "var(--text-main)" }}>{user.name}</div>
            {user.github_username && (
              <div className="font-mono" style={{ fontSize: "10px", color: "var(--text-muted)" }}>
                @{user.github_username}
              </div>
            )}
          </div>
          <button
            type="button"
            onClick={onLogout}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "5px",
              padding: "5px 10px",
              borderRadius: "4px",
              border: "1px solid var(--border-subtle)",
              background: "transparent",
              color: "var(--text-secondary)",
              fontSize: "12px",
              cursor: "pointer",
            }}
          >
            <LogOut size={13} />
            Sign out
          </button>
        </div>
      )}
    </header>
  );
}
