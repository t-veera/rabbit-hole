/** Renders plain text as real paragraphs (and, where detectable, real
 * headings) instead of one flattened blob.
 *
 * Source abstracts vary a lot in what structure they actually carry:
 * - PubMed/bioRxiv/RSS text often has real \n\n or \n breaks — restore those.
 * - OpenAlex-reconstructed abstracts (built from a word/position index, which
 *   is how OpenAlex avoids republishing copyrighted abstract text verbatim)
 *   have NO paragraph info at all, just one long run of sentences — for
 *   those we auto-paragraph at sentence boundaries so it's at least
 *   readable, since there's no real structure left to recover.
 *
 * Full text extracted from a PDF (services/fulltext.py) has no heading
 * markup either — PyMuPDF's block extraction only gives back plain text, no
 * font-size/weight to key off. Section headings are still detectable from
 * the text alone: academic papers overwhelmingly use a closed set of
 * section names, or a numbered-heading convention ("3.1 Results"), and
 * headings are reliably short lines with no sentence-ending punctuation —
 * unlike a genuine sentence that happens to be short.
 */
const _KNOWN_HEADINGS = new Set(
  [
    "abstract", "summary", "introduction", "background", "related work",
    "literature review", "materials and methods", "methods", "methodology",
    "materials", "experimental", "experimental design", "experimental procedures",
    "study design", "participants", "data collection", "data analysis",
    "results", "results and discussion", "findings", "discussion",
    "conclusion", "conclusions", "limitations", "future work",
    "acknowledgments", "acknowledgements", "author contributions",
    "conflict of interest", "conflicts of interest", "funding",
    "supplementary material", "supplementary materials", "supporting information",
    "references", "bibliography", "appendix", "declarations",
    // Structured-abstract labels (Lancet/JAMA/BMJ/NEJM house styles) — a
    // different, much more constrained context than a full-text PDF (short,
    // no tables/reference lists), so it's safe to recognize a wider,
    // journal-specific vocabulary here without the false-positive risk that
    // ruled out a general "short capitalized line" fallback elsewhere.
    "research in context", "evidence before this study", "added value of this study",
    "implications of all the available evidence", "panel", "interpretation",
    "context", "objective", "objectives", "design", "setting", "interventions",
    "exposures", "main outcomes and measures", "main outcome measures",
    "conclusions and relevance", "trial registration", "registration",
    "declaration of interests", "role of the funding source", "data sharing",
  ].map((s) => s.toLowerCase())
);

const _NUMBERED_SUBSECTION_RE = /^(\d+(?:\.\d+){1,3})\.?\s+[A-Za-z]/;
const _NUMBERED_SECTION_RE = /^(\d+)\.?\s+[A-Z][a-z]/;

type HeadingLevel = 2 | 3 | null;

// Deliberately high-precision, low-recall: only a known section name or a
// numbered-heading line counts. An earlier looser heuristic ("short line,
// mostly capitalized, no ending punctuation") also fired on table rows and
// front-matter metadata in real PDF extractions — those are common enough
// in academic papers that the false positives were worse than just leaving
// an unrecognized heading as a plain paragraph.
function detectHeadingLevel(line: string): HeadingLevel {
  const trimmed = line.trim();
  if (trimmed.length === 0 || trimmed.length > 80) return null;

  const bareKey = trimmed.replace(/:$/, "").toLowerCase();
  if (_KNOWN_HEADINGS.has(bareKey)) return 2;

  if (_NUMBERED_SUBSECTION_RE.test(trimmed)) return 3;
  if (_NUMBERED_SECTION_RE.test(trimmed)) return 2;

  return null;
}

// Known heading phrases sorted longest-first so a multi-word label (e.g.
// "evidence before this study") matches before a shorter one that happens
// to be its prefix.
const _KNOWN_HEADINGS_BY_LENGTH = [..._KNOWN_HEADINGS].sort((a, b) => b.length - a.length);

/** Some source abstracts (notably ones with no real paragraph structure at
 * all — see the OpenAlex note above) run a section label straight into its
 * own content with just a space, no line break: "Implications of all the
 * available evidence Comparable information on...". detectHeadingLevel
 * alone can't catch that since it looks at a whole paragraph, not a prefix.
 * This catches a known heading phrase specifically at the START of a
 * paragraph, immediately followed by what reads as new sentence content
 * (capitalized, at least a few words long — long enough that it isn't just
 * the label itself with trailing punctuation). */
