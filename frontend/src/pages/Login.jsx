import React, { useState } from "react";
import { Github, Mail, Terminal, ArrowRight } from "lucide-react";
import {
  getGitHubLoginUrl,
  getGoogleLoginUrl,
  loginWithEmail,
  registerWithEmail,
} from "../api/client";

function GoogleIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true">
      <path
        fill="#EA4335"
        d="M12 10.2v3.9h5.5c-.2 1.3-1.5 3.8-5.5 3.8-3.3 0-6-2.7-6-6s2.7-6 6-6c1.9 0 3.1.8 3.9 1.5l2.6-2.5C16.9 3.4 14.7 2.5 12 2.5 6.8 2.5 2.5 6.8 2.5 12s4.3 9.5 9.5 9.5c5.5 0 9.1-3.9 9.1-9.3 0-.6-.1-1.1-.2-1.6H12z"
      />
    </svg>
  );
}

export function Login({ onAuthSuccess }) {
  const [showEmailForm, setShowEmailForm] = useState(false);
  const [isRegister, setIsRegister] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleEmailSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const user = isRegister
        ? await registerWithEmail(name, email, password)
        : await loginWithEmail(email, password);
      onAuthSuccess(user);
    } catch (err) {
      setError(err.message || "Authentication failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "24px",
        background: "var(--bg-app)",
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: "400px",
          background: "var(--bg-surface)",
          border: "1px solid var(--border-subtle)",
          borderRadius: "10px",
          padding: "32px 28px",
        }}
      >
        {/* Brand */}
        <div style={{ textAlign: "center", marginBottom: "28px" }}>
          <div
            style={{
              width: "40px",
              height: "40px",
              borderRadius: "8px",
              background: "var(--color-primary)",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              marginBottom: "14px",
            }}
          >
            <Terminal size={20} color="#fff" />
          </div>
          <h1 style={{ fontSize: "22px", fontWeight: 700, letterSpacing: "-0.02em" }}>
            Log in to DevTrace
          </h1>
          <p style={{ color: "var(--text-secondary)", fontSize: "13px", marginTop: "6px" }}>
            Evidence-aware engineering provenance for your repositories.
          </p>
        </div>

        {/* Primary: Continue with GitHub */}
        <a
          href={getGitHubLoginUrl()}
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: "10px",
            width: "100%",
            padding: "11px 16px",
            borderRadius: "6px",
            background: "#f3f4f6",
            color: "#0c0e14",
            fontWeight: 600,
            fontSize: "14px",
            textDecoration: "none",
            marginBottom: "10px",
          }}
        >
          <Github size={18} />
          Continue with GitHub
        </a>

        {/* Secondary: Continue with Google */}
        <a
          href={getGoogleLoginUrl()}
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: "10px",
            width: "100%",
            padding: "10px 16px",
            borderRadius: "6px",
            background: "var(--bg-surface-elevated)",
            border: "1px solid var(--border-strong)",
            color: "var(--text-main)",
            fontWeight: 500,
            fontSize: "14px",
            textDecoration: "none",
          }}
        >
          <GoogleIcon />
          Continue with Google
        </a>

        {/* Divider */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "12px",
            margin: "22px 0 16px",
            color: "var(--text-muted)",
            fontSize: "12px",
          }}
        >
          <div style={{ flex: 1, height: "1px", background: "var(--border-subtle)" }} />
          <span>or</span>
          <div style={{ flex: 1, height: "1px", background: "var(--border-subtle)" }} />
        </div>

        {/* Last / unhighlighted: Email */}
        {!showEmailForm ? (
          <button
            type="button"
            onClick={() => setShowEmailForm(true)}
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "8px",
              width: "100%",
              padding: "9px 14px",
              borderRadius: "6px",
              background: "transparent",
              border: "1px solid var(--border-subtle)",
              color: "var(--text-secondary)",
              fontSize: "13px",
              cursor: "pointer",
            }}
          >
            <Mail size={14} />
            Continue with Email
          </button>
        ) : (
          <form onSubmit={handleEmailSubmit} style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {isRegister && (
              <input
                type="text"
                placeholder="Full name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                style={{
                  padding: "9px 12px",
                  borderRadius: "6px",
                  border: "1px solid var(--border-subtle)",
                  background: "var(--bg-app)",
                  color: "var(--text-main)",
                }}
              />
            )}
            <input
              type="email"
              placeholder="Email address"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              style={{
                padding: "9px 12px",
                borderRadius: "6px",
                border: "1px solid var(--border-subtle)",
                background: "var(--bg-app)",
                color: "var(--text-main)",
              }}
            />
            <input
              type="password"
              placeholder={isRegister ? "Password (min 8 chars)" : "Password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={isRegister ? 8 : 1}
              style={{
                padding: "9px 12px",
                borderRadius: "6px",
                border: "1px solid var(--border-subtle)",
                background: "var(--bg-app)",
                color: "var(--text-main)",
              }}
            />

            {error && (
              <div style={{ color: "var(--color-danger)", fontSize: "12px" }}>{error}</div>
            )}

            <button
              type="submit"
              disabled={loading}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "6px",
                padding: "9px 14px",
                borderRadius: "6px",
                border: "1px solid var(--border-strong)",
                background: "var(--bg-surface-elevated)",
                color: "var(--text-main)",
                fontWeight: 500,
                cursor: "pointer",
              }}
            >
              {loading ? "Signing in..." : isRegister ? "Create account" : "Sign in with Email"}
              <ArrowRight size={14} />
            </button>

            <button
              type="button"
              onClick={() => {
                setIsRegister((v) => !v);
                setError(null);
              }}
              style={{
                background: "transparent",
                border: "none",
                color: "var(--text-muted)",
                fontSize: "12px",
                cursor: "pointer",
                marginTop: "4px",
              }}
            >
              {isRegister ? "Already have an account? Sign in" : "Need an account? Sign up with email"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
