import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import type { Article, Paper } from "../types";

interface Props {
  itemType: "paper" | "article";
  itemId: string;
  className?: string;
}

/** Manual graph connections (Graph page's dashed-vs-solid edges) previously
 * had no entry point outside the Graph canvas itself — you had to already
 * know both items showed up there (which requires saving them to a list
 * first) and click one node then the other. This puts the same action
 * (POST /api/graph/edges) directly on the item you're already looking at. */
export default function LinkItemButton({ itemType, itemId, className }: Props) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [papers, setPapers] = useState<Paper[]>([]);
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(false);
  const [linked, setLinked] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function handleOutsideClick(e: MouseEvent) {
      if (!containerRef.current?.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handleOutsideClick);
    return () => document.removeEventListener("mousedown", handleOutsideClick);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setLoading(true);
    const trimmed = query.trim();
    const handle = setTimeout(
      () => {
        const request = trimmed
          ? api.get<{ papers: Paper[]; articles: Article[] }>(`/api/library/search?q=${encodeURIComponent(trimmed)}`)
          : api.get<Paper[]>("/api/feed?limit=8").then((p) => ({ papers: p, articles: [] as Article[] }));
        request
          .then((result) => {
            if (cancelled) return;
            setPapers(result.papers.filter((p) => !(itemType === "paper" && p.id === itemId)));
            setArticles((result.articles ?? []).filter((a) => !(itemType === "article" && a.id === itemId)));
          })
          .finally(() => {
            if (!cancelled) setLoading(false);
          });
      },
      trimmed ? 300 : 0
    );
    return () => {
      cancelled = true;
      clearTimeout(handle);
    };
  }, [open, query, itemType, itemId]);

  async function link(targetType: "paper" | "article", targetId: string) {
    await api.post("/api/graph/edges", {
      source_type: itemType,
      source_id: itemId,
      target_type: targetType,
      target_id: targetId,
    });
    setOpen(false);
    setQuery("");
    setLinked(true);
    setTimeout(() => setLinked(false), 2000);
  }

  return (
    <div ref={containerRef} style={{ position: "relative", display: "inline-block" }}>
      <button
        className={className ?? "subtle"}
        onClick={() => setOpen((o) => !o)}
        type="button"
        title="Connect this to another paper or article in the graph"
      >
        {linked ? "Linked" : "Link to..."}
      </button>
      {open && (
        <div
          style={{
            position: "absolute",
            top: "calc(100% + 4px)",
            right: 0,
            background: "var(--color-bg-raised)",
            border: "1px solid var(--color-border-strong)",
            borderRadius: 6,
            padding: 12,
            width: 280,
            zIndex: 10,
          }}
        >
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search papers & articles..."
            autoFocus
            style={{ width: "100%", marginBottom: 8 }}
          />
          {loading && (
            <p className="empty-state" style={{ margin: 0 }}>
              Loading...
            </p>
          )}
          {!loading && papers.length === 0 && articles.length === 0 && (
            <p className="empty-state" style={{ margin: 0 }}>
              No matches.
            </p>
          )}
          <div className="split-pane-picker-list" style={{ maxHeight: 260 }}>
            {papers.map((p) => (
              <button key={p.id} className="split-pane-picker-row" type="button" onClick={() => link("paper", p.id)}>
                {p.title}
              </button>
            ))}
            {articles.map((a) => (
              <button key={a.id} className="split-pane-picker-row" type="button" onClick={() => link("article", a.id)}>
                {a.title}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
