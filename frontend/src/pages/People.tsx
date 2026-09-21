import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { AuthorSearchResult, FollowedEntry, Paper } from "../types";
import ItemCard from "../components/ItemCard";
import SearchIcon from "../components/SearchIcon";

export default function People() {
  const [q, setQ] = useState("");
  const [results, setResults] = useState<AuthorSearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [followed, setFollowed] = useState<FollowedEntry[]>([]);
  const [followingId, setFollowingId] = useState<string | null>(null);
  const [searchError, setSearchError] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [lastQuery, setLastQuery] = useState("");
  const [expandedTopicId, setExpandedTopicId] = useState<string | null>(null);
  const [topicPapers, setTopicPapers] = useState<Record<string, Paper[]>>({});
  const [loadingTopicId, setLoadingTopicId] = useState<string | null>(null);

  function loadFollowed() {
    api.get<FollowedEntry[]>("/api/researchers/followed").then(setFollowed);
  }

  useEffect(loadFollowed, []);

  async function search() {
    if (!q.trim()) return;
    setSearching(true);
    setSearchError(false);
    try {
      const result = await api.get<AuthorSearchResult[]>(`/api/researchers/search?q=${encodeURIComponent(q)}`);
      setResults(result);
      setLastQuery(q.trim());
      setHasSearched(true);
    } catch {
      setResults([]);
      setSearchError(true);
      setHasSearched(true);
    } finally {
      setSearching(false);
    }
  }

  async function follow(author: AuthorSearchResult) {
    setFollowingId(author.openalex_id);
    try {
      await api.post("/api/researchers/follow", {
        openalex_id: author.openalex_id,
        merged_ids: author.merged_ids,
      });
      setResults((r) => r.filter((a) => a.openalex_id !== author.openalex_id));
      loadFollowed();
    } finally {
      setFollowingId(null);
    }
  }

  async function unfollow(topicId: string) {
    await api.del(`/api/researchers/follow/${topicId}`);
    loadFollowed();
  }

  async function loadTopicPapers(topicId: string) {
    setLoadingTopicId(topicId);
    try {
      const papers = await api.get<Paper[]>(`/api/feed?topic_id=${topicId}&limit=200`);
      setTopicPapers((prev) => ({ ...prev, [topicId]: papers }));
    } finally {
      setLoadingTopicId(null);
    }
  }

  function toggleExpanded(topicId: string) {
    if (expandedTopicId === topicId) {
      setExpandedTopicId(null);
      return;
    }
    setExpandedTopicId(topicId);
    if (!topicPapers[topicId]) loadTopicPapers(topicId);
  }

  const followedOpenAlexIds = new Set(followed.map((f) => f.researcher.openalex_id));

  return (
    <div>
      <div className="search-box">
        <div className="search-input-wrap">
          <SearchIcon />
          <input value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && search()} autoFocus />
        </div>
        <button className="primary" onClick={search} disabled={searching || !q.trim()}>
          {searching ? "Searching..." : "Search"}
        </button>
      </div>

      {searchError && (
        <p className="empty-state">OpenAlex search failed — try again in a moment.</p>
      )}

      {hasSearched && !searchError && results.length === 0 && (
        <p className="empty-state">No one found for "{lastQuery}" — check the spelling?</p>
      )}

      {results.length > 0 && (
        <div className="list-grid" style={{ marginBottom: 32 }}>
          {results.map((a) => {
            const isFollowed = followedOpenAlexIds.has(a.openalex_id);
            return (
              <div key={a.openalex_id} className="source-row">
                <div>
                  <strong>{a.name}</strong>
                  <div className="page-subtitle">
                    {[a.affiliation, a.works_count ? `${a.works_count} works` : null].filter(Boolean).join(" · ")}
                  </div>
                </div>
                <button
                  className={isFollowed ? "subtle" : "primary"}
                  disabled={isFollowed || followingId === a.openalex_id}
                  onClick={() => follow(a)}
                >
                  {isFollowed ? "Following" : followingId === a.openalex_id ? "Following..." : "Follow"}
                </button>
              </div>
            );
          })}
        </div>
      )}

      <h3>Following</h3>
      {followed.length === 0 && <p className="empty-state">Not following anyone yet.</p>}
      <div className="list-grid">
        {followed.map(({ topic, researcher }) => {
          const isExpanded = expandedTopicId === topic.id;
          const papers = topicPapers[topic.id];
          return (
            <div key={topic.id}>
              <div className="topic-row">
                <div>
                  <Link to={`/researchers/${researcher.id}`} style={{ color: "var(--color-ink)" }}>
                    <strong>{researcher.name}</strong>
                  </Link>
                  <div className="page-subtitle">{researcher.affiliation}</div>
                </div>
                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <button className="btn" onClick={() => toggleExpanded(topic.id)}>
                    {isExpanded ? "Hide papers" : `Show papers${papers ? ` (${papers.length})` : ""}`}
                  </button>
                  <button className="subtle" onClick={() => unfollow(topic.id)}>
                    Unfollow
                  </button>
                </div>
              </div>
              {isExpanded && (
                <div style={{ marginBottom: 24 }}>
                  {loadingTopicId === topic.id && <p className="empty-state">Loading...</p>}
                  {papers && papers.length === 0 && (
                    <div className="empty-state">
                      No papers tagged to this follow yet — try again in a moment, or{" "}
                      <button
                        className="subtle"
                        style={{ padding: 0 }}
                        onClick={() => api.post(`/api/topics/${topic.id}/reset-dismissed`).then(() => loadTopicPapers(topic.id))}
                      >
                        reset removed papers
                      </button>
                      .
                    </div>
                  )}
                  {papers?.map((p) => (
                    <ItemCard key={p.id} kind="paper" item={p} onStatusChange={() => loadTopicPapers(topic.id)} />
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
