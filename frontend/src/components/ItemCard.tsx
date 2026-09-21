import { useEffect, useState, type MouseEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import type { Article, Paper, ReadingState } from "../types";
import { api } from "../api/client";
import AddToListButton from "./AddToListButton";
import LinkItemButton from "./LinkItemButton";

function formatDate(iso: string | null): string {
  if (!iso) return "undated";
  return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

function snippet(text: string, maxLength = 480): string {
  const firstParagraph = text.split(/\n\s*\n|\r\n\r\n/)[0].trim();
  if (firstParagraph.length <= maxLength) return firstParagraph;
  const cut = firstParagraph.slice(0, maxLength);
  const lastSpace = cut.lastIndexOf(" ");
  return (lastSpace > maxLength * 0.6 ? cut.slice(0, lastSpace) : cut).trimEnd() + "…";
}

interface Props {
  kind: "paper" | "article";
  item: Paper | Article;
  onStatusChange?: () => void;
}

export default function ItemCard({ kind, item, onStatusChange }: Props) {
  const isPaper = kind === "paper";
  const paper = isPaper ? (item as Paper) : null;
  const article = !isPaper ? (item as Article) : null;
  const detailPath = isPaper ? `/papers/${item.id}` : `/articles/${item.id}`;
  const status = item.reading_status?.status ?? "unread";
  const navigate = useNavigate();
  const [menuPos, setMenuPos] = useState<{ x: number; y: number } | null>(null);

  useEffect(() => {
    if (!menuPos) return;
    function close() {
      setMenuPos(null);
    }
    document.addEventListener("click", close);
    document.addEventListener("contextmenu", close);
    document.addEventListener("keydown", close);
    return () => {
      document.removeEventListener("click", close);
      document.removeEventListener("contextmenu", close);
      document.removeEventListener("keydown", close);
    };
  }, [menuPos]);

  function openContextMenu(e: MouseEvent) {
    e.preventDefault();
    setMenuPos({ x: e.clientX, y: e.clientY });
  }

  function openInSplitView() {
    navigate(`/split?a=${kind}:${item.id}`);
  }

  async function setStatus(next: ReadingState) {
    await api.patch(`/api/items/${kind}/${item.id}/status`, { status: next });
    onStatusChange?.();
  }

  async function toggleQueue() {
    const nextQueue = !(item.reading_status?.in_queue ?? false);
    await api.patch(`/api/items/${kind}/${item.id}/status`, { in_queue: nextQueue });
    onStatusChange?.();
  }

  async function dismiss() {
    await api.post(`/api/papers/${item.id}/dismiss`);
    onStatusChange?.();
  }

  return (
    <div className="item-card" onContextMenu={openContextMenu}>
      {menuPos && (
        <div className="context-menu" style={{ left: menuPos.x, top: menuPos.y }}>
          <button onClick={openInSplitView}>Open in split view</button>
        </div>
      )}
      <div className="item-eyebrow">
        {item.origin_source?.name ?? (paper ? paper.venue ?? "Discovered" : "Journalism")}
      </div>
      <div className="item-title">
        <Link to={detailPath}>{item.title}</Link>
      </div>
      {paper && paper.authors.length > 0 && (
        <div className="item-authors">
          {paper.authors.slice(0, 5).map((a, i) => (
            <span key={a.researcher.id}>
              {i > 0 && ", "}
              <Link to={`/researchers/${a.researcher.id}`} className="item-authors-link">
                {a.researcher.name}
              </Link>
            </span>
          ))}
          {paper.authors.length > 5 ? " et al." : ""}
        </div>
      )}
      {article?.author_name && (
        <div className="item-authors">
          {article.author_researcher_id ? (
            <Link to={`/researchers/${article.author_researcher_id}`} className="item-authors-link">
              {article.author_name}
            </Link>
          ) : (
            article.author_name
          )}
        </div>
      )}
      <div className="item-meta">
        <span className="tag tag-kind">{isPaper ? "Paper" : "Article"}</span>
        <span>·</span>
        <span>{formatDate(item.published_date)}</span>
        {(paper ? paper.origin === "source" : article?.is_from_user_source) && (
          <>
            <span>·</span>
            <span className="tag tag-mine">From your sources</span>
          </>
        )}
        {paper?.origin === "uploaded" && (
          <>
            <span>·</span>
            <span className="tag tag-mine">Uploaded</span>
          </>
        )}
        {status !== "unread" && (
          <>
            <span>·</span>
            <span className="tag">{status}</span>
          </>
        )}
      </div>
      {(paper?.abstract || article?.summary) && (
        <div className="item-abstract">{snippet(paper?.abstract || article?.summary || "")}</div>
      )}
      <div className="item-actions">
        <button className="subtle" onClick={() => setStatus(status === "read" ? "unread" : "read")}>
          {status === "read" ? "Mark unread" : "Mark read"}
        </button>
        <button className="subtle" onClick={() => setStatus("skimmed")}>
          Mark skimmed
        </button>
        <button className="subtle" onClick={toggleQueue}>
          {item.reading_status?.in_queue ? "Remove from queue" : "Add to queue"}
        </button>
        <AddToListButton itemType={kind} itemId={item.id} />
        <LinkItemButton itemType={kind} itemId={item.id} />
        {isPaper && (
          <button className="subtle" onClick={dismiss} title="Remove from feed — use the topic's Reset to bring it back">
            Remove
          </button>
        )}
      </div>
    </div>
  );
}
