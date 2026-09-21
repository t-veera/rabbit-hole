import { useEffect, useState } from "react";
import { api } from "../api/client";
import {
  applyReadingFont,
  applyReadingFontSize,
  getStoredReadingFont,
  getStoredReadingFontSize,
  READING_FONT_SIZES,
  READING_FONTS,
  type ReadingFont,
  type ReadingFontSize,
} from "../readingPrefs";
import type { AppSettings, Cadence, Source, SourceTrack, Topic } from "../types";
import { KNOWN_FIELDS } from "../types";

function sourceLabel(source: "settings" | "env" | "unset"): string {
  if (source === "settings") return "set here";
  if (source === "env") return "set via .env";
  return "not set";
}

function SecretKeyRow({
  label,
  hint,
  isSet,
  source,
  draft,
  onDraftChange,
  onSave,
  onClear,
  saving,
}: {
  label: string;
  hint: string;
  isSet: boolean;
  source: "settings" | "env" | "unset";
  draft: string;
  onDraftChange: (v: string) => void;
  onSave: () => void;
  onClear: () => void;
  saving: boolean;
}) {
  return (
    <div className="source-row" style={{ alignItems: "flex-start", flexWrap: "wrap", gap: 8 }}>
      <div style={{ flex: "1 1 260px" }}>
        <strong>{label}</strong>{" "}
        <span className="page-subtitle">({sourceLabel(source)})</span>
        <div className="page-subtitle">{hint}</div>
      </div>
      <div style={{ display: "flex", gap: 8, alignItems: "center", flex: "1 1 260px" }}>
        <input
          type="password"
          placeholder={isSet ? "•••••••• (leave blank to keep current)" : "Not set"}
          value={draft}
          onChange={(e) => onDraftChange(e.target.value)}
          style={{ flex: 1 }}
        />
        <button className="subtle" onClick={onSave} disabled={saving || !draft.trim()}>
          {saving ? "Saving..." : "Save"}
        </button>
        {source === "settings" && (
          <button className="subtle" onClick={onClear} disabled={saving} title="Fall back to .env (if set)">
            Clear
          </button>
        )}
      </div>
    </div>
  );
}

function PlainFieldRow({
  label,
  hint,
  value,
  source,
  onSave,
  saving,
}: {
  label: string;
  hint: string;
  value: string;
  source: "settings" | "env" | "unset";
  onSave: (v: string) => void;
  saving: boolean;
}) {
  const [draft, setDraft] = useState(value);
  useEffect(() => setDraft(value), [value]);
  return (
    <div className="source-row" style={{ alignItems: "flex-start", flexWrap: "wrap", gap: 8 }}>
      <div style={{ flex: "1 1 260px" }}>
        <strong>{label}</strong>{" "}
        <span className="page-subtitle">({sourceLabel(source)})</span>
        <div className="page-subtitle">{hint}</div>
      </div>
      <div style={{ display: "flex", gap: 8, alignItems: "center", flex: "1 1 260px" }}>
        <input value={draft} onChange={(e) => setDraft(e.target.value)} style={{ flex: 1 }} />
        <button className="subtle" onClick={() => onSave(draft)} disabled={saving || draft === value}>
          {saving ? "Saving..." : "Save"}
        </button>
      </div>
    </div>
  );
}

