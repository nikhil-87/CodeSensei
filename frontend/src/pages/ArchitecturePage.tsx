import { useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  ArrowDownRight,
  ArrowUpRight,
  ChevronRight,
  FileCode2,
  Folder,
  Home,
  Network,
} from "lucide-react";

import { useAnalysisGate } from "@/components/analysis/AnalysisGate";
import { MermaidDiagram } from "@/components/architecture/MermaidDiagram";
import { Card } from "@/components/common/Card";
import { ErrorState } from "@/components/common/ErrorState";
import { GraphCanvasSkeleton, PageHeaderSkeleton } from "@/components/common/Skeleton";
import { NodeInspector } from "@/components/graph/NodeInspector";
import { useArchitecture, useDependencyGraph } from "@/hooks/useInsights";
import { useRepository } from "@/hooks/useRepositories";
import { cn, formatNumber } from "@/lib/format";
import {
  buildAdjacency,
  buildFolderTree,
  classifyLayer,
  colorForLanguage,
  findFolder,
  layerLabel,
  type FolderTreeNode,
} from "@/lib/graphModel";
import type { GraphNode } from "@/types/api";

export function ArchitecturePage() {
  const { repositoryId } = useParams<{ repositoryId: string }>();
  const navigate = useNavigate();
  const gate = useAnalysisGate(repositoryId);
  const arch = useArchitecture(repositoryId, gate.ready);
  const graph = useDependencyGraph(repositoryId, gate.ready);
  const { data: repository } = useRepository(repositoryId);

  const [path, setPath] = useState("");
  const [selectedFileId, setSelectedFileId] = useState<string | undefined>();
  const [showDiagram, setShowDiagram] = useState(false);

  const nodes = useMemo(() => graph.data?.nodes ?? [], [graph.data]);
  const edges = useMemo(() => graph.data?.edges ?? [], [graph.data]);

  const nodeById = useMemo(() => {
    const m = new Map<string, GraphNode>();
    for (const n of nodes) m.set(n.id, n);
    return m;
  }, [nodes]);
  const adjacency = useMemo(() => buildAdjacency(edges), [edges]);
  const tree = useMemo(() => buildFolderTree(nodes), [nodes]);
  const cycleFileIds = useMemo(() => {
    const s = new Set<string>();
    for (const c of graph.data?.cycles ?? []) for (const id of c) s.add(id);
    return s;
  }, [graph.data]);

  const current = useMemo(() => findFolder(tree, path) ?? tree, [tree, path]);

  const childStats = useMemo(
    () => current.folders.map((f) => computeFolderStats(f, adjacency)),
    [current, adjacency],
  );

  if (gate.blocker) return gate.blocker;
  if ((arch.isLoading || graph.isLoading) && !arch.data) {
    return (
      <div className="mx-auto max-w-[1700px] space-y-4 p-4 sm:p-6">
        <PageHeaderSkeleton />
        <GraphCanvasSkeleton />
      </div>
    );
  }
  if (arch.isError && !arch.data) {
    return (
      <div className="p-4 sm:p-6">
        <ErrorState
          message={(arch.error as Error).message}
          onRetry={() => void arch.refetch()}
        />
      </div>
    );
  }
  if (!arch.data) return null;

  const selectedNode = selectedFileId ? nodeById.get(selectedFileId) : undefined;

  const drillTo = (folderPath: string) => {
    setPath(folderPath);
    setSelectedFileId(undefined);
  };

  return (
    <div className="mx-auto max-w-[1700px] space-y-5 p-4 sm:p-6">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-ink-900">Architecture</h1>
          <p className="text-sm text-ink-500">{arch.data.summary}</p>
        </div>
        {arch.data.mermaid_diagram && (
          <button
            type="button"
            onClick={() => setShowDiagram((v) => !v)}
            className="focus-ring inline-flex h-8 items-center gap-1.5 rounded-md border border-ink-200 px-2.5 text-xs font-medium text-ink-600 hover:bg-ink-50"
          >
            <Network className="h-3.5 w-3.5" />
            {showDiagram ? "Hide layer diagram" : "Show layer diagram"}
          </button>
        )}
      </header>

      {showDiagram && arch.data.mermaid_diagram && (
        <Card title="Layer diagram" padded>
          <MermaidDiagram
            source={arch.data.mermaid_diagram}
            className="w-full overflow-auto"
          />
        </Card>
      )}

      <Breadcrumbs path={path} onNavigate={drillTo} />

      <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
        <div className="space-y-4">
          {/* Sub-modules (folders) */}
          {childStats.length > 0 && (
            <section>
              <h2 className="mb-2 text-[11px] font-medium uppercase tracking-wide text-ink-400">
                Modules ({childStats.length})
              </h2>
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                {childStats.map((c) => (
                  <FolderCard
                    key={c.node.path}
                    stats={c}
                    onOpen={() => drillTo(c.node.path)}
                  />
                ))}
              </div>
            </section>
          )}

          {/* Files directly in this folder */}
          {current.files.length > 0 && (
            <section>
              <h2 className="mb-2 text-[11px] font-medium uppercase tracking-wide text-ink-400">
                Files ({current.files.length})
              </h2>
              <ul className="divide-y divide-ink-100 overflow-hidden rounded-lg border border-ink-200 bg-surface">
                {current.files.map((f) => (
                  <FileRow
                    key={f.id}
                    file={f}
                    adjacency={adjacency}
                    selected={selectedFileId === f.id}
                    onSelect={() => setSelectedFileId(f.id)}
                  />
                ))}
              </ul>
            </section>
          )}

          {childStats.length === 0 && current.files.length === 0 && (
            <p className="rounded-lg border border-dashed border-ink-200 p-6 text-center text-sm text-ink-400">
              This folder is empty.
            </p>
          )}
        </div>

        <aside className="h-[480px] overflow-hidden rounded-lg border border-ink-200 bg-surface lg:h-[640px]">
          {selectedNode ? (
            <NodeInspector
              repositoryId={repositoryId as string}
              selected={{
                id: selectedNode.id,
                kind: "file",
                label: selectedNode.path.split("/").pop() ?? selectedNode.path,
                path: selectedNode.path,
                fileIds: [selectedNode.id],
                fileCount: 1,
                language: selectedNode.language,
                totalLines: selectedNode.line_count,
                expandable: false,
                depth: 0,
              }}
              nodeById={nodeById}
              adjacency={adjacency}
              inCycle={cycleFileIds.has(selectedNode.id)}
              analyzedAt={repository?.analyzed_at}
              onSelectFile={(id) => setSelectedFileId(id)}
              onFocusDependencies={() =>
                navigate(`/repos/${repositoryId}/graph?focus=${selectedNode.id}&dir=down`)
              }
              onFocusDependents={() =>
                navigate(`/repos/${repositoryId}/graph?focus=${selectedNode.id}&dir=up`)
              }
            />
          ) : (
            <FolderSummary folder={current} adjacency={adjacency} />
          )}
        </aside>
      </div>
    </div>
  );
}

