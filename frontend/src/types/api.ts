/**
 * Backend DTOs mirrored as TypeScript types.
 *
 * The backend's Pydantic schemas are the *source of truth*; this file is
 * a hand-curated mirror kept in sync with backend/app/schemas/*. We keep
 * names and field types aligned so a future OpenAPI codegen step is a
 * drop-in replacement.
 */

// ---------------------------------------------------------------------------
// common
// ---------------------------------------------------------------------------
export interface Paginated<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
}

// ---------------------------------------------------------------------------
// repository
// ---------------------------------------------------------------------------
export type RepositoryStatus =
  | "pending"
  | "analyzing"
  | "ready"
  | "failed";

export type AnalysisFreshnessState =
  | "fresh"
  | "stale"
  | "unknown"
  | "unavailable";

export interface RepositoryFreshness {
  state: AnalysisFreshnessState;
  reasons: string[];
  affected_features: string[];
  can_refresh: boolean;
}

export interface Repository {
  id: string;
  url: string;
  branch: string | null;
  default_branch: string | null;
  name: string;
  owner: string;
  owner_id: string | null;
  is_public: boolean;
  status: RepositoryStatus;
  error_message: string | null;
  analyzed_at: string | null;
  file_count: number;
  total_lines: number;
  languages: string | null;
  star_count: number;
  viewer_has_starred: boolean;
  commit_hash: string | null;
  analysis_version: number | null;
  pipeline_version: number | null;
  schema_version: number | null;
  embedding_model: string | null;
  freshness: RepositoryFreshness | null;
  created_at: string;
  updated_at: string;
}

export interface RepositoryCreateInput {
  url: string;
  branch?: string | null;
}

// ---------------------------------------------------------------------------
// social: stars, discovery, profiles
// ---------------------------------------------------------------------------
/** Sort order for the public discovery hub + profile repo lists. */
export type RepositorySort = "stars" | "recent" | "name";

/** Result of toggling a star on a repository. */
export interface StarState {
  starred: boolean;
  star_count: number;
}

/** A user's public-facing profile summary (served at /users/{username}). */
export interface PublicProfile {
  username: string;
  display_name: string | null;
  avatar_url: string | null;
  public_repository_count: number;
  total_stars: number;
}

// ---------------------------------------------------------------------------
// repository-centric discovery
// ---------------------------------------------------------------------------
/** One card in the repository-centric Discover grid (a (url, branch) group). */
export interface DiscoverRepository {
  url: string;
  branch: string | null;
  name: string;
  owner: string;
  analyses_count: number;
  total_stars: number;
  latest_analyzed_at: string | null;
  languages: string | null;
  file_count: number;
  total_lines: number;
  /** Most-recent analysis — lets the UI offer a 1-click "open latest". */
  latest_repository_id: string;
}

/** Public-safe reference to the analyst (repo owner) who produced an analysis. */
export interface AnalystRef {
  username: string | null;
  display_name: string | null;
  avatar_url: string | null;
}

/** One public analysis of a repository (a single repositories row). */
export interface PublicAnalysis {
  repository_id: string;
  analyst: AnalystRef;
  analyzed_at: string | null;
  star_count: number;
  viewer_has_starred: boolean;
  analysis_version: number | null;
  pipeline_version: number | null;
  schema_version: number | null;
  file_count: number;
  total_lines: number;
  languages: string | null;
  freshness: RepositoryFreshness | null;
}

/** The repository overview page: header + every public analysis of it. */
export interface RepositoryGroupDetail {
  url: string;
  branch: string | null;
  name: string;
  owner: string;
  analyses_count: number;
  total_stars: number;
  latest_analyzed_at: string | null;
  analyses: PublicAnalysis[];
}

// ---------------------------------------------------------------------------
// auth
// ---------------------------------------------------------------------------
export interface User {
  id: string;
  github_id: number;
  username: string;
  display_name: string | null;
  email: string | null;
  avatar_url: string | null;
}

// ---------------------------------------------------------------------------
// analysis job
// ---------------------------------------------------------------------------
export type AnalysisJobStatus =
  | "queued"
  | "running"
  | "succeeded"
  | "failed"
  | "cancelled";

