import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { API_BASE, api } from "../api/client";
import type { Article, Book, ListItemRow, Note, Paper } from "../types";
import ItemCard from "../components/ItemCard";
import BookCard from "../components/BookCard";

export default function ListDetail() {
  const { id } = useParams<{ id: string }>();
  const [rows, setRows] = useState<ListItemRow[]>([]);
  const [papers, setPapers] = useState<Record<string, Paper>>({});
  const [articles, setArticles] = useState<Record<string, Article>>({});
  const [books, setBooks] = useState<Record<string, Book>>({});
  const [notes, setNotes] = useState<Record<string, Note>>({});
  const [loading, setLoading] = useState(true);

  // A row can outlive the thing it points to (item_id isn't a real FK — see
  // backend/app/models.py ListItem) — a single missing item must not sink
  // the whole page in a permanent "Loading...": fetch each defensively and
  // drop only that row instead of failing the whole Promise.all.
  function fetchOrNull<T>(path: string): Promise<T | null> {
    return api.get<T>(path).catch(() => null);
  }

  async function load() {
    if (!id) return;
    setLoading(true);
    const items = await api.get<ListItemRow[]>(`/api/lists/${id}/items`);
    setRows(items);
    const paperEntries = await Promise.all(
      items.filter((i) => i.item_type === "paper").map((i) => fetchOrNull<Paper>(`/api/papers/${i.item_id}`))
    );
    const articleEntries = await Promise.all(
      items
        .filter((i) => i.item_type === "article")
        .map((i) => fetchOrNull<Article>(`/api/journalism/${i.item_id}`))
    );
    const bookEntries = await Promise.all(
      items.filter((i) => i.item_type === "book").map((i) => fetchOrNull<Book>(`/api/books/${i.item_id}`))
    );
    const noteEntries = await Promise.all(
      items.filter((i) => i.item_type === "note").map((i) => fetchOrNull<Note>(`/api/notes/${i.item_id}`))
    );
    setPapers(Object.fromEntries(paperEntries.filter((p): p is Paper => p !== null).map((p) => [p.id, p])));
    setArticles(Object.fromEntries(articleEntries.filter((a): a is Article => a !== null).map((a) => [a.id, a])));
    setBooks(Object.fromEntries(bookEntries.filter((b): b is Book => b !== null).map((b) => [b.id, b])));
    setNotes(Object.fromEntries(noteEntries.filter((n): n is Note => n !== null).map((n) => [n.id, n])));
    setLoading(false);
  }

  useEffect(() => {
    load();
  }, [id]);

  async function removeItem(rowId: string) {
    await api.del(`/api/lists/${id}/items/${rowId}`);
    load();
  }

  if (loading) return <p className="empty-state">Loading...</p>;

  return (
    <div>
      <div className="page-header">
        <h1>List</h1>
        <div style={{ display: "flex", gap: 8 }}>
          <a className="btn" href={`${API_BASE}/api/lists/${id}/export?format=bibtex`} target="_blank" rel="noreferrer">
            Export BibTeX
          </a>
          <a className="btn" href={`${API_BASE}/api/lists/${id}/export?format=ris`} target="_blank" rel="noreferrer">
            Export RIS
          </a>
        </div>
      </div>
      {rows.length === 0 && <p className="empty-state">This list is empty.</p>}
      {rows.map((row) => {
        if (row.item_type === "book") {
          const book = books[row.item_id];
          if (!book) return null;
          return (
            <div key={row.id} style={{ position: "relative" }}>
              <BookCard book={book} />
              <button className="subtle" style={{ position: "absolute", top: 20, right: 0 }} onClick={() => removeItem(row.id)}>
                Remove from list
              </button>
            </div>
          );
        }
        if (row.item_type === "note") {
          const note = notes[row.item_id];
          if (!note) return null;
          return (
            <div key={row.id} className="note-block">
              {note.quote_text && <div className="note-quote">"{note.quote_text}"</div>}
              <div>{note.note_text}</div>
              <button className="subtle" onClick={() => removeItem(row.id)}>
                Remove from list
              </button>
            </div>
          );
        }
        const item = row.item_type === "paper" ? papers[row.item_id] : articles[row.item_id];
        if (!item) return null;
        return (
          <div key={row.id} style={{ position: "relative" }}>
            <ItemCard kind={row.item_type} item={item} onStatusChange={load} />
            <button className="subtle" style={{ position: "absolute", top: 20, right: 0 }} onClick={() => removeItem(row.id)}>
              Remove from list
            </button>
          </div>
        );
      })}
    </div>
  );
}
