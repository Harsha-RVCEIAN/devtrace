import React, { useEffect, useState } from "react";
import { Navbar } from "./components/Navbar";
import { Login } from "./pages/Login";
import { Projects } from "./pages/Projects";
import { ProjectWorkspace } from "./pages/ProjectWorkspace";
import { fetchCurrentUser, logout } from "./api/client";

export default function App() {
  const [user, setUser] = useState(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [workspaceProject, setWorkspaceProject] = useState(null);

  useEffect(() => {
    async function checkAuth() {
      try {
        const me = await fetchCurrentUser();
        setUser(me);
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
    setWorkspaceProject(null);
  };

  if (!authChecked) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-muted)" }}>
        Loading DevTrace...
      </div>
    );
  }

  if (!user) {
    return <Login onAuthSuccess={(loggedInUser) => setUser(loggedInUser)} />;
  }

  if (workspaceProject) {
    return (
      <ProjectWorkspace
        project={workspaceProject}
        currentUser={user}
        onBack={() => setWorkspaceProject(null)}
      />
    );
  }

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <Navbar user={user} onLogout={handleLogout} />
      <main style={{ flex: 1 }}>
        <Projects user={user} onOpenWorkspace={(p) => setWorkspaceProject(p)} />
      </main>
    </div>
  );
}