export interface AnalysisJob {
  id: string;
  repository_id: string;
  status: AnalysisJobStatus;
  rq_job_id: string | null;
  error: string | null;
  queued_at: string;
  started_at: string | null;
  completed_at: string | null;
  progress: number;
  progress_message: string | null;
}

export interface AnalysisProgressEvent {
  event: "queued" | "running" | "progress" | "succeeded" | "failed";
  repository_id: string;
  job_id: string;
  progress: number;
  message: string | null;
  error: string | null;
}

// ---------------------------------------------------------------------------
// dependency graph
// ---------------------------------------------------------------------------
export type DependencyKind =
  | "import"
  | "inheritance"
  | "call"
  | "instantiation"
  | "reference";

export interface GraphNode {
  id: string;
  path: string;
  language: string;
  line_count: number;
  in_degree: number;
  out_degree: number;
}

export interface GraphEdge {
  from: string;
  to: string;
  kind: DependencyKind;
  symbol: string | null;
}

export interface DependencyGraph {
  repository_id: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  cycles: string[][];
}

// ---------------------------------------------------------------------------
// metrics / complexity
// ---------------------------------------------------------------------------
export interface FileComplexity {
  file_id: string;
  path: string;
  language: string;
  cyclomatic: number;
  cognitive: number;
  lines_of_code: number;
  function_count: number;
  class_count: number;
}

export interface ComplexityRanking {
  repository_id: string;
  top_files: FileComplexity[];
  average_cyclomatic: number;
  average_cognitive: number;
  median_lines_of_code: number;
}

// ---------------------------------------------------------------------------
// dead code
// ---------------------------------------------------------------------------
export type SymbolKind =
  | "function"
  | "method"
  | "class"
  | "interface"
  | "struct"
  | "enum"
  | "variable"
  | "constant"
  | "type_alias"
  | "module";

export interface DeadCodeItem {
  file_id: string;
  path: string;
  symbol_name: string;
  kind: SymbolKind;
  line_start: number;
  line_end: number;
  confidence: number;
  reason: string;
}

export interface DeadCodeReport {
  repository_id: string;
  items: DeadCodeItem[];
  summary: Record<string, number>;
}

// ---------------------------------------------------------------------------
// architecture
// ---------------------------------------------------------------------------
export interface LayerInfo {
  name: string;
  file_count: number;
  files: string[];
}

export interface ArchitectureReport {
  repository_id: string;
  layers: LayerInfo[];
  components: LayerInfo[];
  mermaid_diagram: string;
  summary: string;
}

// ---------------------------------------------------------------------------
// impact
// ---------------------------------------------------------------------------
export interface ImpactRequest {
  file_path: string;
  max_depth?: number;
}

export interface ImpactedFile {
  file_id: string;
  path: string;
  distance: number;
  risk_score: number;
}

export interface ImpactResponse {
  repository_id: string;
  source_file: string;
  impacted_files: ImpactedFile[];
  risk_score: number;
  summary: string;
}

// ---------------------------------------------------------------------------
// AI chat
// ---------------------------------------------------------------------------
export type ChatRole = "system" | "user" | "assistant";

export interface ChatMessage {
  role: ChatRole;
  content: string;
}

export interface ChatRequest {
  repository_id: string;
  question: string;
  history: ChatMessage[];
  top_k?: number;
}

export interface ChatCitation {
  file_path: string;
  line_start: number;
  line_end: number;
  symbol: string | null;
  snippet: string;
}

export type ChatTokenEvent =
  | { event: "token"; content: string }
  | { event: "citations"; citations: ChatCitation[] }
  | { event: "done" }
  | { event: "error"; error: string };

// ---------------------------------------------------------------------------
// Persistent chat sessions
// ---------------------------------------------------------------------------
export interface AttachedContext {
  path: string;
  language?: string | null;
}

export interface ChatSession {
  id: string;
  repository_id: string;
  title: string;
  last_activity_at: string;
  created_at: string;
  updated_at: string;
}

export interface ChatMessageRecord {
  id: string;
  session_id: string;
  role: "user" | "assistant";
  content: string;
  citations: ChatCitation[] | null;
  attached_context: AttachedContext[] | null;
  created_at: string;
}

export interface ChatSessionCreateInput {
  title?: string | null;
}

export interface ChatSessionUpdateInput {
  title: string;
}

export interface SessionChatRequest {
  question: string;
  attached: AttachedContext[];
  top_k?: number;
}
