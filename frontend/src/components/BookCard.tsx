import type { Book } from "../types";
import { api } from "../api/client";

interface Props {
  book: Book;
  onStatusChange?: () => void;
}

export default function BookCard({ book, onStatusChange }: Props) {
  const status = book.reading_status?.status ?? "unread";

  async function setStatus(next: "read" | "unread" | "skimmed") {
    await api.patch(`/api/items/book/${book.id}/status`, { status: next });
    onStatusChange?.();
  }

  async function toggleQueue() {
    await api.patch(`/api/items/book/${book.id}/status`, {
      in_queue: !(book.reading_status?.in_queue ?? false),
    });
    onStatusChange?.();
  }

  return (
    <div className="item-card book-card">
      {book.cover_url && <img src={book.cover_url} alt="" className="book-cover" />}
      <div>
        <div className="item-eyebrow">Book</div>
        <div className="item-title">
          {book.open_library_url ? (
            <a href={book.open_library_url} target="_blank" rel="noreferrer">
              {book.title}
            </a>
          ) : (
            book.title
          )}
        </div>
        <div className="item-authors">
          {(book.authors ?? []).join(", ")}
          {book.first_publish_year ? ` · ${book.first_publish_year}` : ""}
        </div>
        {book.description && <div className="item-abstract">{book.description}</div>}
        <div className="item-actions">
          <button className="subtle" onClick={() => setStatus(status === "read" ? "unread" : "read")}>
            {status === "read" ? "Mark unread" : "Mark read"}
          </button>
          <button className="subtle" onClick={toggleQueue}>
            {book.reading_status?.in_queue ? "Remove from queue" : "Add to queue"}
          </button>
        </div>
      </div>
    </div>
  );
}
