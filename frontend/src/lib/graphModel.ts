/**
 * Graph model — pure helpers that turn a flat dependency graph into the
 * hierarchical, progressively-disclosable structures the UI renders.
 *
 * Everything here is deterministic and side-effect free so it can be unit
 * tested and memoised cheaply. The functions are designed to scale: they
 * operate on plain maps/sets and never hold cytoscape instances.
 */
import type { GraphEdge, GraphNode } from "@/types/api";

// ---------------------------------------------------------------------------
// architectural layers — mirrors backend ArchitectureService._classify_layer
// so the two surfaces agree on which layer a file belongs to.
// ---------------------------------------------------------------------------
const LAYER_HINTS: ReadonlyArray<readonly [string, readonly string[]]> = [
  ["controllers", ["api", "controller", "endpoint", "route", "handler"]],
  ["services", ["service"]],
  ["repositories", ["repository", "repositories", "dao", "store"]],
  ["models", ["model", "schema", "entity", "domain"]],
  ["infrastructure", ["infra", "config", "settings", "db", "cache"]],
  ["ui", ["ui", "frontend", "view", "component", "page"]],
  ["tests", ["test", "spec"]],
];

/** Human-friendly architectural layer for a path (UI, Service, …). */
export function classifyLayer(path: string): string {
  const lowered = path.toLowerCase();
  for (const [layer, hints] of LAYER_HINTS) {
    if (hints.some((h) => lowered.includes(h))) return layer;
  }
  return "other";
}

/** Title-cased label for display ("controllers" → "Controllers"). */
export function layerLabel(layer: string): string {
  return layer.charAt(0).toUpperCase() + layer.slice(1);
}

// ---------------------------------------------------------------------------
// adjacency + reachability
// ---------------------------------------------------------------------------
export interface Adjacency {
  /** file id → ids it depends on (outgoing). */
  out: Map<string, Set<string>>;
  /** file id → ids that depend on it (incoming). */
  in: Map<string, Set<string>>;
}

export function buildAdjacency(edges: GraphEdge[]): Adjacency {
  const out = new Map<string, Set<string>>();
  const inn = new Map<string, Set<string>>();
  for (const e of edges) {
    if (e.from === e.to) continue;
    (out.get(e.from) ?? out.set(e.from, new Set()).get(e.from)!).add(e.to);
    (inn.get(e.to) ?? inn.set(e.to, new Set()).get(e.to)!).add(e.from);
  }
  return { out, in: inn };
}

/**
 * Breadth-first reachable set from `start` following `direction`, excluding
 * the start node. `maxDepth` bounds traversal so focus mode stays responsive
 * on very large graphs (default: unbounded).
 */
export function reachable(
  start: string,
  adjacency: Adjacency,
  direction: "downstream" | "upstream",
  maxDepth = Infinity,
): Set<string> {
  const map = direction === "downstream" ? adjacency.out : adjacency.in;
  const seen = new Set<string>();
  let frontier: string[] = [start];
  let depth = 0;
  while (frontier.length > 0 && depth < maxDepth) {
    const next: string[] = [];
    for (const node of frontier) {
      for (const neighbour of map.get(node) ?? []) {
        if (!seen.has(neighbour) && neighbour !== start) {
          seen.add(neighbour);
          next.push(neighbour);
        }
      }
    }
    frontier = next;
    depth += 1;
  }
  return seen;
}

/** Direct neighbours (depth 1) in both directions. */
export function directNeighbours(
  id: string,
  adjacency: Adjacency,
): { dependencies: string[]; dependents: string[] } {
  return {
    dependencies: [...(adjacency.out.get(id) ?? [])],
    dependents: [...(adjacency.in.get(id) ?? [])],
  };
}

/**
 * The longest dependency chain length starting at `start` and following
 * `direction`. Bounded by `maxDepth` so it stays responsive on huge graphs.
 * Cycle-safe (visited set prevents infinite loops).
 */
export function chainDepth(
  start: string,
  adjacency: Adjacency,
  direction: "downstream" | "upstream",
  maxDepth = 12,
): number {
  const map = direction === "downstream" ? adjacency.out : adjacency.in;
  const seen = new Set<string>([start]);
  let frontier: string[] = [start];
  let depth = 0;
  while (frontier.length > 0 && depth < maxDepth) {
    const next: string[] = [];
    for (const node of frontier) {
      for (const neighbour of map.get(node) ?? []) {
        if (!seen.has(neighbour)) {
          seen.add(neighbour);
          next.push(neighbour);
        }
      }
    }
    if (next.length === 0) break;
    frontier = next;
    depth += 1;
  }
  return depth;
}

export interface ImpactSummary {
  /** Files transitively affected if this file changes (its dependents). */
  impactScope: number;
  /** Files this one transitively relies on (its dependencies). */
  dependencyReach: number;
  /** Longest chain of files that transitively depend on this one. */
  impactDepth: number;
  /** Longest chain of files this one transitively depends on. */
  dependencyDepth: number;
  /** 0–100 importance score blending fan-in, reach and centrality. */
  criticality: number;
  /** Coarse label derived from the criticality score. */
  criticalityLabel: "Low" | "Moderate" | "High" | "Critical";
}

