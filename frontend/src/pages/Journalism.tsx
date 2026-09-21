import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Article } from "../types";
import ItemCard from "../components/ItemCard";

export default function Journalism() {
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);

  function load() {
    setLoading(true);
    api
      .get<Article[]>("/api/journalism")
      .then(setArticles)
      .finally(() => setLoading(false));
  }

  useEffect(load, []);

  return (
    <div>
      <div className="page-header">
        <h1>Journalism</h1>
      </div>
      {loading && <p className="empty-state">Loading...</p>}
      {!loading && articles.length === 0 && (
        <p className="empty-state">
          No journalism items yet — run a search on the Search page, or wait for the next scheduled
          refresh.
        </p>
      )}
      {articles.map((a) => (
        <ItemCard key={a.id} kind="article" item={a} onStatusChange={load} />
      ))}
    </div>
  );
}
