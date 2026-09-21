import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { API_BASE, api } from "../api/client";
import type { Article, FollowedEntry, ItemType, Paper } from "../types";
import AddToListButton from "./AddToListButton";
import LinkItemButton from "./LinkItemButton";
import Highlighter from "./Highlighter";
import PlusIcon from "./PlusIcon";
import Prose from "./Prose";
import UploadPdf from "./UploadPdf";

interface Props {
  kind: ItemType;
  id: string;
  compact?: boolean;
}

export default function ItemReader({ kind, id, compact }: Props) {
  const [paper, setPaper] = useState<Paper | null>(null);
  const [article, setArticle] = useState<Article | null>(null);
  const [loading, setLoading] = useState(true);
  const [fullText, setFullText] = useState<string | null>(null);
  const [fullTextLoading, setFullTextLoading] = useState(false);
  const [trackedIds, setTrackedIds] = useState<Set<string>>(new Set());
  const [trackingId, setTrackingId] = useState<string | null>(null);

  function loadTracked() {
    api
      .get<FollowedEntry[]>("/api/researchers/followed")
      .then((entries) => setTrackedIds(new Set(entries.map((e) => e.researcher.id))))
      .catch(() => {});
  }

  useEffect(() => {
    setLoading(true);
    setFullText(null);
    setFullTextLoading(true);
    const detailPath = kind === "paper" ? `/api/papers/${id}` : `/api/journalism/${id}`;
    const fulltextPath = kind === "paper" ? `/api/papers/${id}/fulltext-text` : `/api/journalism/${id}/fulltext-text`;

    if (kind === "paper") {
      api.get<Paper>(detailPath).then(setPaper).finally(() => setLoading(false));
      loadTracked();
    } else {
      api.get<Article>(detailPath).then(setArticle).finally(() => setLoading(false));
    }

    api
      .get<{ text: string | null }>(fulltextPath)
      .then((r) => setFullText(r.text))
      .catch(() => setFullText(null))
      .finally(() => setFullTextLoading(false));
  }, [kind, id]);

  async function addToPeople(researcherId: string) {
    setTrackingId(researcherId);
    try {
      await api.post(`/api/researchers/${researcherId}/track`);
      loadTracked();
    } catch {
      // e.g. "already following" from a race with another tab — harmless, just refresh state
      loadTracked();
    } finally {
      setTrackingId(null);
    }
  }

  if (loading) return <p className="empty-state">Loading...</p>;

  const item = paper ?? article;
  if (!item) return <p className="empty-state">Not found.</p>;

  return (
    <div>
      <div className="detail-header">
        {!compact && <h1 className="detail-title">{item.title}</h1>}
        {compact && <h3>{item.title}</h3>}
        <div className="item-meta">
          <span>{item.origin_source?.name ?? (paper ? paper.venue ?? "Discovered" : "Journalism")}</span>
          <span>&middot;</span>
          <span>{item.published_date ? new Date(item.published_date).toLocaleDateString() : "undated"}</span>
          {paper?.oa_status && <span className="tag tag-oa">open access</span>}
          {paper?.origin === "uploaded" && <span className="tag tag-mine">uploaded</span>}
          <AddToListButton itemType={kind} itemId={id} />
          <LinkItemButton itemType={kind as "paper" | "article"} itemId={id} />
        </div>
      </div>

      {paper && paper.authors.length > 0 && (
        <div style={{ marginBottom: 16, display: "flex", flexWrap: "wrap", alignItems: "center" }}>
          {paper.authors.map((a) => (
            <span key={a.researcher.id} className="author-row">
              <Link to={`/researchers/${a.researcher.id}`} className="author-chip">
                {a.researcher.name}
              </Link>
              {!trackedIds.has(a.researcher.id) && (
                <button
                  className="add-person-btn"
                  disabled={trackingId === a.researcher.id}
                  onClick={() => addToPeople(a.researcher.id)}
                  title={`Follow ${a.researcher.name} — pull in their other work automatically`}
                  aria-label={`Add ${a.researcher.name} to People`}
                >
                  <PlusIcon />
                </button>
              )}
            </span>
          ))}
        </div>
      )}

      {article?.author_name && (
        <div style={{ marginBottom: 16 }}>
          {article.author_researcher_id ? (
            <Link to={`/researchers/${article.author_researcher_id}`} className="author-chip">
              {article.author_name}
            </Link>
          ) : (
            <span className="item-authors">{article.author_name}</span>
          )}
        </div>
      )}

      <Highlighter itemType={kind} itemId={id}>
        <Prose className="article-body" text={paper?.abstract || article?.summary || "No abstract available."} />
      </Highlighter>

      {fullTextLoading && (
        <p className="page-subtitle" style={{ marginTop: 12 }}>
          Fetching and formatting the full text...
        </p>
      )}

      {!fullTextLoading && fullText && (
        <div style={{ marginTop: 28 }}>
          <div className="fulltext-embed-bar" style={{ marginBottom: 16 }}>
            <span>Full text</span>
          </div>
          <Highlighter itemType={kind} itemId={id}>
            <Prose className="article-body" text={fullText} />
          </Highlighter>
        </div>
      )}

      {!fullTextLoading && !fullText && (
        <div className="translation-preview" style={{ marginTop: 20 }}>
          <p style={{ margin: 0 }}>
            {paper
              ? "No full text on file — either there's no open-access copy, or every copy we found blocks automated fetching (common for major publishers)."
              : "No full text on file — the source site blocks automated fetching (common for major publishers)."}
          </p>
          <div style={{ marginTop: 10, display: "flex", gap: 10, alignItems: "center" }}>
            {paper && <UploadPdf compact />}
            {paper?.oa_url && (
              <a href={paper.oa_url} target="_blank" rel="noreferrer">
                Try the source site yourself ↗
              </a>
            )}
          </div>
        </div>
      )}

      <div className="reader-secondary-actions">
        {!paper?.oa_url && paper?.landing_url && (
          <a href={paper.landing_url} target="_blank" rel="noreferrer">
            View at publisher
          </a>
        )}
        {article && (
          <a href={article.url} target="_blank" rel="noreferrer">
            Read on {article.origin_source?.name ?? "source site"} ↗
          </a>
        )}
        {paper && (
          <>
            <a href={`${API_BASE}/api/papers/${id}/export?format=bibtex`} target="_blank" rel="noreferrer">
              BibTeX
            </a>
            <a href={`${API_BASE}/api/papers/${id}/export?format=ris`} target="_blank" rel="noreferrer">
              RIS
            </a>
          </>
        )}
      </div>
    </div>
  );
}