/**
 * Compute a file's blast-radius and importance from the dependency graph.
 * "Impact" follows incoming edges (who depends on me) — the set affected when
 * this file changes. Criticality blends direct fan-in, transitive reach and
 * the file's share of the whole graph into a single 0–100 score.
 */
export function computeImpact(
  fileId: string,
  adjacency: Adjacency,
  totalFiles: number,
): ImpactSummary {
  const dependents = reachable(fileId, adjacency, "upstream");
  const dependencies = reachable(fileId, adjacency, "downstream");
  const directIn = adjacency.in.get(fileId)?.size ?? 0;
  const directOut = adjacency.out.get(fileId)?.size ?? 0;

  const impactScope = dependents.size;
  const reachShare = totalFiles > 1 ? impactScope / (totalFiles - 1) : 0;

  // Blend: direct fan-in (saturating), transitive reach share, and the
  // hub-ness of having both many dependents and dependencies.
  const fanInScore = Math.min(1, directIn / 12); // 12+ importers ≈ max
  const reachScore = Math.min(1, reachShare * 2.5); // touching 40% of repo ≈ max
  const hubScore = Math.min(1, (directIn + directOut) / 24);
  const criticality = Math.round(
    100 * (0.5 * fanInScore + 0.35 * reachScore + 0.15 * hubScore),
  );

  const criticalityLabel =
    criticality >= 75
      ? "Critical"
      : criticality >= 45
        ? "High"
        : criticality >= 20
          ? "Moderate"
          : "Low";

  return {
    impactScope,
    dependencyReach: dependencies.size,
    impactDepth: chainDepth(fileId, adjacency, "upstream"),
    dependencyDepth: chainDepth(fileId, adjacency, "downstream"),
    criticality,
    criticalityLabel,
  };
}

// ---------------------------------------------------------------------------
// path helpers
// ---------------------------------------------------------------------------
export function dirOf(path: string): string {
  const idx = path.lastIndexOf("/");
  return idx === -1 ? "" : path.slice(0, idx);
}

export function baseName(path: string): string {
  const idx = path.lastIndexOf("/");
  return idx === -1 ? path : path.slice(idx + 1);
}

/** Ordered folder prefixes of a path, shallow → deep. `a/b/c.py` → [a, a/b]. */
export function folderPrefixes(path: string): string[] {
  const dir = dirOf(path);
  if (dir === "") return [];
  const segments = dir.split("/");
  const prefixes: string[] = [];
  let acc = "";
  for (const seg of segments) {
    acc = acc === "" ? seg : `${acc}/${seg}`;
    prefixes.push(acc);
  }
  return prefixes;
}

// ---------------------------------------------------------------------------
// progressive clustering
// ---------------------------------------------------------------------------
export type UnitKind = "file" | "folder";

export interface GraphUnit {
  /** Stable id: file id for files, "dir:<path>" for folders. */
  id: string;
  kind: UnitKind;
  /** Display label (basename for files, folder name for folders). */
  label: string;
  /** Full path (file path, or folder path). */
  path: string;
  /** Files represented by this unit. */
  fileIds: string[];
  fileCount: number;
  /** Dominant language (for colour); folders use their plurality language. */
  language: string;
  totalLines: number;
  /** Whether this folder can be expanded (has nested structure). */
  expandable: boolean;
  /** Depth of the folder (number of path segments); 0 for root files. */
  depth: number;
}

export interface ClusterModel {
  units: GraphUnit[];
  /** file id → unit id, for mapping edges and highlights. */
  fileToUnit: Map<string, string>;
}

/**
 * Resolve every file to the shallowest folder prefix that is NOT expanded.
 * When all of a file's ancestor folders are expanded, the file itself becomes
 * a unit. With an empty `expanded` set this yields one cluster per top-level
 * folder — the "repository" overview — and drilling expands progressively.
 */
export function computeClusters(
  nodes: GraphNode[],
  expanded: ReadonlySet<string>,
): ClusterModel {
  const fileToUnit = new Map<string, string>();
  const unitFiles = new Map<string, GraphNode[]>();
  const unitIsFolder = new Map<string, boolean>();

  for (const node of nodes) {
    const prefixes = folderPrefixes(node.path);
    let unitId: string | null = null;
    for (const prefix of prefixes) {
      if (!expanded.has(prefix)) {
        unitId = `dir:${prefix}`;
        unitIsFolder.set(unitId, true);
        break;
      }
    }
    if (unitId === null) {
      // Root file, or every ancestor folder expanded → render the file.
      unitId = node.id;
      unitIsFolder.set(unitId, false);
    }
    fileToUnit.set(node.id, unitId);
    (unitFiles.get(unitId) ?? unitFiles.set(unitId, []).get(unitId)!).push(node);
  }

  const units: GraphUnit[] = [];
  for (const [unitId, files] of unitFiles) {
    const isFolder = unitIsFolder.get(unitId) ?? false;
    if (isFolder) {
      const folderPath = unitId.slice("dir:".length);
      units.push({
        id: unitId,
        kind: "folder",
        label: baseName(folderPath),
        path: folderPath,
        fileIds: files.map((f) => f.id),
        fileCount: files.length,
        language: dominantLanguage(files),
        totalLines: files.reduce((s, f) => s + f.line_count, 0),
        // Expandable when drilling reveals detail: more than one file, or
        // nested sub-folders beneath this prefix.
        expandable:
          files.length > 1 ||
          files.some((f) => f.path.slice(folderPath.length + 1).includes("/")),
        depth: folderPath.split("/").length,
      });
    } else {
      const file = files[0];
      if (!file) continue;
      units.push({
        id: file.id,
        kind: "file",
        label: baseName(file.path),
        path: file.path,
        fileIds: [file.id],
        fileCount: 1,
        language: file.language,
        totalLines: file.line_count,
        expandable: false,
        depth: 0,
      });
    }
  }

  return { units, fileToUnit };
}

