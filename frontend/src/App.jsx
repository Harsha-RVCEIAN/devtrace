import React, { useEffect, useState } from "react";
import { Navbar } from "./components/Navbar";
import { CandidateStudio } from "./pages/CandidateStudio";
import { Login } from "./pages/Login";
import { Projects } from "./pages/Projects";
import { fetchCurrentUser, logout } from "./api/client";

export default function App() {
  const [user, setUser] = useState(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [activeTab, setActiveTab] = useState("projects");
  const [offlineNlpMode, setOfflineNlpMode] = useState(false);

  useEffect(() => {
    async function checkAuth() {
      try {
        const me = await fetchCurrentUser();
        setUser(me);
        if (me) setActiveTab("projects");
      } catch {
        setUser(null);
      } finally {
        setAuthChecked(true);
      }
    }
    checkAuth();
  }, []);

  const handleLogout = async () => {
    await logout().catch(() => {});
    setUser(null);
    setOfflineNlpMode(false);
  };

  if (!authChecked) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-muted)" }}>
        Loading DevTrace...
      </div>
    );
  }

  if (!user && !offlineNlpMode) {
    return (
      <Login
        onAuthSuccess={(loggedInUser) => {
          setUser(loggedInUser);
          setActiveTab("projects");
        }}
        onOpenNlpOffline={() => {
          setOfflineNlpMode(true);
          setActiveTab("nlp");
        }}
      />
    );
  }

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        user={user}
        onLogout={handleLogout}
        onBackToLogin={() => setOfflineNlpMode(false)}
      />
      <main style={{ flex: 1 }}>
        {activeTab === "projects" && user && <Projects user={user} />}
        {activeTab === "nlp" && <CandidateStudio />}
      </main>
    </div>
  );
}
