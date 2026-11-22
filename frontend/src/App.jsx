import React, { useState, useEffect } from "react";
import { Navbar } from "./components/Navbar";
import { Dashboard } from "./pages/Dashboard";
import { Decisions } from "./pages/Decisions";
import { Provenance } from "./pages/Provenance";
import { CandidateStudio } from "./pages/CandidateStudio";
import { Timeline } from "./components/Timeline";
import {
  fetchProjects,
  fetchSummary,
  fetchDecisions,
  fetchTimeline,
  fetchChanges,
} from "./api/client";

export default function App() {
  const [activeTab, setActiveTab] = useState("overview");
  const [projects, setProjects] = useState([]);
  const [currentProject, setCurrentProject] = useState(null);
  const [summary, setSummary] = useState({
    total_changes: 5,
    ai_exact_changes: 3,
    ai_inferred_changes: 1,
    human_changes: 1,
    missing_provenance: 1,
    uncommitted_changes: 0,
  });
  const [decisions, setDecisions] = useState([]);
  const [timelineEvents, setTimelineEvents] = useState([]);
  const [changes, setChanges] = useState([]);

  useEffect(() => {
    async function loadInitial() {
      const projs = await fetchProjects();
      setProjects(projs);
      if (projs.length > 0) {
        setCurrentProject(projs[0]);
      }
    }
    loadInitial();
  }, []);

  useEffect(() => {
    if (!currentProject) return;

    async function loadProjectData() {
      const pid = currentProject.project_id;
      const [sum, decs, tl, chgs] = await Promise.all([
        fetchSummary(pid),
        fetchDecisions(pid),
        fetchTimeline(pid),
        fetchChanges(pid),
      ]);
      setSummary(sum);
      setDecisions(decs);
      setTimelineEvents(tl);
      setChanges(chgs);
    }
    loadProjectData();
  }, [currentProject]);

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        projects={projects}
        currentProject={currentProject}
        setCurrentProject={setCurrentProject}
      />

      <main style={{ flex: 1 }}>
        {activeTab === "overview" && (
          <Dashboard project={currentProject} summary={summary} decisions={decisions} />
        )}

        {activeTab === "decisions" && (
          <Decisions decisions={decisions} />
        )}

        {activeTab === "timeline" && (
          <div style={{ maxWidth: "900px", margin: "0 auto", padding: "24px" }}>
            <div style={{ marginBottom: "20px" }}>
              <h1 style={{ fontSize: "20px", fontWeight: 700, marginBottom: "4px" }}>
                Project Activity Timeline
              </h1>
              <p style={{ color: "var(--text-secondary)", fontSize: "13px" }}>
                Chronological unified activity stream of commits, architectural decisions, and AI interactions.
              </p>
            </div>
            <Timeline events={timelineEvents} />
          </div>
        )}

        {activeTab === "provenance" && (
          <Provenance changes={changes} />
        )}

        {activeTab === "nlp" && (
          <CandidateStudio projectId={currentProject?.project_id} />
        )}
      </main>
    </div>
  );
}
