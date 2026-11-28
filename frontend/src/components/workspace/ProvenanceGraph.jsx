import React, { useEffect, useMemo, useState } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  MarkerType,
  Handle,
  Position,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import {
  Folder,
  FileCode2,
  GitBranch,
  GitCommit,
  Bot,
  Link2,
  CheckCircle2,
  XCircle,
  HelpCircle,
  X,
} from "lucide-react";
import {
  fetchAlternatives,
  fetchEvidence,
  fetchProvenance,
  linkDecisionToChange,
} from "../../api/client";
import { OriginBadge, fmtDate, fmtDateTime, statusColor } from "./shared";

function ModuleNode({ data }) {
  return (
    <div
      style={{
        background: "#161b26",
        border: `1.5px solid ${data.selected ? "#6366f1" : "#2d3548"}`,
        borderRadius: "8px",
        padding: "10px 14px",
        minWidth: "200px",
        color: "#f3f4f6",
        boxShadow: data.selected ? "0 0 0 2px rgba(99,102,241,0.35)" : "0 4px 12px rgba(0,0,0,0.3)",
      }}
    >
      <Handle type="source" position={Position.Right} style={{ background: "#6366f1", width: 7, height: 7 }} />
      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
        <Folder size={15} color="#818cf8" />
        <span className="font-mono" style={{ fontSize: "12px", fontWeight: 700 }}>
          {data.label}
        </span>
      </div>
      <div style={{ fontSize: "11px", color: "#9ca3af", marginTop: "4px" }}>
        {data.fileCount} file{data.fileCount !== 1 ? "s" : ""} · {data.linkedCount} linked
      </div>
    </div>
  );
}

function FileNode({ data }) {
  const hasDecision = Boolean(data.change?.decision);
  const borderColor = data.selected
    ? "#6366f1"
    : hasDecision
    ? "rgba(16,185,129,0.55)"
    : "rgba(245,158,11,0.4)";

  return (
    <div
      style={{
        background: "#111520",
        border: `1.5px solid ${borderColor}`,
        borderRadius: "8px",
        padding: "9px 12px",
        width: "245px",
        color: "#f3f4f6",
        boxShadow: data.selected ? "0 0 0 2px rgba(99,102,241,0.35)" : "0 4px 10px rgba(0,0,0,0.28)",
      }}
    >
      <Handle type="target" position={Position.Left} style={{ background: "#64748b", width: 7, height: 7 }} />
      <Handle type="source" position={Position.Right} style={{ background: hasDecision ? "#10b981" : "#f59e0b", width: 7, height: 7 }} />
      <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "5px" }}>
        <FileCode2 size={13} color={hasDecision ? "#34d399" : "#fbbf24"} style={{ flexShrink: 0 }} />
        <span
          className="font-mono"
          style={{
            fontSize: "11px",
            fontWeight: 600,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {data.fileName}
        </span>
      </div>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "6px" }}>
        <OriginBadge origin={data.change.origin} />
        <span className="font-mono" style={{ fontSize: "10px", color: "#9ca3af" }}>
          +{data.change.lines_added ?? 0} −{data.change.lines_deleted ?? 0}
        </span>
      </div>
    </div>
  );
}

function DecisionNode({ data }) {
  const d = data.decision;
  const col = statusColor(d.status);
  return (
    <div
      style={{
        background: "#151a28",
        border: `1.5px solid ${data.selected ? "#818cf8" : col}`,
        borderRadius: "8px",
        padding: "10px 13px",
        width: "260px",
        color: "#f3f4f6",
        boxShadow: data.selected ? "0 0 0 2px rgba(99,102,241,0.4)" : "0 6px 14px rgba(0,0,0,0.32)",
      }}
    >
      <Handle type="target" position={Position.Left} style={{ background: col, width: 7, height: 7 }} />
      <Handle type="source" position={Position.Right} style={{ background: col, width: 7, height: 7 }} />
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "6px", marginBottom: "4px" }}>
        <span style={{ display: "inline-flex", alignItems: "center", gap: "5px", fontSize: "10px", fontWeight: 700, color: col, textTransform: "uppercase" }}>
          <GitBranch size={11} />
          {d.decision_type} · {d.status}
        </span>
        {data.linkedFilesCount > 0 && (
          <span className="font-mono" style={{ fontSize: "10px", color: "#9ca3af" }}>
            {data.linkedFilesCount} file{data.linkedFilesCount !== 1 ? "s" : ""}
          </span>
        )}
      </div>
      <div style={{ fontSize: "12px", fontWeight: 600, lineHeight: 1.35 }}>
        {d.title}
      </div>
      {d.reason_text && (
        <div
          style={{
            fontSize: "11px",
            color: "#9ca3af",
            marginTop: "5px",
            overflow: "hidden",
            display: "-webkit-box",
            WebkitLineClamp: 2,
            WebkitBoxOrient: "vertical",
          }}
        >
          {d.reason_text}
        </div>
      )}
    </div>
  );
}