function splitLeadingHeading(paragraph: string): [string, string] | null {
  const trimmed = paragraph.trim();
  for (const heading of _KNOWN_HEADINGS_BY_LENGTH) {
    if (trimmed.length <= heading.length) continue;
    const prefix = trimmed.slice(0, heading.length);
    if (prefix.toLowerCase() !== heading) continue;
    const rest = trimmed.slice(heading.length).trimStart();
    if (rest.length < 15 || !/^[A-Z]/.test(rest)) continue;
    return [trimmed.slice(0, heading.length), rest];
  }
  return null;
}

import type { ReactNode } from "react";

export interface ProseHighlight {
  id: string;
  quote_text: string;
}

/** Splits one paragraph's text into plain-text and <mark> segments for
 * every highlight whose quote_text appears in it — a highlight only ever
 * shows up fully within one paragraph in practice, since it comes from a
 * contiguous text selection the user made against this same rendered
 * output. Overlapping matches (rare — would mean two highlights share
 * text) keep whichever was found first and skip the rest, rather than
 * producing broken nested marks. */
function renderWithHighlights(text: string, highlights: ProseHighlight[], keyPrefix: string): ReactNode[] {
  const matches: { start: number; end: number; highlight: ProseHighlight }[] = [];
  for (const h of highlights) {
    if (!h.quote_text) continue;
    const idx = text.indexOf(h.quote_text);
    if (idx === -1) continue;
    const end = idx + h.quote_text.length;
    if (matches.some((m) => idx < m.end && end > m.start)) continue;
    matches.push({ start: idx, end, highlight: h });
  }
  if (matches.length === 0) return [text];

  matches.sort((a, b) => a.start - b.start);
  const nodes: ReactNode[] = [];
  let cursor = 0;
  matches.forEach((m, i) => {
    if (m.start > cursor) nodes.push(text.slice(cursor, m.start));
    nodes.push(
      <mark className="note-highlight" data-note-id={m.highlight.id} key={`${keyPrefix}-${i}`}>
        {text.slice(m.start, m.end)}
      </mark>
    );
    cursor = m.end;
  });
  if (cursor < text.length) nodes.push(text.slice(cursor));
  return nodes;
}

function splitSentences(text: string): string[] {
  return text.split(/(?<=[.!?])\s+(?=[A-Z(])/).filter(Boolean);
}

function chunk<T>(items: T[], size: number): T[][] {
  const out: T[][] = [];
  for (let i = 0; i < items.length; i += size) out.push(items.slice(i, i + size));
  return out;
}

export default function Prose({
  text,
  className,
  highlights,
}: {
  text: string;
  className?: string;
  highlights?: ProseHighlight[];
}) {
  let paragraphs = text
    .split(/\n\s*\n|\r\n\r\n/)
    .flatMap((block) => block.split(/\n/))
    .map((p) => p.trim())
    .filter(Boolean);

  if (paragraphs.length <= 1) {
    const sentences = splitSentences(text.trim());
    if (sentences.length > 4) {
      paragraphs = chunk(sentences, 3).map((group) => group.join(" "));
    }
  }

  if (paragraphs.length <= 1) {
    return <div className={className}>{highlights ? renderWithHighlights(text, highlights, "h") : text}</div>;
  }

  return (
    <div className={className}>
      {paragraphs.flatMap((p, i) => {
        const level = detectHeadingLevel(p);
        if (level === 2) return [<h2 key={i}>{p}</h2>];
        if (level === 3) return [<h3 key={i}>{p}</h3>];

        const split = splitLeadingHeading(p);
        if (split) {
          const [heading, rest] = split;
          return [
            <h2 key={`${i}h`}>{heading}</h2>,
            <p key={`${i}p`}>{highlights ? renderWithHighlights(rest, highlights, `${i}p`) : rest}</p>,
          ];
        }

        return [<p key={i}>{highlights ? renderWithHighlights(p, highlights, `${i}`) : p}</p>];
      })}
    </div>
  );
}
