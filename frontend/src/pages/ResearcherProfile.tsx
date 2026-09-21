import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import type { Researcher } from "../types";

interface PublicationStub {
  title: string;
  openalex_id: string | null;
  doi: string | null;
  published_date: string | null;
}

export default function ResearcherProfile() {
  const { id } = useParams<{ id: string }>();
  const [researcher, setResearcher] = useState<Researcher | null>(null);
  const [publications, setPublications] = useState<PublicationStub[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    Promise.all([
      api.get<Researcher>(`/api/researchers/${id}?enrich=true`),
      api.get<PublicationStub[]>(`/api/researchers/${id}/publications`),
    ])
      .then(([r, pubs]) => {
        setResearcher(r);
        setPublications(pubs);
      })
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <p className="empty-state">Loading...</p>;
  if (!researcher) return <p className="empty-state">Researcher not found.</p>;

  const initials = researcher.name
    .split(" ")
    .map((p) => p[0])
    .slice(0, 2)
    .join("");

  return (
    <div>
      <div className="researcher-header">
        <div className="avatar avatar-lg">
          {researcher.photo_url ? <img src={researcher.photo_url} alt={researcher.name} /> : initials}
        </div>
        <div>
          <h1 style={{ marginBottom: 4 }}>{researcher.name}</h1>
          <div className="page-subtitle">
            {[researcher.degree, researcher.affiliation].filter(Boolean).join(" · ") || "No affiliation on file"}
          </div>
          {researcher.email && <div className="page-subtitle">{researcher.email}</div>}
          {researcher.orcid && (
            <div className="page-subtitle">
              <a href={`https://orcid.org/${researcher.orcid}`} target="_blank" rel="noreferrer">
                ORCID: {researcher.orcid}
              </a>
            </div>
          )}
        </div>
      </div>

      <h3>Recent publications</h3>
      {publications.length === 0 && <p className="empty-state">No publication history found via OpenAlex.</p>}
      {publications.map((p, i) => {
        const externalUrl = p.doi
          ? `https://doi.org/${p.doi}`
          : p.openalex_id ?? null;
        return (
          <div key={i} className="item-card">
            <div className="item-title">
              {externalUrl ? (
                <a href={externalUrl} target="_blank" rel="noreferrer">
                  {p.title}
                </a>
              ) : (
                p.title
              )}
            </div>
            <div className="item-meta">
              <span>{p.published_date ?? "undated"}</span>
              {p.doi && <span>· {p.doi}</span>}
            </div>
          </div>
        );
      })}
    </div>
  );
}