const NODE_TYPES = {
  moduleNode: ModuleNode,
  fileNode: FileNode,
  decisionNode: DecisionNode,
};

function getFolder(filePath) {
  const idx = filePath.lastIndexOf("/");
  return idx > 0 ? filePath.slice(0, idx) + "/" : "(root)";
}

function getBaseName(filePath) {
  const idx = filePath.lastIndexOf("/");
  return idx >= 0 ? filePath.slice(idx + 1) : filePath;
}

export function ProvenanceGraph({
  commits,
  codeChanges,
  decisions,
  onChangeLinked,
}) {
  const [lens, setLens] = useState("files"); // "files" | "decisions"
  const [selectedItem, setSelectedItem] = useState(null); // { type: "file"|"decision"|"module", id, payload }
  const [provenance, setProvenance] = useState(null);
  const [alts, setAlts] = useState([]);
  const [evidence, setEvidence] = useState([]);
  const [detailLoading, setDetailLoading] = useState(false);
  const [linkTargetId, setLinkTargetId] = useState("");
  const [linking, setLinking] = useState(false);

  const visibleDecisions = useMemo(
    () => decisions.filter((d) => d.status !== "rejected"),
    [decisions]
  );

  // Deduplicate code changes by file_path (keep latest change per file for clean GitDiagram map)
  const latestChangesByFile = useMemo(() => {
    const map = new Map();
    for (const ch of codeChanges) {
      const prev = map.get(ch.file_path);
      if (!prev || new Date(ch.changed_at) >= new Date(prev.changed_at)) {
        map.set(ch.file_path, ch);
      }
    }
    return Array.from(map.values());
  }, [codeChanges]);

  const { nodes, edges } = useMemo(() => {
    const builtNodes = [];
    const builtEdges = [];
    const decById = Object.fromEntries(visibleDecisions.map((d) => [d.decision_id, d]));

    if (lens === "files") {
      const folderGroups = new Map();
      for (const ch of latestChangesByFile) {
        const folder = getFolder(ch.file_path);
        if (!folderGroups.has(folder)) folderGroups.set(folder, []);
        folderGroups.get(folder).push(ch);
      }

      let fileRowY = 0;
      const connectedDecisionIds = new Set();

      Array.from(folderGroups.entries()).forEach(([folder, files]) => {
        const startY = fileRowY;
        const linkedCount = files.filter((f) => Boolean(f.decision)).length;

        files.forEach((ch) => {
          const fileNodeId = `file-${ch.change_id}`;
          builtNodes.push({
            id: fileNodeId,
            type: "fileNode",
            position: { x: 280, y: fileRowY },
            data: {
              fileName: getBaseName(ch.file_path),
              change: ch,
              selected: selectedItem?.type === "file" && selectedItem.id === ch.change_id,
            },
          });

          builtEdges.push({
            id: `e-mod-${folder}-${ch.change_id}`,
            source: `mod-${folder}`,
            target: fileNodeId,
            style: { stroke: "#363d52", strokeWidth: 1.5 },
          });

          if (ch.decision?.decision_id && decById[ch.decision.decision_id]) {
            connectedDecisionIds.add(ch.decision.decision_id);
            builtEdges.push({
              id: `e-file-dec-${ch.change_id}-${ch.decision.decision_id}`,
              source: fileNodeId,
              target: `dec-${ch.decision.decision_id}`,
              animated: true,
              markerEnd: { type: MarkerType.ArrowClosed, color: "#10b981" },
              style: { stroke: "#10b981", strokeWidth: 1.8 },
            });
          }

          fileRowY += 86;
        });

        const midY = startY + ((files.length - 1) * 86) / 2;
        builtNodes.push({
          id: `mod-${folder}`,
          type: "moduleNode",
          position: { x: 20, y: midY },
          data: {
            label: folder,
            fileCount: files.length,
            linkedCount,
            selected: selectedItem?.type === "module" && selectedItem.id === folder,
          },
        });

        fileRowY += 28;
      });

      // Place decisions on the right column (linked first, then standalone decisions)
      const orderedDecisions = [
        ...visibleDecisions.filter((d) => connectedDecisionIds.has(d.decision_id)),
        ...visibleDecisions.filter((d) => !connectedDecisionIds.has(d.decision_id)),
      ];

      orderedDecisions.forEach((d, idx) => {
        const linkedFilesCount = latestChangesByFile.filter(
          (c) => c.decision?.decision_id === d.decision_id
        ).length;
        builtNodes.push({
          id: `dec-${d.decision_id}`,
          type: "decisionNode",
          position: { x: 620, y: idx * 125 },
          data: {
            decision: d,
            linkedFilesCount,
            selected: selectedItem?.type === "decision" && selectedItem.id === d.decision_id,
          },
        });

        if (d.replaced_by_decision_id && decById[d.replaced_by_decision_id]) {
          builtEdges.push({
            id: `e-rep-${d.decision_id}`,
            source: `dec-${d.decision_id}`,
            target: `dec-${d.replaced_by_decision_id}`,
            label: "replaced by",
            labelStyle: { fill: "#9ca3af", fontSize: 10 },
            style: { stroke: "#6b7280", strokeDasharray: "5 4", strokeWidth: 1.5 },
            markerEnd: { type: MarkerType.ArrowClosed, color: "#6b7280" },
          });
        }
      });
    } else {
      // Decision Evolution Lens: Decisions -> Linked Files
      let rowY = 0;
      visibleDecisions.forEach((d) => {
        const linkedFiles = latestChangesByFile.filter(
          (c) => c.decision?.decision_id === d.decision_id
        );
        const startY = rowY;

        linkedFiles.forEach((ch) => {
          const fNodeId = `file-${ch.change_id}`;
          builtNodes.push({
            id: fNodeId,
            type: "fileNode",
            position: { x: 380, y: rowY },
            data: {
              fileName: ch.file_path,
              change: ch,
              selected: selectedItem?.type === "file" && selectedItem.id === ch.change_id,
            },
          });
          builtEdges.push({
            id: `e-d-f-${d.decision_id}-${ch.change_id}`,
            source: `dec-${d.decision_id}`,
            target: fNodeId,
            animated: true,
            style: { stroke: "#6366f1", strokeWidth: 1.6 },
            markerEnd: { type: MarkerType.ArrowClosed, color: "#6366f1" },
          });
          rowY += 84;
        });

        if (linkedFiles.length === 0) {
          rowY += 125;
        } else {
          rowY += 36;
        }

        const decY =
          linkedFiles.length > 0 ? startY + ((linkedFiles.length - 1) * 84) / 2 : startY;

        builtNodes.push({
          id: `dec-${d.decision_id}`,
          type: "decisionNode",
          position: { x: 30, y: decY },
          data: {
            decision: d,
            linkedFilesCount: linkedFiles.length,
            selected: selectedItem?.type === "decision" && selectedItem.id === d.decision_id,
          },
        });

        if (d.replaced_by_decision_id && decById[d.replaced_by_decision_id]) {
          builtEdges.push({
            id: `e-rep-${d.decision_id}`,
            source: `dec-${d.decision_id}`,
            target: `dec-${d.replaced_by_decision_id}`,
            label: "replaced by",
            labelStyle: { fill: "#9ca3af", fontSize: 10 },
            style: { stroke: "#6b7280", strokeDasharray: "5 4", strokeWidth: 1.5 },
            markerEnd: { type: MarkerType.ArrowClosed, color: "#6b7280" },
          });
        }
      });
    }

    return { nodes: builtNodes, edges: builtEdges };
  }, [lens, latestChangesByFile, visibleDecisions, selectedItem]);

  // Load deep provenance or decision details when a node is clicked
  useEffect(() => {
    if (!selectedItem) return;
    let cancelled = false;

    async function loadDetail() {
      setDetailLoading(true);
      try {
        if (selectedItem.type === "file") {
          const p = await fetchProvenance(selectedItem.id);
          if (cancelled) return;
          setProvenance(p);
          setLinkTargetId(p?.decision?.decision_id || "");
          if (p?.decision?.decision_id) {
            const [a, e] = await Promise.all([
              fetchAlternatives(p.decision.decision_id).catch(() => []),
              fetchEvidence(p.decision.decision_id).catch(() => []),
            ]);
            if (!cancelled) {
              setAlts(a);
              setEvidence(e);
            }
          } else {
            setAlts([]);
            setEvidence([]);
          }
        } else if (selectedItem.type === "decision") {
          const [a, e] = await Promise.all([
            fetchAlternatives(selectedItem.id).catch(() => []),
            fetchEvidence(selectedItem.id).catch(() => []),
          ]);
          if (!cancelled) {
            setAlts(a);
            setEvidence(e);
            setProvenance(null);
            setLinkTargetId("");
          }
        }
      } finally {
        if (!cancelled) setDetailLoading(false);
      }
    }

    loadDetail();
    return () => {
      cancelled = true;
    };
  }, [selectedItem?.type, selectedItem?.id]);

  const handleNodeClick = (_evt, node) => {
    if (node.id.startsWith("file-")) {
      const ch = node.data.change;
      setSelectedItem({ type: "file", id: ch.change_id, payload: ch });
    } else if (node.id.startsWith("dec-")) {
      const d = node.data.decision;
      setSelectedItem({ type: "decision", id: d.decision_id, payload: d });
    } else if (node.id.startsWith("mod-")) {
      setSelectedItem({ type: "module", id: node.data.label, payload: node.data.label });
    }
  };

  const handleLinkFileToDecision = async (changeId, decisionIdOrNull) => {
    setLinking(true);
    try {
      const updated = await linkDecisionToChange(changeId, decisionIdOrNull);
      if (onChangeLinked) onChangeLinked(updated);
      if (selectedItem?.type === "file") {
        setProvenance(updated);
      }
    } finally {
      setLinking(false);
    }
  };

  const emptyGraph = latestChangesByFile.length === 0 && visibleDecisions.length === 0;

  return (
    <div style={{ display: "grid", gridTemplateColumns: selectedItem ? "1fr 390px" : "1fr", gap: "16px", height: "640px" }}>
      {/* Interactive React Flow Canvas */}
      <div
        style={{
          position: "relative",
          background: "#0a0d14",
          border: "1px solid var(--border-subtle)",
          borderRadius: "8px",
          overflow: "hidden",
        }}
      >
        {/* Top-left Lens Switcher */}
        <div
          style={{
            position: "absolute",
            top: 12,
            left: 12,
            zIndex: 10,
            display: "flex",
            gap: "4px",
            background: "var(--bg-surface)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "6px",
            padding: "4px",
          }}
        >
          <button
            type="button"
            onClick={() => setLens("files")}
            style={{
              padding: "5px 10px",
              borderRadius: "4px",
              border: "none",
              background: lens === "files" ? "var(--color-primary)" : "transparent",
              color: lens === "files" ? "#fff" : "var(--text-secondary)",
              fontSize: "12px",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            File &amp; Module Map
          </button>
          <button
            type="button"
            onClick={() => setLens("decisions")}
            style={{
              padding: "5px 10px",
              borderRadius: "4px",
              border: "none",
              background: lens === "decisions" ? "var(--color-primary)" : "transparent",
              color: lens === "decisions" ? "#fff" : "var(--text-secondary)",
              fontSize: "12px",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Decision Evolution
          </button>
        </div>

        {/* Legend */}
        <div
          style={{
            position: "absolute",
            bottom: 12,
            left: 12,
            zIndex: 10,
            display: "flex",
            gap: "12px",
            background: "rgba(20, 23, 33, 0.9)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "6px",
            padding: "6px 10px",
            fontSize: "11px",
            color: "var(--text-secondary)",
          }}
        >
          <span><span style={{ color: "#10b981" }}>●</span> Linked / Active</span>
          <span><span style={{ color: "#f59e0b" }}>●</span> Unlinked File</span>
          <span>Click any node to inspect</span>
        </div>

        {emptyGraph ? (
          <div style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-muted)", fontSize: "13px" }}>
            No commits or decisions yet. Sync GitHub or click &ldquo;Import AI Chats&rdquo; above.
          </div>
        ) : (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={NODE_TYPES}
            onNodeClick={handleNodeClick}
            fitView
            fitViewOptions={{ padding: 0.2 }}
            minZoom={0.25}
            maxZoom={1.8}
          >
            <Background color="#1e2433" gap={20} />
            <Controls />
            <MiniMap
              nodeColor="#2d3548"
              maskColor="rgba(12, 14, 20, 0.7)"
              style={{ background: "#141721", border: "1px solid #242938" }}
            />
          </ReactFlow>
        )}
      </div>

      {/* Right Slide-in Inspector Drawer */}
      {selectedItem && (
        <aside
          style={{
            background: "var(--bg-surface)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "8px",
            padding: "16px",
            overflowY: "auto",
            display: "flex",
            flexDirection: "column",
            gap: "14px",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: "11px", fontWeight: 700, color: "var(--color-primary)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
              {selectedItem.type === "file"
                ? "File Provenance"
                : selectedItem.type === "decision"
                ? "Decision Details"
                : "Module Files"}
            </span>
            <button
              type="button"
              onClick={() => setSelectedItem(null)}
              style={{ background: "transparent", border: "none", color: "var(--text-muted)", cursor: "pointer" }}
            >
              <X size={16} />
            </button>
          </div>

          {detailLoading ? (
            <div style={{ color: "var(--text-muted)", fontSize: "13px" }}>Loading details...</div>
          ) : selectedItem.type === "module" ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              <div className="font-mono" style={{ fontSize: "14px", fontWeight: 700 }}>
                {selectedItem.id}
              </div>
              {latestChangesByFile
                .filter((ch) => getFolder(ch.file_path) === selectedItem.id)
                .map((ch) => (
                  <button
                    key={ch.change_id}
                    type="button"
                    onClick={() => setSelectedItem({ type: "file", id: ch.change_id, payload: ch })}
                    style={{
                      textAlign: "left",
                      padding: "8px 10px",
                      borderRadius: "6px",
                      border: "1px solid var(--border-subtle)",
                      background: "var(--bg-app)",
                      color: "var(--text-main)",
                      cursor: "pointer",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                    }}
                  >
                    <span className="font-mono" style={{ fontSize: "12px" }}>{getBaseName(ch.file_path)}</span>
                    <OriginBadge origin={ch.origin} />
                  </button>
                ))}
            </div>
          ) : selectedItem.type === "file" && provenance ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <div>
                <div className="font-mono" style={{ fontSize: "13px", fontWeight: 700, wordBreak: "break-all" }}>
                  {provenance.file_path}
                </div>
                <div style={{ display: "flex", gap: "8px", marginTop: "6px", alignItems: "center" }}>
                  <OriginBadge origin={provenance.origin} />
                  <span style={{ fontSize: "12px", color: "#10b981" }}>+{provenance.lines_added ?? 0}</span>
                  <span style={{ fontSize: "12px", color: "#ef4444" }}>−{provenance.lines_deleted ?? 0}</span>
                </div>
              </div>

              {provenance.commit && (
                <div style={{ padding: "10px", borderRadius: "6px", background: "var(--bg-app)", border: "1px solid var(--border-subtle)" }}>
                  <div style={{ fontSize: "10px", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: "4px", display: "flex", alignItems: "center", gap: "5px" }}>
                    <GitCommit size={12} /> Commit {provenance.commit.commit_hash?.slice(0, 7)}
                  </div>
                  <div style={{ fontSize: "12px", color: "var(--text-main)" }}>{provenance.commit.message}</div>
                  <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "3px" }}>{fmtDateTime(provenance.commit.commit_time)}</div>
                </div>
              )}

              {provenance.decision ? (
                <div style={{ padding: "10px", borderRadius: "6px", background: "var(--bg-app)", border: "1px solid rgba(16,185,129,0.3)" }}>
                  <div style={{ fontSize: "10px", fontWeight: 700, color: "#10b981", textTransform: "uppercase", marginBottom: "4px" }}>
                    Linked Decision
                  </div>
                  <div style={{ fontSize: "13px", fontWeight: 600 }}>{provenance.decision.title}</div>
                  {provenance.decision.reason_text && (
                    <div style={{ fontSize: "12px", color: "var(--text-secondary)", fontStyle: "italic", marginTop: "5px" }}>
                      &ldquo;{provenance.decision.reason_text}&rdquo;
                    </div>
                  )}
                  {alts.length > 0 && (
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "4px", marginTop: "8px" }}>
                      {alts.map((a) => (
                        <span
                          key={a.alternative_id}
                          style={{
                            fontSize: "11px",
                            padding: "2px 7px",
                            borderRadius: "4px",
                            background: a.selection_status === "selected" ? "rgba(16,185,129,0.12)" : "rgba(239,68,68,0.1)",
                            color: a.selection_status === "selected" ? "#34d399" : "#f87171",
                            textDecoration: a.selection_status === "rejected" ? "line-through" : "none",
                          }}
                        >
                          {a.description}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <div style={{ padding: "10px", borderRadius: "6px", background: "rgba(245,158,11,0.08)", border: "1px solid rgba(245,158,11,0.25)", color: "#fbbf24", fontSize: "12px" }}>
                  No decision linked to this file yet.
                </div>
              )}

              {provenance.interaction && (
                <div style={{ padding: "10px", borderRadius: "6px", background: "var(--bg-app)", border: "1px solid var(--border-subtle)" }}>
                  <div style={{ fontSize: "10px", fontWeight: 700, color: "#818cf8", textTransform: "uppercase", marginBottom: "4px", display: "flex", alignItems: "center", gap: "5px" }}>
                    <Bot size={12} /> {provenance.interaction.tool_name} ({provenance.interaction.model_name})
                  </div>
                  <div style={{ fontSize: "12px", color: "var(--text-secondary)", maxHeight: "100px", overflowY: "auto", whiteSpace: "pre-wrap" }}>
                    {provenance.interaction.prompt}
                  </div>
                </div>
              )}

              {/* Link / Change Decision */}
              <div style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: "10px" }}>
                <div style={{ fontSize: "11px", fontWeight: 600, color: "var(--text-muted)", marginBottom: "6px", display: "flex", alignItems: "center", gap: "5px" }}>
                  <Link2 size={12} /> Link Decision to File
                </div>
                <div style={{ display: "flex", gap: "6px" }}>
                  <select
                    value={linkTargetId}
                    onChange={(e) => setLinkTargetId(e.target.value)}
                    style={{ flex: 1, padding: "6px 8px", borderRadius: "4px", border: "1px solid var(--border-subtle)", background: "var(--bg-app)", color: "var(--text-main)", fontSize: "12px" }}
                  >
                    <option value="">— No decision —</option>
                    {visibleDecisions.map((d) => (
                      <option key={d.decision_id} value={d.decision_id}>
                        {d.title}
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    disabled={linking}
                    onClick={() => handleLinkFileToDecision(provenance.change_id, linkTargetId || null)}
                    style={{ padding: "6px 10px", borderRadius: "4px", border: "none", background: "var(--color-primary)", color: "#fff", fontSize: "12px", fontWeight: 600, cursor: "pointer" }}
                  >
                    Save
                  </button>
                </div>
              </div>
            </div>
          ) : selectedItem.type === "decision" ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <div>
                <div style={{ fontSize: "15px", fontWeight: 700 }}>{selectedItem.payload.title}</div>
                <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "4px" }}>
                  {selectedItem.payload.description}
                </div>
                <div style={{ display: "flex", gap: "8px", marginTop: "6px", fontSize: "11px" }}>
                  <span style={{ color: statusColor(selectedItem.payload.status), fontWeight: 700 }}>
                    {selectedItem.payload.status}
                  </span>
                  <span style={{ color: "var(--text-muted)" }}>{selectedItem.payload.decision_type}</span>
                  <span style={{ color: "var(--text-muted)" }}>{fmtDate(selectedItem.payload.decided_at)}</span>
                </div>
              </div>

              {/* Rationale */}
              <div style={{ padding: "10px", borderRadius: "6px", background: "rgba(99,102,241,0.08)", border: "1px solid rgba(99,102,241,0.22)" }}>
                <div style={{ fontSize: "10px", fontWeight: 700, color: "#818cf8", textTransform: "uppercase", marginBottom: "4px" }}>
                  Rationale ({selectedItem.payload.reason_source_type})
                </div>
                <div style={{ fontSize: "12px", fontStyle: "italic", color: "var(--text-main)" }}>
                  {selectedItem.payload.reason_text || "No rationale recorded."}
                </div>
              </div>

              {/* Linked Files & Commits */}
              <div>
                <div style={{ fontSize: "10px", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: "6px" }}>
                  Linked Files &amp; Commits
                </div>
                {codeChanges.filter((c) => c.decision?.decision_id === selectedItem.id).length === 0 ? (
                  <div style={{ fontSize: "12px", color: "var(--text-muted)", marginBottom: "8px" }}>
                    No files linked yet.
                  </div>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: "5px", marginBottom: "8px" }}>
                    {codeChanges
                      .filter((c) => c.decision?.decision_id === selectedItem.id)
                      .map((c) => (
                        <button
                          key={c.change_id}
                          type="button"
                          onClick={() => setSelectedItem({ type: "file", id: c.change_id, payload: c })}
                          style={{
                            textAlign: "left",
                            padding: "7px 9px",
                            borderRadius: "5px",
                            border: "1px solid var(--border-subtle)",
                            background: "var(--bg-app)",
                            color: "var(--text-main)",
                            cursor: "pointer",
                          }}
                        >
                          <div className="font-mono" style={{ fontSize: "12px", fontWeight: 600 }}>{c.file_path}</div>
                          {c.commit && (
                            <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "2px" }}>
                              {c.commit.commit_hash?.slice(0, 7)} · {c.commit.message}
                            </div>
                          )}
                        </button>
                      ))}
                  </div>
                )}

                {/* Quick link an unlinked file */}
                {latestChangesByFile.filter((c) => c.decision?.decision_id !== selectedItem.id).length > 0 && (
                  <div style={{ display: "flex", gap: "6px" }}>
                    <select
                      value={linkTargetId}
                      onChange={(e) => setLinkTargetId(e.target.value)}
                      style={{ flex: 1, padding: "6px 8px", borderRadius: "4px", border: "1px solid var(--border-subtle)", background: "var(--bg-app)", color: "var(--text-main)", fontSize: "12px" }}
                    >
                      <option value="">Attach a file...</option>
                      {latestChangesByFile
                        .filter((c) => c.decision?.decision_id !== selectedItem.id)
                        .map((c) => (
                          <option key={c.change_id} value={c.change_id}>
                            {c.file_path}
                          </option>
                        ))}
                    </select>
                    <button
                      type="button"
                      disabled={!linkTargetId || linking}
                      onClick={() => linkTargetId && handleLinkFileToDecision(linkTargetId, selectedItem.id)}
                      style={{ padding: "6px 10px", borderRadius: "4px", border: "none", background: "var(--color-primary)", color: "#fff", fontSize: "12px", fontWeight: 600, cursor: "pointer" }}
                    >
                      Attach
                    </button>
                  </div>
                )}
              </div>

              {/* Alternatives */}
              {alts.length > 0 && (
                <div>
                  <div style={{ fontSize: "10px", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: "6px" }}>
                    Alternatives
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                    {alts.map((a) => (
                      <div key={a.alternative_id} style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", padding: "5px 8px", borderRadius: "4px", background: "var(--bg-app)" }}>
                        {a.selection_status === "selected" ? (
                          <CheckCircle2 size={13} color="#10b981" />
                        ) : a.selection_status === "rejected" ? (
                          <XCircle size={13} color="#ef4444" />
                        ) : (
                          <HelpCircle size={13} color="#9ca3af" />
                        )}
                        <span style={{ flex: 1 }}>{a.description}</span>
                        <span style={{ fontSize: "10px", color: "var(--text-muted)" }}>{a.selection_status}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Evidence */}
              {evidence.length > 0 && (
                <div>
                  <div style={{ fontSize: "10px", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: "6px" }}>
                    Transcript Evidence ({evidence.length})
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                    {evidence.map((ev) => (
                      <div key={ev.evidence_id} style={{ fontSize: "11px", color: "var(--text-secondary)", fontStyle: "italic", padding: "6px 8px", borderRadius: "4px", background: "var(--bg-app)" }}>
                        {ev.source_reference}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : null}
        </aside>
      )}
    </div>
  );
}