// --------------------------------------------------------------------------
// folder statistics
// --------------------------------------------------------------------------
interface FolderStats {
  node: FolderTreeNode;
  dominantLayer: string;
  languages: { language: string; count: number }[];
  fanIn: number;
  fanOut: number;
}

function collectFileIds(node: FolderTreeNode, acc: Set<string>): void {
  for (const f of node.files) acc.add(f.id);
  for (const c of node.folders) collectFileIds(c, acc);
}

function collectFiles(node: FolderTreeNode, acc: GraphNode[]): void {
  for (const f of node.files) acc.push(f);
  for (const c of node.folders) collectFiles(c, acc);
}

function computeFolderStats(
  node: FolderTreeNode,
  adjacency: ReturnType<typeof buildAdjacency>,
): FolderStats {
  const members = new Set<string>();
  collectFileIds(node, members);
  const files: GraphNode[] = [];
  collectFiles(node, files);

  const langCounts = new Map<string, number>();
  const layerCounts = new Map<string, number>();
  for (const f of files) {
    langCounts.set(f.language, (langCounts.get(f.language) ?? 0) + 1);
    const l = classifyLayer(f.path);
    layerCounts.set(l, (layerCounts.get(l) ?? 0) + 1);
  }

  let fanOut = 0;
  let fanIn = 0;
  for (const id of members) {
    for (const t of adjacency.out.get(id) ?? []) if (!members.has(t)) fanOut += 1;
    for (const s of adjacency.in.get(id) ?? []) if (!members.has(s)) fanIn += 1;
  }

  const dominantLayer =
    [...layerCounts.entries()].sort((a, b) => b[1] - a[1])[0]?.[0] ?? "other";
  const languages = [...langCounts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 4)
    .map(([language, count]) => ({ language, count }));

  return { node, dominantLayer, languages, fanIn, fanOut };
}

