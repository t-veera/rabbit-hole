import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import type { Article, Paper } from "../types";
import ItemReader from "../components/ItemReader";
import NotesPane from "../components/NotesPane";

type PaneSpec = { mode: "doc"; kind: "paper" | "article"; id: string } | { mode: "notes" };

function parsePane(raw: string | null): PaneSpec | null {
  if (!raw) return null;
  if (raw === "notes") return { mode: "notes" };
  const [kind, id] = raw.split(":");
  if ((kind === "paper" || kind === "article") && id) return { mode: "doc", kind, id };
  return null;
}

function DocPicker({ onPick }: { onPick: (value: string) => void }) {
  const [query, setQuery] = useState("");
  const [papers, setPapers] = useState<Paper[]>([]);
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    const trimmed = query.trim();
    const handle = setTimeout(
      () => {
        const request = trimmed
          ? api.get<{ papers: Paper[]; articles: Article[] }>(`/api/library/search?q=${encodeURIComponent(trimmed)}`)
          : api.get<Paper[]>("/api/feed?limit=8").then((papers) => ({ papers, articles: [] as Article[] }));
        request
          .then((result) => {
            if (cancelled) return;
            setPapers(result.papers);
            setArticles(result.articles ?? []);
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
  }, [query]);

  return (
    <div>
      <input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        style={{ width: "100%", marginBottom: 12 }}
        autoFocus
      />
      <div className="page-subtitle" style={{ marginBottom: 8 }}>
        {query.trim() ? "Matching your library" : "Recent from your feed"}
      </div>
      {loading && <p className="empty-state">Loading...</p>}
      {!loading && papers.length === 0 && articles.length === 0 && <p className="empty-state">No matches.</p>}
      <div className="split-pane-picker-list">
        {papers.map((p) => (
          <button key={p.id} className="split-pane-picker-row" onClick={() => onPick(`paper:${p.id}`)}>
            {p.title}
          </button>
        ))}
        {articles.map((a) => (
          <button key={a.id} className="split-pane-picker-row" onClick={() => onPick(`article:${a.id}`)}>
            {a.title}
          </button>
        ))}
      </div>
    </div>
  );
}

function Pane({ spec, lastDoc, onChange }: { spec: PaneSpec | null; lastDoc: string; onChange: (value: string) => void }) {
  return (
    <div className="split-pane-col">
      <div style={{ display: "flex", gap: 8, marginBottom: 8, alignItems: "center" }}>
        <div className="field-filters" style={{ margin: 0, border: "none", padding: 0, gap: 12 }}>
          <button
            className={"chip" + (spec?.mode === "notes" ? " active" : "")}
            onClick={() => onChange(spec?.mode === "notes" ? "" : "notes")}
          >
            Notes
          </button>
          <button
            className={"chip" + (spec?.mode === "doc" ? " active" : "")}
            onClick={() => onChange(spec?.mode === "doc" ? "" : lastDoc)}
          >
            Document
          </button>
        </div>
        <button className="subtle" onClick={() => onChange("")} disabled={!spec} title="Close this pane" style={{ marginLeft: "auto" }}>
          ×
        </button>
      </div>

      {spec?.mode === "notes" && <NotesPane />}
      {spec?.mode === "doc" && <ItemReader kind={spec.kind} id={spec.id} compact />}
      {!spec && <DocPicker onPick={onChange} />}
    </div>
  );
}

export default function SplitView() {
  const [params, setParams] = useSearchParams();
  const rawA = params.get("a") ?? "";
  const rawB = params.get("b") ?? "";
  const left = parsePane(rawA);
  const right = parsePane(rawB);

  // Remembers each slot's last real document reference so switching to
  // Notes and back doesn't lose it — the URL param only holds one value at
  // a time, and setting it to "notes" would otherwise overwrite the
  // paper/article id with no way to restore it.
  const lastDocA = useRef("");
  const lastDocB = useRef("");
  if (rawA && rawA !== "notes") lastDocA.current = rawA;
  if (rawB && rawB !== "notes") lastDocB.current = rawB;

  function setSlot(slot: "a" | "b", value: string) {
    const next = new URLSearchParams(params);
    if (value) next.set(slot, value);
    else next.delete(slot);
    setParams(next, { replace: true });
  }

  // Closing split view should return to whichever document was open, not
  // always the Feed — otherwise the paper you were reading just vanishes.
  const openDoc = left?.mode === "doc" ? left : right?.mode === "doc" ? right : null;
  const closeTarget = openDoc ? `/${openDoc.kind}s/${openDoc.id}` : "/";

  return (
    <div>
      <div className="page-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <div>
          <h1>Side-by-side reading</h1>
          <div className="page-subtitle">
            Either pane can hold a document (search your library, or open one with "Open in split
            view") or a running Notes pane — an open synthesis space that stays put as you swap
            documents in the other pane.
          </div>
        </div>
        <Link to={closeTarget} className="btn subtle">
          Close split view
        </Link>
      </div>
      <div className="split-pane">
        <Pane spec={left} lastDoc={lastDocA.current} onChange={(v) => setSlot("a", v)} />
        <Pane spec={right} lastDoc={lastDocB.current} onChange={(v) => setSlot("b", v)} />
      </div>
    </div>
  );
}
