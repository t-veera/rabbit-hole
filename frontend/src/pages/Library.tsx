import { useState } from "react";
import { api } from "../api/client";
import type { Article, Book, Note, Paper } from "../types";
import ItemCard from "../components/ItemCard";
import BookCard from "../components/BookCard";
import UploadPdf from "../components/UploadPdf";
import SearchIcon from "../components/SearchIcon";

interface Results {
  papers: Paper[];
  articles: Article[];
  books: Book[];
  notes: Note[];
}

export default function Library() {
  const [q, setQ] = useState("");
  const [results, setResults] = useState<Results | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function search() {
    if (!q.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const result = await api.get<Results>(`/api/library/search?q=${encodeURIComponent(q)}`);
      setResults(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Search failed. Try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <div className="search-box">
        <div className="search-input-wrap">
          <SearchIcon />
          <input value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && search()} autoFocus />
        </div>
        <button className="primary" onClick={search} disabled={loading}>
          {loading ? "Searching..." : "Search"}
        </button>
        <UploadPdf compact />
      </div>

      {error && <p className="empty-state" style={{ color: "var(--color-accent)" }}>{error}</p>}

      {results && (
        <div>
          <h3>Papers ({results.papers.length})</h3>
          {results.papers.map((p) => (
            <ItemCard key={p.id} kind="paper" item={p} onStatusChange={search} />
          ))}
          <h3 style={{ marginTop: 24 }}>Books ({results.books.length})</h3>
          {results.books.map((b) => (
            <BookCard key={b.id} book={b} onStatusChange={search} />
          ))}
          <h3 style={{ marginTop: 24 }}>Journalism ({results.articles.length})</h3>
          {results.articles.map((a) => (
            <ItemCard key={a.id} kind="article" item={a} onStatusChange={search} />
          ))}
          <h3 style={{ marginTop: 24 }}>Notes ({results.notes.length})</h3>
          {results.notes.map((n) => (
            <div key={n.id} className="note-block">
              {n.quote_text && <div className="note-quote">"{n.quote_text}"</div>}
              <div>{n.note_text}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
