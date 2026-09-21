import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { RHList } from "../types";

export default function Lists() {
  const [lists, setLists] = useState<RHList[]>([]);
  const [name, setName] = useState("");

  function load() {
    api.get<RHList[]>("/api/lists").then(setLists);
  }

  useEffect(load, []);

  async function create() {
    if (!name.trim()) return;
    await api.post("/api/lists", { name: name.trim() });
    setName("");
    load();
  }

  async function remove(id: string) {
    await api.del(`/api/lists/${id}`);
    load();
  }

  return (
    <div>
      <div className="list-create-row">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && create()}
        />
        <button className="primary" onClick={create}>
          Create
        </button>
      </div>

      <div className="list-grid">
        {lists.length === 0 && <p className="empty-state">No lists yet.</p>}
        {lists.map((l) => (
          <div key={l.id} className="source-row">
            <Link to={`/lists/${l.id}`}>{l.name}</Link>
            <button className="subtle" onClick={() => remove(l.id)}>
              Delete
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
