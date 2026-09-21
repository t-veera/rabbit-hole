import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { Paper, UploadDraft } from "../types";

type Step = "closed" | "picking" | "extracting" | "reviewing" | "saving";

interface Props {
  /** Compact inline variant for the paper-detail fallback; full button otherwise. */
  compact?: boolean;
}

export default function UploadPdf({ compact }: Props) {
  const [step, setStep] = useState<Step>("closed");
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState<UploadDraft | null>(null);
  const [title, setTitle] = useState("");
  const [authorsText, setAuthorsText] = useState("");
  const [publishedDate, setPublishedDate] = useState("");
  const [venue, setVenue] = useState("");
  const [doi, setDoi] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  function reset() {
    setStep("closed");
    setError(null);
    setDraft(null);
    setTitle("");
    setAuthorsText("");
    setPublishedDate("");
    setVenue("");
    setDoi("");
  }

  async function handleFile(file: File) {
    if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
      setError("Only PDF files are supported.");
      setStep("picking");
      return;
    }
    setStep("extracting");
    setError(null);
    try {
      const result = await api.upload<UploadDraft>("/api/papers/upload", file);
      setDraft(result);
      setTitle(result.suggested_title || "");
      setAuthorsText(result.suggested_authors.join(", "));
      setDoi(result.suggested_doi || "");
      setStep("reviewing");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed.");
      setStep("picking");
    }
  }

  async function confirm() {
    if (!draft || !title.trim()) return;
    setStep("saving");
    try {
      const paper = await api.post<Paper>("/api/papers/upload/confirm", {
        title: title.trim(),
        authors: authorsText
          .split(",")
          .map((a) => a.trim())
          .filter(Boolean),
        published_date: publishedDate || null,
        venue: venue.trim() || null,
        doi: doi.trim() || null,
        full_text: draft.full_text,
      });
      reset();
      navigate(`/papers/${paper.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't save this paper.");
      setStep("reviewing");
    }
  }

  if (step === "closed") {
    return (
      <button className={compact ? "btn" : "primary"} onClick={() => setStep("picking")}>
        Upload PDF
      </button>
    );
  }

  return (
    <div className="upload-overlay" onClick={reset}>
      <div className="upload-panel" onClick={(e) => e.stopPropagation()}>
        {(step === "picking" || step === "extracting") && (
          <>
            <h3>Upload a paper</h3>
            <div
              className={"upload-dropzone" + (dragOver ? " drag-over" : "")}
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragOver(false);
                const file = e.dataTransfer.files[0];
                if (file) handleFile(file);
              }}
              onClick={() => fileInputRef.current?.click()}
            >
              {step === "extracting" ? (
                <p>Extracting text...</p>
              ) : (
                <p>Drag a PDF here, or click to choose a file</p>
              )}
              <input
                ref={fileInputRef}
                type="file"
                accept="application/pdf"
                hidden
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) handleFile(file);
                }}
              />
            </div>
            {error && <p className="page-subtitle" style={{ color: "var(--color-accent)" }}>{error}</p>}
            <button className="subtle" onClick={reset}>
              Cancel
            </button>
          </>
        )}

        {(step === "reviewing" || step === "saving") && draft && (
          <>
            <h3>Confirm details</h3>
            <p className="page-subtitle" style={{ marginBottom: 16 }}>
              Pulled from the PDF where possible ({draft.page_count} pages extracted) — fix anything
              that's wrong or missing.
            </p>
            <div className="form-row">
              <label>Title</label>
              <input value={title} onChange={(e) => setTitle(e.target.value)} />
            </div>
            <div className="form-row">
              <label>Authors (comma-separated)</label>
              <input value={authorsText} onChange={(e) => setAuthorsText(e.target.value)} />
            </div>
            <div className="form-row">
              <label>Published date</label>
              <input type="date" value={publishedDate} onChange={(e) => setPublishedDate(e.target.value)} />
            </div>
            <div className="form-row">
              <label>Venue / journal (optional)</label>
              <input value={venue} onChange={(e) => setVenue(e.target.value)} />
            </div>
            <div className="form-row">
              <label>DOI (optional — enables citation-graph enrichment)</label>
              <input value={doi} onChange={(e) => setDoi(e.target.value)} />
            </div>
            {error && <p className="page-subtitle" style={{ color: "var(--color-accent)" }}>{error}</p>}
            <div style={{ display: "flex", gap: 8 }}>
              <button className="primary" onClick={confirm} disabled={!title.trim() || step === "saving"}>
                {step === "saving" ? "Saving..." : "Save paper"}
              </button>
              <button className="subtle" onClick={reset}>
                Cancel
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
