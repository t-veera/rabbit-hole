import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import type { Notification, Paper, PaperOrigin, ReadingState, Topic } from "../types";
import ItemCard from "../components/ItemCard";
import FieldFilters from "../components/FieldFilters";
import UploadPdf from "../components/UploadPdf";

type ViewMode = "all" | "queue" | "reference";
type SortMode = "published_desc" | "published_asc" | "added_desc" | "added_asc" | "title_asc";

const SORT_LABELS: Record<SortMode, string> = {
  published_desc: "Newest published",
  published_asc: "Oldest published",
  added_desc: "Recently added",
  added_asc: "Oldest added",
  title_asc: "Title A–Z",
};

export default function Feed() {
  const [urlParams] = useSearchParams();
  const initialTopicId = urlParams.get("topic_id") ?? "";
  const [papers, setPapers] = useState<Paper[]>([]);
  const [field, setField] = useState<string | null>(null);
  const [topicId, setTopicId] = useState<string>(initialTopicId);
  const [origin, setOrigin] = useState<"" | PaperOrigin>("");
  const [status, setStatus] = useState<ReadingState | "">("");
  const [hideRead, setHideRead] = useState(false);
  const [view, setView] = useState<ViewMode>("all");
  const [sort, setSort] = useState<SortMode>("published_desc");
  const [topics, setTopics] = useState<Topic[]>([]);
  const [loading, setLoading] = useState(true);
  const [showFilters, setShowFilters] = useState(!!initialTopicId);

  useEffect(() => {
    api.get<Topic[]>("/api/topics").then(setTopics).catch(() => {});
  }, []);

  useEffect(() => {
    load();
    markSeen();
  }, [field, topicId, origin, status, hideRead, view, sort]);

  // The sidebar's unread badge is per-topic (services/scheduler + SeenLog),
  // so "viewing the feed" has to translate into marking the relevant
  // topic(s) seen — viewing one topic marks just that one, viewing "All"
  // marks every topic currently showing a badge. Sidebar listens for this
  // event to refresh its own count immediately rather than on next mount.
  function markSeen() {
    if (topicId) {
      api.post(`/api/topics/${topicId}/mark-seen`).finally(() => window.dispatchEvent(new Event("rh:notifications-refresh")));
      return;
    }
    api
      .get<Notification[]>("/api/topics/notifications")
      .then((notifications) => Promise.all(notifications.map((n) => api.post(`/api/topics/${n.topic_id}/mark-seen`))))
      .finally(() => window.dispatchEvent(new Event("rh:notifications-refresh")));
  }

  function load() {
    setLoading(true);
    const params = new URLSearchParams();
    if (field) params.set("field", field);
    if (topicId) params.set("topic_id", topicId);
    if (origin) params.set("origin", origin);
    if (status) params.set("status", status);
    if (hideRead) params.set("exclude_status", "read");
    if (view === "queue") params.set("in_queue", "true");
    if (view === "reference") params.set("in_reference", "true");
    params.set("sort", sort);
    api
      .get<Paper[]>(`/api/feed?${params.toString()}`)
      .then(setPapers)
      .finally(() => setLoading(false));
  }

  const activeFilterCount = [field, topicId, origin, status].filter(Boolean).length + (hideRead ? 1 : 0);

  return (
    <div>
      <div className="feed-toolbar">
        <div className="field-filters" style={{ margin: 0, border: "none", padding: 0 }}>
          {(["all", "queue", "reference"] as ViewMode[]).map((v) => (
            <button key={v} className={"chip" + (view === v ? " active" : "")} onClick={() => setView(v)}>
              {v === "all" ? "All" : v === "queue" ? "To read" : "Reference library"}
            </button>
          ))}
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <select value={sort} onChange={(e) => setSort(e.target.value as SortMode)}>
            {(Object.keys(SORT_LABELS) as SortMode[]).map((s) => (
              <option key={s} value={s}>
                {SORT_LABELS[s]}
              </option>
            ))}
          </select>
          <button
            className={"btn" + (showFilters || activeFilterCount ? " active" : "")}
            onClick={() => setShowFilters((s) => !s)}
          >
            Filters{activeFilterCount ? ` (${activeFilterCount})` : ""} {showFilters ? "▴" : "▾"}
          </button>
          <UploadPdf compact />
        </div>
      </div>

      {showFilters && (
        <div className="translation-preview" style={{ marginTop: 0 }}>
          <FieldFilters value={field} onChange={setField} />
          <div className="field-filters" style={{ border: "none", padding: 0, marginBottom: 0 }}>
            <select value={topicId} onChange={(e) => setTopicId(e.target.value)}>
              <option value="">All topics</option>
              {topics.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.raw_query}
                </option>
              ))}
            </select>
            <select value={origin} onChange={(e) => setOrigin(e.target.value as any)}>
              <option value="">Any origin</option>
              <option value="source">From your sources</option>
              <option value="discovered">Discovered</option>
              <option value="uploaded">Uploaded</option>
            </select>
            <select value={status} onChange={(e) => setStatus(e.target.value as any)}>
              <option value="">Any status</option>
              <option value="unread">Unread</option>
              <option value="read">Read</option>
              <option value="skimmed">Skimmed</option>
            </select>
            <label style={{ display: "inline-flex", alignItems: "center", gap: 5 }}>
              <input type="checkbox" checked={hideRead} onChange={(e) => setHideRead(e.target.checked)} />
              Hide read
            </label>
            {topicId && (
              <button
                className="subtle"
                onClick={() => api.post(`/api/topics/${topicId}/reset-dismissed`).then(load)}
                title="Bring back any papers you removed from this topic"
              >
                Reset removed papers
              </button>
            )}
          </div>
        </div>
      )}

      {loading && <p className="empty-state">Loading...</p>}
      {!loading && papers.length === 0 && (
        <p className="empty-state">
          Nothing here yet. Head to Search to add a topic and pull in some papers.
        </p>
      )}
      {papers.map((p) => (
        <ItemCard key={p.id} kind="paper" item={p} onStatusChange={load} />
      ))}
    </div>
  );
}
