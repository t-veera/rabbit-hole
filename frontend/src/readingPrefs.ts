/** Reading-view typography preferences (font + size), persisted the same way
 * as theme.ts: applied as CSS custom properties on the document root so
 * every article-body element picks them up without prop drilling, and
 * mirrored to localStorage so the choice holds across sessions. */

export type ReadingFont = "literata" | "source-serif" | "lora" | "spectral";
export type ReadingFontSize = "small" | "medium" | "large";

const FONT_KEY = "rabbit-hole-reading-font";
const SIZE_KEY = "rabbit-hole-reading-font-size";

// A small curated set, not an open list of every system font — each one is
// an editorial/long-form serif already used by publications like Aeon and
// The Atavist ("Fifty Two"), and each is loaded via the Google Fonts link
// in index.html.
export const READING_FONTS: { value: ReadingFont; label: string; family: string }[] = [
  { value: "literata", label: "Literata", family: '"Literata", Georgia, "Times New Roman", serif' },
  { value: "source-serif", label: "Source Serif", family: '"Source Serif 4", Georgia, "Times New Roman", serif' },
  { value: "lora", label: "Lora", family: '"Lora", Georgia, "Times New Roman", serif' },
  { value: "spectral", label: "Spectral", family: '"Spectral", Georgia, "Times New Roman", serif' },
];

export const READING_FONT_SIZES: { value: ReadingFontSize; label: string; px: string }[] = [
  { value: "small", label: "Small", px: "16.5px" },
  { value: "medium", label: "Medium", px: "18.5px" },
  { value: "large", label: "Large", px: "21px" },
];

export function getStoredReadingFont(): ReadingFont {
  try {
    const stored = localStorage.getItem(FONT_KEY);
    if (READING_FONTS.some((f) => f.value === stored)) return stored as ReadingFont;
  } catch {
    // localStorage unavailable — fall through to default
  }
  return "literata";
}

export function getStoredReadingFontSize(): ReadingFontSize {
  try {
    const stored = localStorage.getItem(SIZE_KEY);
    if (stored === "small" || stored === "medium" || stored === "large") return stored;
  } catch {
    // ignore
  }
  return "medium";
}

export function applyReadingFont(choice: ReadingFont) {
  const family = READING_FONTS.find((f) => f.value === choice)?.family ?? READING_FONTS[0].family;
  document.documentElement.style.setProperty("--reading-font", family);
  try {
    localStorage.setItem(FONT_KEY, choice);
  } catch {
    // ignore
  }
}

export function applyReadingFontSize(choice: ReadingFontSize) {
  const px = READING_FONT_SIZES.find((s) => s.value === choice)?.px ?? READING_FONT_SIZES[1].px;
  document.documentElement.style.setProperty("--reading-font-size", px);
  try {
    localStorage.setItem(SIZE_KEY, choice);
  } catch {
    // ignore
  }
}