export default function Settings() {
  const [sources, setSources] = useState<Source[]>([]);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [field, setField] = useState("");
  const [track, setTrack] = useState<SourceTrack>("research");
  const [readingFont, setReadingFont] = useState<ReadingFont>(getStoredReadingFont());
  const [readingFontSize, setReadingFontSize] = useState<ReadingFontSize>(getStoredReadingFontSize());
  const [appSettings, setAppSettings] = useState<AppSettings | null>(null);
  const [keyDrafts, setKeyDrafts] = useState<Record<string, string>>({});
  const [savingField, setSavingField] = useState<string | null>(null);

  function loadAppSettings() {
    api.get<AppSettings>("/api/settings").then(setAppSettings);
  }

  useEffect(loadAppSettings, []);

  async function saveField(field: string, value: string) {
    setSavingField(field);
    try {
      const updated = await api.patch<AppSettings>("/api/settings", { [field]: value });
      setAppSettings(updated);
      setKeyDrafts((d) => ({ ...d, [field]: "" }));
    } finally {
      setSavingField(null);
    }
  }

  function chooseReadingFont(choice: ReadingFont) {
    setReadingFont(choice);
    applyReadingFont(choice);
  }

  function chooseReadingFontSize(choice: ReadingFontSize) {
    setReadingFontSize(choice);
    applyReadingFontSize(choice);
  }

  function load() {
    api.get<Source[]>("/api/sources").then(setSources);
    api.get<Topic[]>("/api/topics").then(setTopics);
  }

  useEffect(load, []);

  async function addSource() {
    if (!name.trim() || !url.trim()) return;
    await api.post("/api/sources", { name, url, kind: "rss", track, field: field || null, priority: 0 });
    setName("");
    setUrl("");
    setField("");
    load();
  }

  async function removeSource(id: string) {
    await api.del(`/api/sources/${id}`);
    load();
  }

  async function updateCadence(id: string, cadence: Cadence) {
    await api.patch(`/api/topics/${id}`, { cadence });
    load();
  }

  async function removeTopic(id: string) {
    await api.del(`/api/topics/${id}`);
    load();
  }

  return (
    <div>
      <h3>Reading view</h3>
      <div className="page-subtitle" style={{ marginBottom: 16 }}>
        Font and size for the article/paper reading view. Saved to this browser.
      </div>
      <div className="form-row">
        <label>Body font</label>
        <select value={readingFont} onChange={(e) => chooseReadingFont(e.target.value as ReadingFont)}>
          {READING_FONTS.map((f) => (
            <option key={f.value} value={f.value}>
              {f.label}
            </option>
          ))}
        </select>
      </div>
      <div className="form-row">
        <label>Font size</label>
        <div className="size-toggle">
          {READING_FONT_SIZES.map((s) => (
            <button
              key={s.value}
              type="button"
              className={readingFontSize === s.value ? "active" : ""}
              onClick={() => chooseReadingFontSize(s.value)}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>
      <div
        className="reading-font-preview article-body"
        style={{ fontFamily: READING_FONTS.find((f) => f.value === readingFont)?.family, fontSize: READING_FONT_SIZES.find((s) => s.value === readingFontSize)?.px }}
      >
        <p style={{ margin: 0 }}>
          The quick brown fox jumps over the lazy dog — a preview of how the reading view will look.
        </p>
      </div>

      <h3 style={{ marginTop: 40 }}>API keys</h3>
      <div className="page-subtitle" style={{ marginBottom: 16 }}>
        All optional — the app runs without any of these, just with dumber search-term
        translation and weaker full-text/rate-limit coverage. Saved here take effect
        immediately (no restart) and override backend/.env.
      </div>
      {appSettings && (
        <div className="list-grid" style={{ marginBottom: 40 }}>
          <SecretKeyRow
            label="Anthropic API key"
            hint="Real search-term translation instead of a naive keyword pass"
            isSet={appSettings.anthropic_api_key_set}
            source={appSettings.anthropic_api_key_source}
            draft={keyDrafts.anthropic_api_key ?? ""}
            onDraftChange={(v) => setKeyDrafts((d) => ({ ...d, anthropic_api_key: v }))}
            onSave={() => saveField("anthropic_api_key", keyDrafts.anthropic_api_key ?? "")}
            onClear={() => saveField("anthropic_api_key", "")}
            saving={savingField === "anthropic_api_key"}
          />
          <PlainFieldRow
            label="Unpaywall email"
            hint="Required by Unpaywall's usage terms — must be a real address, or every open-access lookup silently fails"
            value={appSettings.unpaywall_email ?? ""}
            source={appSettings.unpaywall_email_source}
            onSave={(v) => saveField("unpaywall_email", v)}
            saving={savingField === "unpaywall_email"}
          />
          <PlainFieldRow
            label="OpenAlex contact email"
            hint="Gets OpenAlex's faster 'polite pool' rate limit"
            value={appSettings.openalex_mailto ?? ""}
            source={appSettings.openalex_mailto_source}
            onSave={(v) => saveField("openalex_mailto", v)}
            saving={savingField === "openalex_mailto"}
          />
          <SecretKeyRow
            label="NCBI API key"
            hint="Raises PubMed's rate limit from 3 to 10 requests/sec"
            isSet={appSettings.ncbi_api_key_set}
            source={appSettings.ncbi_api_key_source}
            draft={keyDrafts.ncbi_api_key ?? ""}
            onDraftChange={(v) => setKeyDrafts((d) => ({ ...d, ncbi_api_key: v }))}
            onSave={() => saveField("ncbi_api_key", keyDrafts.ncbi_api_key ?? "")}
            onClear={() => saveField("ncbi_api_key", "")}
            saving={savingField === "ncbi_api_key"}
          />
          <SecretKeyRow
            label="CORE.ac.uk API key"
            hint="Finds institutional-repository PDF copies Unpaywall/OpenAlex miss"
            isSet={appSettings.core_api_key_set}
            source={appSettings.core_api_key_source}
            draft={keyDrafts.core_api_key ?? ""}
            onDraftChange={(v) => setKeyDrafts((d) => ({ ...d, core_api_key: v }))}
            onSave={() => saveField("core_api_key", keyDrafts.core_api_key ?? "")}
            onClear={() => saveField("core_api_key", "")}
            saving={savingField === "core_api_key"}
          />
          <SecretKeyRow
            label="Semantic Scholar API key"
            hint="Reserved for future use — not called by anything yet"
            isSet={appSettings.semantic_scholar_api_key_set}
            source={appSettings.semantic_scholar_api_key_source}
            draft={keyDrafts.semantic_scholar_api_key ?? ""}
            onDraftChange={(v) => setKeyDrafts((d) => ({ ...d, semantic_scholar_api_key: v }))}
            onSave={() => saveField("semantic_scholar_api_key", keyDrafts.semantic_scholar_api_key ?? "")}
            onClear={() => saveField("semantic_scholar_api_key", "")}
            saving={savingField === "semantic_scholar_api_key"}
          />
        </div>
      )}

      <h3 style={{ marginTop: 40 }}>Custom sources</h3>
      <div className="page-subtitle" style={{ marginBottom: 16 }}>
        Journals, RSS feeds, or sites you add here are searched first, before the broader API set.
      </div>
      <div className="inline-form" style={{ flexWrap: "wrap" }}>
        <div className="form-row">
          <label>Name</label>
          <input value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div className="form-row">
          <label>Feed URL</label>
          <input value={url} onChange={(e) => setUrl(e.target.value)} />
        </div>
        <div className="form-row">
          <label>Track</label>
          <select value={track} onChange={(e) => setTrack(e.target.value as SourceTrack)}>
            <option value="research">Research</option>
            <option value="journalism">Journalism</option>
          </select>
        </div>
        <div className="form-row">
          <label>Field (optional)</label>
          <select value={field} onChange={(e) => setField(e.target.value)}>
            <option value="">Any</option>
            {KNOWN_FIELDS.map((f) => (
              <option key={f} value={f}>
                {f.replace("_", " ")}
              </option>
            ))}
          </select>
        </div>
        <button className="primary" onClick={addSource}>
          Add source
        </button>
      </div>

      <div className="list-grid" style={{ marginBottom: 40 }}>
        {sources.map((s) => (
          <div key={s.id} className="source-row">
            <div>
              <strong>{s.name}</strong>{" "}
              <span className="page-subtitle">
                ({s.track}{s.field ? `, ${s.field.replace("_", " ")}` : ""})
              </span>
            </div>
            {s.is_user_added ? (
              <button className="subtle" onClick={() => removeSource(s.id)}>
                Remove
              </button>
            ) : (
              <span className="tag">built-in</span>
            )}
          </div>
        ))}
      </div>

      <h3>Topics &amp; digest cadence</h3>
      <div className="page-subtitle" style={{ marginBottom: 16 }}>
        Controls how often the background scheduler refreshes each saved topic.
      </div>
      <div className="list-grid">
        {topics.length === 0 && <p className="empty-state">No saved topics yet — save one from the Search page.</p>}
        {topics.map((t) => (
          <div key={t.id} className="topic-row">
            <div>
              <strong>{t.raw_query}</strong>
              <div className="page-subtitle">{t.translated_query}</div>
            </div>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <select value={t.cadence} onChange={(e) => updateCadence(t.id, e.target.value as Cadence)}>
                <option value="realtime">Real-time (~15 min)</option>
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
              </select>
              <button className="subtle" onClick={() => removeTopic(t.id)}>
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
