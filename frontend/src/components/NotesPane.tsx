import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Note } from "../types";
import AddToListButton from "./AddToListButton";

/** The split-view "Notes" pane slot (Phase 2 roadmap #1): a free-form
 * synthesis space, not anchored to whatever document is open in the other
 * pane — so it stays put as you swap documents in and out. */
export default function NotesPane() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [draft, setDraft] = useState("");
  const [tag, setTag] = useState("");
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);

  function load() {
    setLoading(true);
    api
      .get<Note[]>("/api/notes?freeform=true")
      .then(setNotes)
      .finally(() => setLoading(false));
  }

  useEffect(load, []);

  async function save() {
    if (!draft.trim() || saving) return;
    setSaving(true);
    try {
      await api.post("/api/notes", { note_text: draft.trim(), topic_tag: tag.trim() || null });
      setDraft("");
      load();
    } finally {
      setSaving(false);
    }
  }

  async function remove(id: string) {
    await api.del(`/api/notes/${id}`);
    load();
  }

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && (e.metaKey || e.ctrlKey) && save()}
          rows={4}
          style={{ width: "100%", marginBottom: 8 }}
        />
        <div style={{ display: "flex", gap: 8 }}>
          <input value={tag} onChange={(e) => setTag(e.target.value)} style={{ flex: 1 }} />
          <button className="primary" onClick={save} disabled={saving || !draft.trim()}>
            {saving ? "Saving..." : "Add note"}
          </button>
        </div>
      </div>

      {loading && <p className="empty-state">Loading...</p>}
      {!loading && notes.length === 0 && <p className="empty-state">No freeform notes yet.</p>}
      {notes.map((n) => (
        <div key={n.id} className="note-block">
          <div className="item-meta">
            <span>{new Date(n.created_at).toLocaleString()}</span>
            {n.topic_tag && <span className="tag">{n.topic_tag}</span>}
          </div>
          <div>{n.note_text}</div>
          <div style={{ display: "flex", gap: 8 }}>
            <AddToListButton itemType="note" itemId={n.id} />
            <button className="subtle" onClick={() => remove(n.id)}>
              Delete
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
