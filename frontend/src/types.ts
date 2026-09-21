export type ItemType = "paper" | "article" | "book" | "note";
export type ReadingState = "unread" | "read" | "skimmed";
export type Cadence = "realtime" | "daily" | "weekly";
export type SourceKind = "academic_api" | "rss";
export type SourceTrack = "research" | "journalism";
export type EdgeType = "manual" | "citation";
export type PaperOrigin = "source" | "discovered" | "uploaded";

export interface Source {
  id: string;
  name: string;
  url: string;
  kind: SourceKind;
  track: SourceTrack;
  field: string | null;
  is_user_added: boolean;
  priority: number;
  created_at: string;
}

export interface ReadingStatus {
  item_type: ItemType;
  item_id: string;
  status: ReadingState;
  in_queue: boolean;
  in_reference: boolean;
  updated_at: string;
}

export interface Researcher {
  id: string;
  name: string;
  orcid: string | null;
  openalex_id: string | null;
  affiliation: string | null;
  degree: string | null;
  email: string | null;
  photo_url: string | null;
  faculty_page_url: string | null;
}

export interface PaperAuthor {
  author_order: number;
  is_corresponding: boolean;
  researcher: Researcher;
}

export interface Paper {
  id: string;
  title: string;
  abstract: string | null;
  doi: string | null;
  external_id: string | null;
  field: string | null;
  venue: string | null;
  published_date: string | null;
  origin: PaperOrigin;
  oa_status: boolean;
  oa_url: string | null;
  landing_url: string | null;
  openalex_id: string | null;
  created_at: string;
  origin_source: Source | null;
  authors: PaperAuthor[];
  reading_status: ReadingStatus | null;
}

export interface UploadDraft {
  suggested_title: string | null;
  suggested_authors: string[];
  suggested_doi: string | null;
  full_text: string;
  page_count: number;
}

export interface Article {
  id: string;
  title: string;
  summary: string | null;
  url: string;
  author_name: string | null;
  author_researcher_id: string | null;
  is_from_user_source: boolean;
  published_date: string | null;
  created_at: string;
  origin_source: Source | null;
  reading_status: ReadingStatus | null;
}

export interface Book {
  id: string;
  title: string;
  authors: string[] | null;
  first_publish_year: number | null;
  isbn: string | null;
  description: string | null;
  cover_url: string | null;
  open_library_id: string | null;
  open_library_url: string | null;
  created_at: string;
  reading_status: ReadingStatus | null;
}

export interface Topic {
  id: string;
  raw_query: string;
  translated_query: string | null;
  field: string | null;
  cadence: Cadence;
  last_run_at: string | null;
  researcher_id: string | null;
  created_at: string;
}

export interface AuthorSearchResult {
  openalex_id: string;
  name: string;
  orcid: string | null;
  affiliation: string | null;
  works_count: number | null;
  merged_ids: string[];
}

export interface FollowedEntry {
  topic: Topic;
  researcher: Researcher;
}

export interface RHList {
  id: string;
  name: string;
  created_at: string;
}

export interface ListItemRow {
  id: string;
  item_type: ItemType;
  item_id: string;
  added_at: string;
}

export interface Note {
  id: string;
  item_type: ItemType | null;
  item_id: string | null;
  quote_text: string | null;
  note_text: string;
  topic_tag: string | null;
  created_at: string;
}

export interface GraphNode {
  id: string;
  item_type: ItemType;
  item_id: string;
  title: string;
  is_saved: boolean;
  is_linked: boolean;
}

export interface GraphEdge {
  id: string;
  source_type: ItemType;
  source_id: string;
  target_type: ItemType;
  target_id: string;
  edge_type: EdgeType;
  created_at: string;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface Notification {
  topic_id: string;
  topic_query: string;
  new_count: number;
}

export type SettingSource = "settings" | "env" | "unset";

export interface AppSettings {
  anthropic_api_key_set: boolean;
  anthropic_api_key_source: SettingSource;
  unpaywall_email: string | null;
  unpaywall_email_source: SettingSource;
  openalex_mailto: string | null;
  openalex_mailto_source: SettingSource;
  ncbi_api_key_set: boolean;
  ncbi_api_key_source: SettingSource;
  semantic_scholar_api_key_set: boolean;
  semantic_scholar_api_key_source: SettingSource;
  core_api_key_set: boolean;
  core_api_key_source: SettingSource;
}

export const KNOWN_FIELDS = [
  "biology",
  "medicine",
  "genomics",
  "physics",
  "astronomy",
  "computer_science",
  "math",
  "economics",
  "humanities",
  "politics",
  "general_science",
];