function dominantLanguage(files: GraphNode[]): string {
  const counts = new Map<string, number>();
  for (const f of files) counts.set(f.language, (counts.get(f.language) ?? 0) + 1);
  let best = "unknown";
  let bestCount = -1;
  for (const [lang, count] of counts) {
    if (count > bestCount) {
      best = lang;
      bestCount = count;
    }
  }
  return best;
}

// ---------------------------------------------------------------------------
// aggregated edges between units
// ---------------------------------------------------------------------------
export interface AggregatedEdge {
  source: string;
  target: string;
  /** Number of underlying file→file edges collapsed into this one. */
  weight: number;
}

export function aggregateEdges(
  edges: GraphEdge[],
  fileToUnit: Map<string, string>,
  visibleFiles: ReadonlySet<string>,
): AggregatedEdge[] {
  const weights = new Map<string, AggregatedEdge>();
  for (const e of edges) {
    if (!visibleFiles.has(e.from) || !visibleFiles.has(e.to)) continue;
    const source = fileToUnit.get(e.from);
    const target = fileToUnit.get(e.to);
    if (!source || !target || source === target) continue;
    const key = `${source}\u0000${target}`;
    const existing = weights.get(key);
    if (existing) existing.weight += 1;
    else weights.set(key, { source, target, weight: 1 });
  }
  return [...weights.values()];
}

// ---------------------------------------------------------------------------
// folder tree (architecture drill-down)
// ---------------------------------------------------------------------------
export interface FolderTreeNode {
  name: string;
  path: string;
  /** Direct child folders. */
  folders: FolderTreeNode[];
  /** Files directly in this folder. */
  files: GraphNode[];
  /** Total files under this subtree (recursive). */
  fileCount: number;
}

/** Build a nested folder tree from a flat file list. */
export function buildFolderTree(nodes: GraphNode[]): FolderTreeNode {
  const root: FolderTreeNode = {
    name: "",
    path: "",
    folders: [],
    files: [],
    fileCount: 0,
  };
  const lookup = new Map<string, FolderTreeNode>([["", root]]);

  const ensureFolder = (path: string): FolderTreeNode => {
    const existing = lookup.get(path);
    if (existing) return existing;
    const parentPath = dirOf(path);
    const parent = ensureFolder(parentPath);
    const node: FolderTreeNode = {
      name: baseName(path),
      path,
      folders: [],
      files: [],
      fileCount: 0,
    };
    parent.folders.push(node);
    lookup.set(path, node);
    return node;
  };

  for (const file of nodes) {
    const folder = ensureFolder(dirOf(file.path));
    folder.files.push(file);
  }

  // Compute recursive counts and sort for stable, meaningful ordering.
  const finalise = (node: FolderTreeNode): number => {
    let total = node.files.length;
    for (const child of node.folders) total += finalise(child);
    node.fileCount = total;
    node.folders.sort((a, b) => b.fileCount - a.fileCount || a.name.localeCompare(b.name));
    node.files.sort((a, b) => a.path.localeCompare(b.path));
    return total;
  };
  finalise(root);
  return root;
}

/** Resolve a folder path to its tree node (or null). */
export function findFolder(
  root: FolderTreeNode,
  path: string,
): FolderTreeNode | null {
  if (path === "") return root;
  let current: FolderTreeNode | null = root;
  const segments = path.split("/");
  let acc = "";
  for (const seg of segments) {
    acc = acc === "" ? seg : `${acc}/${seg}`;
    current = current.folders.find((f) => f.path === acc) ?? null;
    if (!current) return null;
  }
  return current;
}

// ---------------------------------------------------------------------------
// language palette (shared by graph + legends)
// ---------------------------------------------------------------------------
export const LANGUAGE_COLORS: Record<string, string> = {
  python: "#3a7eff",
  typescript: "#1f5fef",
  javascript: "#d97706",
  go: "#16a34a",
  java: "#dc2626",
  rust: "#a855f7",
  ruby: "#e11d48",
  csharp: "#7c3aed",
  cpp: "#0891b2",
  c: "#0891b2",
  unknown: "#7d8597",
};

export function colorForLanguage(language: string): string {
  return LANGUAGE_COLORS[language] ?? LANGUAGE_COLORS.unknown ?? "#7d8597";
}
