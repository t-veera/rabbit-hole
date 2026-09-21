import { useEffect, useState } from "react";
import { API_BASE, api } from "../api/client";
import type { Note } from "../types";
import AddToListButton from "../components/AddToListButton";

export default function Notes() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [tag, setTag] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [titles, setTitles] = useState<Record<string, string>>({});
  const [creating, setCreating] = useState(false);
  const [draft, setDraft] = useState("");
  const [draftTag, setDraftTag] = useState("");
  const [saving, setSaving] = useState(false);

  function load() {
    const params = new URLSearchParams();
    if (tag) params.set("topic_tag", tag);
    if (dateFrom) params.set("date_from", dateFrom);
    if (dateTo) params.set("date_to", dateTo);
    api.get<Note[]>(`/api/notes?${params.toString()}`).then(async (result) => {
      setNotes(result);
      const paperIds = [...new Set(result.filter((n) => n.item_type === "paper").map((n) => n.item_id))];
      const articleIds = [...new Set(result.filter((n) => n.item_type === "article").map((n) => n.item_id))];
      const map: Record<string, string> = {};
      await Promise.all(
        paperIds.map((id) =>
          api
            .get<{ title: string }>(`/api/papers/${id}`)
            .then((p) => (map[`paper:${id}`] = p.title))
            .catch(() => {})
        )
      );
      await Promise.all(
        articleIds.map((id) =>
          api
            .get<{ title: string }>(`/api/journalism/${id}`)
            .then((a) => (map[`article:${id}`] = a.title))
            .catch(() => {})
        )
      );
      setTitles(map);
    });
  }

  useEffect(load, [tag, dateFrom, dateTo]);

  async function remove(id: string) {
    await api.del(`/api/notes/${id}`);
    load();
  }

  async function createNote() {
    if (!draft.trim() || saving) return;
    setSaving(true);
    try {
      await api.post("/api/notes", { note_text: draft.trim(), topic_tag: draftTag.trim() || null });
      setDraft("");
      setDraftTag("");
      setCreating(false);
      load();
    } finally {
      setSaving(false);
    }
  }

  const exportParams = new URLSearchParams();
  if (tag) exportParams.set("topic_tag", tag);
  if (dateFrom) exportParams.set("date_from", dateFrom);
  if (dateTo) exportParams.set("date_to", dateTo);

  return (
    <div>
      <div className="field-filters">
        <input value={tag} onChange={(e) => setTag(e.target.value)} />
        <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
        <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
        <a className="btn" href={`${API_BASE}/api/notes/export/run?format=markdown&${exportParams.toString()}`} target="_blank" rel="noreferrer">
          Export Markdown
        </a>
        <a className="btn" href={`${API_BASE}/api/notes/export/run?format=text&${exportParams.toString()}`} target="_blank" rel="noreferrer">
          Export Text
        </a>
        <button className="primary" onClick={() => setCreating((c) => !c)} style={{ marginLeft: "auto" }}>
          {creating ? "Cancel" : "Create note"}
        </button>
      </div>

      {creating && (
        <div className="note-create-form">
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && (e.metaKey || e.ctrlKey) && createNote()}
            rows={4}
            autoFocus
          />
          <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
            <input value={draftTag} onChange={(e) => setDraftTag(e.target.value)} style={{ flex: 1 }} />
            <button className="primary" onClick={createNote} disabled={saving || !draft.trim()}>
              {saving ? "Saving..." : "Save note"}
            </button>
          </div>
        </div>
      )}

      {notes.length === 0 && <p className="empty-state">No notes yet — highlight text on any paper or article to add one.</p>}
      {notes.map((n) => (
        <div key={n.id} className="note-block">
          <div className="item-meta">
            <span>{n.item_id ? titles[`${n.item_type}:${n.item_id}`] ?? "..." : "Freeform note"}</span>
            <span>&middot;</span>
            <span>{new Date(n.created_at).toLocaleDateString()}</span>
            {n.topic_tag && <span className="tag">{n.topic_tag}</span>}
          </div>
          {n.quote_text && <div className="note-quote">"{n.quote_text}"</div>}
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