// --------------------------------------------------------------------------
// presentational pieces
// --------------------------------------------------------------------------
function Breadcrumbs({
  path,
  onNavigate,
}: {
  path: string;
  onNavigate: (p: string) => void;
}) {
  const segments = path === "" ? [] : path.split("/");
  const crumbs = segments.map((seg, i) => ({
    label: seg,
    path: segments.slice(0, i + 1).join("/"),
  }));
  return (
    <nav className="flex flex-wrap items-center gap-1 text-sm" aria-label="Breadcrumb">
      <button
        type="button"
        onClick={() => onNavigate("")}
        className="focus-ring inline-flex items-center gap-1 rounded px-1.5 py-1 font-medium text-ink-600 hover:bg-ink-50 hover:text-ink-900"
      >
        <Home className="h-3.5 w-3.5" /> Repository
      </button>
      {crumbs.map((c) => (
        <span key={c.path} className="flex items-center gap-1">
          <ChevronRight className="h-3.5 w-3.5 text-ink-300" />
          <button
            type="button"
            onClick={() => onNavigate(c.path)}
            className="focus-ring rounded px-1.5 py-1 font-mono text-xs text-ink-700 hover:bg-ink-50 hover:text-ink-900"
          >
            {c.label}
          </button>
        </span>
      ))}
    </nav>
  );
}

function FolderCard({
  stats,
  onOpen,
}: {
  stats: FolderStats;
  onOpen: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onOpen}
      className="focus-ring group flex flex-col gap-3 rounded-lg border border-ink-200 bg-surface p-4 text-left transition-all hover:-translate-y-0.5 hover:border-accent-300 hover:shadow-card"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          <Folder className="h-4 w-4 shrink-0 text-accent-600" />
          <span className="truncate font-semibold text-ink-900">{stats.node.name}</span>
        </div>
        <ChevronRight className="h-4 w-4 shrink-0 text-ink-300 transition-transform group-hover:translate-x-0.5 group-hover:text-accent-500" />
      </div>

      <div className="flex items-center gap-2">
        <span className="inline-flex items-center gap-1 rounded-full border border-accent-200 bg-accent-50 px-2 py-0.5 text-[11px] font-medium text-accent-800">
          {layerLabel(stats.dominantLayer)}
        </span>
        <span className="text-xs text-ink-500">
          {formatNumber(stats.node.fileCount)} files
        </span>
      </div>

      <div className="flex items-center gap-1.5">
        {stats.languages.map((l) => (
          <span
            key={l.language}
            className="inline-flex items-center gap-1 text-[11px] text-ink-500"
            title={`${l.language}: ${l.count}`}
          >
            <span
              className="h-2 w-2 rounded-full"
              style={{ backgroundColor: colorForLanguage(l.language) }}
            />
            {l.language}
          </span>
        ))}
      </div>

      <div className="flex items-center gap-3 border-t border-ink-100 pt-2 text-[11px] text-ink-500">
        <span className="inline-flex items-center gap-1" title="Incoming dependencies from other modules">
          <ArrowDownRight className="h-3 w-3 text-amber-500" /> used by {stats.fanIn}
        </span>
        <span className="inline-flex items-center gap-1" title="Outgoing dependencies to other modules">
          <ArrowUpRight className="h-3 w-3 text-blue-500" /> depends on {stats.fanOut}
        </span>
      </div>
    </button>
  );
}

