import {
  Children,
  cloneElement,
  isValidElement,
  useEffect,
  useRef,
  useState,
  type MouseEvent,
  type ReactElement,
  type ReactNode,
} from "react";
import type { ItemType, Note } from "../types";
import { api } from "../api/client";
import type { ProseHighlight } from "./Prose";

interface Props {
  itemType: ItemType;
  itemId: string;
  children: ReactNode;
  onNoteSaved?: () => void;
}

export default function Highlighter({ itemType, itemId, children, onNoteSaved }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [popover, setPopover] = useState<{ x: number; y: number; quote: string } | null>(null);
  const [composing, setComposing] = useState(false);
  const [noteText, setNoteText] = useState("");
  const [tag, setTag] = useState("");
  const [highlights, setHighlights] = useState<Note[]>([]);
  const [viewing, setViewing] = useState<{ x: number; y: number; note: Note } | null>(null);

  function loadHighlights() {
    api
      .get<Note[]>(`/api/notes?item_type=${itemType}&item_id=${itemId}`)
      .then((notes) => setHighlights(notes.filter((n) => n.quote_text)))
      .catch(() => {});
  }

  useEffect(loadHighlights, [itemType, itemId]);

  useEffect(() => {
    if (!popover && !viewing) return;
    function handleOutsideClick(e: globalThis.MouseEvent) {
      const target = e.target as HTMLElement;
      // Clicking the highlighted mark itself re-opens the same popover via
      // handleClick above — don't fight that click here.
      if (target.closest(".highlight-popover") || target.closest("mark.note-highlight")) return;
      closePopover();
      setViewing(null);
    }
    document.addEventListener("mousedown", handleOutsideClick);
    return () => document.removeEventListener("mousedown", handleOutsideClick);
  }, [popover, viewing]);

  function closePopover() {
    setPopover(null);
    setComposing(false);
    setNoteText("");
    setTag("");
  }

  function handleMouseUp() {
    const selection = window.getSelection();
    const text = selection?.toString().trim();
    if (!text || !containerRef.current?.contains(selection?.anchorNode ?? null)) {
      return;
    }
    const range = selection!.getRangeAt(0);
    const rect = range.getBoundingClientRect();
    setViewing(null);
    setPopover({ x: rect.left + rect.width / 2, y: rect.top - 36, quote: text });
    setComposing(false);
  }

  function handleClick(e: MouseEvent) {
    const mark = (e.target as HTMLElement).closest<HTMLElement>("mark.note-highlight");
    if (!mark) return;
    const noteId = mark.dataset.noteId;
    const note = highlights.find((n) => n.id === noteId);
    if (!note) return;
    const rect = mark.getBoundingClientRect();
    setPopover(null);
    setViewing({ x: rect.left + rect.width / 2, y: rect.top - 36, note });
  }

  async function saveNote() {
    if (!popover) return;
    await api.post("/api/notes", {
      item_type: itemType,
      item_id: itemId,
      quote_text: popover.quote,
      note_text: noteText || "(highlight)",
      topic_tag: tag || null,
    });
    setPopover(null);
    setNoteText("");
    setTag("");
    loadHighlights();
    onNoteSaved?.();
  }

  async function deleteHighlight(noteId: string) {
    await api.del(`/api/notes/${noteId}`);
    setViewing(null);
    loadHighlights();
    onNoteSaved?.();
  }

  const proseHighlights: ProseHighlight[] = highlights.map((n) => ({ id: n.id, quote_text: n.quote_text! }));
  const enrichedChildren = Children.map(children, (child) =>
    isValidElement(child) ? cloneElement(child as ReactElement<{ highlights?: ProseHighlight[] }>, { highlights: proseHighlights }) : child
  );

  return (
    <div ref={containerRef} onMouseUp={handleMouseUp} onClick={handleClick} style={{ position: "relative" }}>
      {enrichedChildren}
      {popover && !composing && (
        <div className="highlight-popover" style={{ left: popover.x, top: popover.y }}>
          <button onClick={() => setComposing(true)}>Add note</button>
        </div>
      )}
      {popover && composing && (
        <div className="highlight-popover" style={{ left: popover.x, top: popover.y, flexDirection: "column", alignItems: "stretch" }}>
          <textarea
            autoFocus
            value={noteText}
            onChange={(e) => setNoteText(e.target.value)}
            rows={2}
            style={{ minWidth: 220 }}
          />
          <input value={tag} onChange={(e) => setTag(e.target.value)} />
          <div style={{ display: "flex", gap: 6 }}>
            <button onClick={saveNote}>Save</button>
            <button onClick={closePopover}>Cancel</button>
          </div>
        </div>
      )}
      {viewing && (
        <div className="highlight-popover" style={{ left: viewing.x, top: viewing.y, flexDirection: "column", alignItems: "stretch", maxWidth: 280 }}>
          <div>{viewing.note.note_text}</div>
          <div style={{ display: "flex", gap: 6 }}>
            <button onClick={() => deleteHighlight(viewing.note.id)}>Delete</button>
            <button onClick={() => setViewing(null)}>Close</button>
          </div>
        </div>
      )}
    </div>
  );
}
