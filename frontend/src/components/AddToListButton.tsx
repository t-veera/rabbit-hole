import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import type { ItemType, RHList } from "../types";
import BookmarkIcon from "./BookmarkIcon";

interface Props {
  itemType: ItemType;
  itemId: string;
  className?: string;
}

export default function AddToListButton({ itemType, itemId, className }: Props) {
  const [open, setOpen] = useState(false);
  const [lists, setLists] = useState<RHList[]>([]);
  const [selected, setSelected] = useState("");
  const [newListName, setNewListName] = useState("");
  const [saved, setSaved] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open) api.get<RHList[]>("/api/lists").then(setLists);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    function handleOutsideClick(e: MouseEvent) {
      if (!containerRef.current?.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handleOutsideClick);
    return () => document.removeEventListener("mousedown", handleOutsideClick);
  }, [open]);

  async function addToSelected() {
    let listId = selected;
    if (!listId && newListName.trim()) {
      const created = await api.post<RHList>("/api/lists", { name: newListName.trim() });
      listId = created.id;
    }
    if (!listId) return;
    await api.post(`/api/lists/${listId}/items`, { item_type: itemType, item_id: itemId });
    setSaved(true);
    setOpen(false);
    setSelected("");
    setNewListName("");
    setTimeout(() => setSaved(false), 2000);
  }

  return (
    <div ref={containerRef} style={{ position: "relative", display: "inline-block" }}>
      <button
        className={className ?? "subtle"}
        onClick={() => setOpen((o) => !o)}
        style={{ display: "inline-flex", alignItems: "center", gap: 5 }}
        title="Add to list"
      >
        <BookmarkIcon filled={saved} />
        {saved ? "Added" : "Add to list"}
      </button>
      {open && (
        <div
          style={{
            position: "absolute",
            top: "calc(100% + 4px)",
            right: 0,
            background: "var(--color-bg-raised)",
            border: "1px solid var(--color-border-strong)",
            borderRadius: 6,
            padding: 12,
            width: 220,
            zIndex: 10,
          }}
        >
          <select value={selected} onChange={(e) => setSelected(e.target.value)} style={{ width: "100%", marginBottom: 8 }}>
            <option value="">Select a list...</option>
            {lists.map((l) => (
              <option key={l.id} value={l.id}>
                {l.name}
              </option>
            ))}
          </select>
          <input
            value={newListName}
            onChange={(e) => setNewListName(e.target.value)}
            style={{ width: "100%", marginBottom: 8 }}
          />
          <button className="primary" onClick={addToSelected} style={{ width: "100%" }}>
            Save
          </button>
        </div>
      )}
    </div>
  );
}
