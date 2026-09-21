import { useState } from "react";
import { api } from "../api/client";
import type { Article, Book, Cadence, Paper } from "../types";
import ItemCard from "../components/ItemCard";
import BookCard from "../components/BookCard";
import SearchIcon from "../components/SearchIcon";

export default function Search() {
  const [rawQuery, setRawQuery] = useState("");
  const [translated, setTranslated] = useState("");
  const [field, setField] = useState("");
  const [running, setRunning] = useState(false);
  const [saveAsTopic, setSaveAsTopic] = useState(true);
  const [cadence, setCadence] = useState<Cadence>("daily");
  const [showOptions, setShowOptions] = useState(false);
  const [papers, setPapers] = useState<Paper[]>([]);
  const [articles, setArticles] = useState<Article[]>([]);
  const [books, setBooks] = useState<Book[]>([]);
  const [hasRun, setHasRun] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // One click: translate + run happen together. Translated terms are shown
  // alongside the results afterward, editable, for anyone who wants to
  // refine and re-search — but nobody has to see that step to get results.
  async function handleSearch() {
    if (!rawQuery.trim() || running) return;
    setRunning(true);
    setHasRun(false);
    setError(null);
    try {
      const result = await api.post<{
        translated_query: string;
        inferred_field: string;
        papers: Paper[];
        articles: Article[];
        books: Book[];
      }>("/api/search/run", {
        raw_query: rawQuery,
        save_as_topic: saveAsTopic,
        cadence,
      });
      setTranslated(result.translated_query);
      setField(result.inferred_field);
      setPapers(result.papers);
      setArticles(result.articles);
      setBooks(result.books);
      setHasRun(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Search failed. Try again.");
    } finally {
      setRunning(false);
    }
  }

  async function rerunWithEditedTerms() {
    if (!translated.trim() || running) return;
    setRunning(true);
    setError(null);
    try {
      const result = await api.post<{ papers: Paper[]; articles: Article[]; books: Book[] }>(
        "/api/search/run",
        { raw_query: translated, field: field || undefined, save_as_topic: false }
      );
      setPapers(result.papers);
      setArticles(result.articles);
      setBooks(result.books);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Search failed. Try again.");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div>
      <div className="search-box">
        <div className="search-input-wrap">
          <SearchIcon />
          <input
            value={rawQuery}
            onChange={(e) => setRawQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            autoFocus
          />
        </div>
        <button className="primary" onClick={handleSearch} disabled={running || !rawQuery.trim()}>
          {running ? "Searching..." : "Search"}
        </button>
        <button className="subtle" onClick={() => setShowOptions((s) => !s)} type="button">
          Options
        </button>
      </div>

      {error && <p className="empty-state" style={{ color: "var(--color-accent)" }}>{error}</p>}

      {showOptions && (
        <div className="translation-preview">
          <label style={{ display: "block", marginBottom: 8 }}>
            <input type="checkbox" checked={saveAsTopic} onChange={(e) => setSaveAsTopic(e.target.checked)} />{" "}
            Save as a topic (keeps refreshing in the background)
          </label>
          {saveAsTopic && (
            <label>
              Refresh cadence:{" "}
              <select value={cadence} onChange={(e) => setCadence(e.target.value as Cadence)}>
                <option value="realtime">Real-time (~15 min)</option>
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
              </select>
            </label>
          )}
        </div>
      )}

      {hasRun && (
        <div>
          <div className="translation-preview">
            <strong>Searched as:</strong> "{translated}" &middot; field: {field.replace("_", " ")}
            <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
              <input value={translated} onChange={(e) => setTranslated(e.target.value)} style={{ flex: 1 }} />
              <button onClick={rerunWithEditedTerms} disabled={running}>
                Refine &amp; re-search
              </button>
            </div>
          </div>

          <h3>Papers ({papers.length})</h3>
          {papers.length === 0 && <p className="empty-state">No papers found for this query.</p>}
          {papers.map((p) => (
            <ItemCard key={p.id} kind="paper" item={p} />
          ))}
          <h3 style={{ marginTop: 32 }}>Books ({books.length})</h3>
          {books.length === 0 && <p className="empty-state">No books found for this query.</p>}
          {books.map((b) => (
            <BookCard key={b.id} book={b} />
          ))}
          <h3 style={{ marginTop: 32 }}>Journalism ({articles.length})</h3>
          {articles.length === 0 && <p className="empty-state">No journalism items found for this query.</p>}
          {articles.map((a) => (
            <ItemCard key={a.id} kind="article" item={a} />
          ))}
        </div>
      )}
    </div>
  );
}
