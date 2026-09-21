import { useEffect, useMemo, useRef, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { GraphData, GraphNode } from "../types";

function cssVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

export default function Graph() {
  const [data, setData] = useState<GraphData>({ nodes: [], edges: [] });
  const [includeCitations, setIncludeCitations] = useState(true);
  const [orphansOnly, setOrphansOnly] = useState(false);
  const [connectFrom, setConnectFrom] = useState<GraphNode | null>(null);
  const [connecting, setConnecting] = useState(false);
  const navigate = useNavigate();
  const containerRef = useRef<HTMLDivElement>(null);

  // Canvas can't read CSS custom properties directly, so pull the resolved
  // theme colors once per mount/theme-change instead of hardcoding hex that
  // would silently go stale (and mismatch) every time the palette changes.
  const colors = useMemo(
    () => ({
      accent: cssVar("--color-accent"),
      ink: cssVar("--color-ink"),
      bg: cssVar("--color-bg"),
      borderStrong: cssVar("--color-border-strong"),
    }),
    []
  );

  function load() {
    const path = orphansOnly ? "/api/graph/orphans" : `/api/graph?include_citations=${includeCitations}`;
    api.get<GraphData>(path).then(setData);
  }

  useEffect(load, [includeCitations, orphansOnly]);

  async function connectTo(target: GraphNode) {
    if (!connectFrom || target.id === connectFrom.id) return;
    setConnecting(true);
    try {
      await api.post("/api/graph/edges", {
        source_type: connectFrom.item_type,
        source_id: connectFrom.item_id,
        target_type: target.item_type,
        target_id: target.item_id,
      });
      setConnectFrom(null);
      load();
    } finally {
      setConnecting(false);
    }
  }

  async function removeEdge(edgeId: string) {
    await api.del(`/api/graph/edges/${edgeId}`);
    load();
  }

  const manualEdges = data.edges.filter((e) => e.edge_type === "manual");
  const nodeById = new Map(data.nodes.map((n) => [n.id, n]));

  const graphData = useMemo(
    () => ({
      nodes: data.nodes.map((n) => ({ ...n })),
      links: data.edges.map((e) => ({
        source: `${e.source_type}:${e.source_id}`,
        target: `${e.target_type}:${e.target_id}`,
        edge_type: e.edge_type,
      })),
    }),
    [data]
  );

  return (
    <div>
      <div className="graph-page-container" ref={containerRef}>
        <div className="graph-overlay-controls">
          <strong style={{ fontFamily: "var(--font-display)", fontSize: 17 }}>Graph</strong>
          <label>
            <input
              type="checkbox"
              checked={includeCitations}
              onChange={(e) => setIncludeCitations(e.target.checked)}
              disabled={orphansOnly}
            />{" "}
            Citation edges
          </label>
          <label>
            <input type="checkbox" checked={orphansOnly} onChange={(e) => setOrphansOnly(e.target.checked)} />{" "}
            Orphans only
          </label>
          {!connectFrom && <span className="page-subtitle">Click a node, then click another to connect them</span>}
          {connectFrom && (
            <span className="page-subtitle" style={{ display: "flex", alignItems: "center", gap: 8 }}>
              {connecting ? "Connecting..." : `Connecting from "${connectFrom.title.slice(0, 40)}" — click another node`}
              <button className="subtle" onClick={() => setConnectFrom(null)}>
                Cancel
              </button>
              <button
                className="subtle"
                onClick={() =>
                  navigate(connectFrom.item_type === "paper" ? `/papers/${connectFrom.item_id}` : `/articles/${connectFrom.item_id}`)
                }
              >
                Open it instead
              </button>
            </span>
          )}
        </div>

        {data.nodes.length === 0 ? (
          <p className="empty-state" style={{ padding: 24 }}>
            Nothing to show yet. Save items to lists and draw connections to populate the graph.
          </p>
        ) : (
          <ForceGraph2D
            graphData={graphData as any}
            nodeId="id"
            width={containerRef.current?.clientWidth ?? 800}
            height={containerRef.current?.clientHeight ?? 800}
            linkColor={(l: any) => (l.edge_type === "citation" ? colors.borderStrong : colors.accent)}
            linkLineDash={(l: any) => (l.edge_type === "citation" ? [3, 3] : null)}
            linkWidth={1.5}
            nodeCanvasObject={(node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
              const label = node.title.length > 40 ? node.title.slice(0, 40) + "..." : node.title;
              const fontSize = 11 / globalScale;
              ctx.font = `${fontSize}px "Work Sans", sans-serif`;
              const isSelected = connectFrom?.id === node.id;
              const radius = isSelected ? 7 : 5;

              ctx.beginPath();
              ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI);
              ctx.fillStyle = node.is_saved ? colors.accent : colors.bg;
              ctx.fill();
              ctx.lineWidth = isSelected ? 3 : 1.5;
              ctx.strokeStyle = isSelected ? colors.accent : node.is_linked ? colors.ink : colors.accent;
              ctx.stroke();

              ctx.fillStyle = colors.ink;
              ctx.textAlign = "center";
              ctx.fillText(label, node.x, node.y + radius + fontSize);
            }}
            onNodeClick={(node: any) => {
              const graphNode = node as GraphNode;
              if (!connectFrom) {
                setConnectFrom(graphNode);
                return;
              }
              if (connectFrom.id === graphNode.id) {
                setConnectFrom(null);
                return;
              }
              connectTo(graphNode);
            }}
          />
        )}
      </div>

      {manualEdges.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <h3>Manual connections</h3>
          {manualEdges.map((e) => {
            const source = nodeById.get(`${e.source_type}:${e.source_id}`);
            const target = nodeById.get(`${e.target_type}:${e.target_id}`);
            return (
              <div key={e.id} className="topic-row">
                <div className="page-subtitle">
                  {source?.title ?? e.source_type} &harr; {target?.title ?? e.target_type}
                </div>
                <button className="subtle" onClick={() => removeEdge(e.id)}>
                  Remove
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