function FileRow({
  file,
  adjacency,
  selected,
  onSelect,
}: {
  file: GraphNode;
  adjacency: ReturnType<typeof buildAdjacency>;
  selected: boolean;
  onSelect: () => void;
}) {
  const deps = adjacency.out.get(file.id)?.size ?? 0;
  const dependents = adjacency.in.get(file.id)?.size ?? 0;
  return (
    <li>
      <button
        type="button"
        onClick={onSelect}
        className={cn(
          "flex w-full items-center gap-3 px-3 py-2 text-left transition-colors hover:bg-ink-50",
          selected && "bg-accent-50 hover:bg-accent-50",
        )}
      >
        <FileCode2 className="h-4 w-4 shrink-0 text-ink-400" />
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm text-ink-800">{file.path.split("/").pop()}</span>
          <span className="block text-[11px] text-ink-400">
            {layerLabel(classifyLayer(file.path))} · {file.language} ·{" "}
            {formatNumber(file.line_count)} lines
          </span>
        </span>
        <span className="shrink-0 text-[11px] text-ink-400">
          ↓{dependents} ↑{deps}
        </span>
      </button>
    </li>
  );
}

function FolderSummary({
  folder,
  adjacency,
}: {
  folder: FolderTreeNode;
  adjacency: ReturnType<typeof buildAdjacency>;
}) {
  const stats = useMemo(
    () => computeFolderStats(folder, adjacency),
    [folder, adjacency],
  );
  return (
    <div className="flex h-full flex-col gap-4 p-5">
      <div>
        <p className="text-sm font-semibold text-ink-900">
          {folder.name || "Repository root"}
        </p>
        <p className="mt-0.5 text-xs text-ink-500">
          {formatNumber(folder.fileCount)} files ·{" "}
          {folder.folders.length} sub-modules
        </p>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div className="rounded-md border border-ink-100 bg-ink-50/60 px-2.5 py-2">
          <p className="text-[10px] uppercase tracking-wide text-ink-400">Used by</p>
          <p className="mt-0.5 text-sm font-semibold text-ink-900">{stats.fanIn}</p>
        </div>
        <div className="rounded-md border border-ink-100 bg-ink-50/60 px-2.5 py-2">
          <p className="text-[10px] uppercase tracking-wide text-ink-400">Depends on</p>
          <p className="mt-0.5 text-sm font-semibold text-ink-900">{stats.fanOut}</p>
        </div>
      </div>

      <div className="space-y-1.5">
        <p className="text-[11px] font-medium uppercase tracking-wide text-ink-400">
          Languages
        </p>
        <div className="flex flex-wrap gap-1.5">
          {stats.languages.map((l) => (
            <span
              key={l.language}
              className="inline-flex items-center gap-1 rounded-full border border-ink-200 bg-ink-50 px-2 py-0.5 text-[11px] text-ink-600"
            >
              <span
                className="h-2 w-2 rounded-full"
                style={{ backgroundColor: colorForLanguage(l.language) }}
              />
              {l.language} · {l.count}
            </span>
          ))}
        </div>
      </div>

      <p className="mt-auto text-[11px] text-ink-400">
        Open a module to drill in, or select a file to inspect it and ask AI.
      </p>
    </div>
  );
}

