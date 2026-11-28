import React, { useEffect, useState } from "react";
import { Navbar } from "./components/Navbar";
import { CandidateStudio } from "./pages/CandidateStudio";
import { Login } from "./pages/Login";
import { Projects } from "./pages/Projects";
import { ProjectWorkspace } from "./pages/ProjectWorkspace";
import { fetchCurrentUser, logout } from "./api/client";

export default function App() {
  const [user, setUser] = useState(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [activeTab, setActiveTab] = useState("projects");
  const [offlineNlpMode, setOfflineNlpMode] = useState(false);
  const [workspaceProject, setWorkspaceProject] = useState(null);

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
    await logout().catch(() => { });
    setUser(null);
    setOfflineNlpMode(false);
    setWorkspaceProject(null);
  };

  const openWorkspace = (project) => {
    setWorkspaceProject(project);
  };

  const closeWorkspace = () => {
    setWorkspaceProject(null);
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

  // Workspace view replaces everything when a project is open
  if (workspaceProject && user) {
    return (
      <ProjectWorkspace
        project={workspaceProject}
        currentUser={user}
        onBack={closeWorkspace}
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
        {activeTab === "projects" && user && (
          <Projects user={user} onOpenWorkspace={openWorkspace} />
        )}
        {activeTab === "nlp" && <CandidateStudio />}
      </main>
    </div>
  );
}
