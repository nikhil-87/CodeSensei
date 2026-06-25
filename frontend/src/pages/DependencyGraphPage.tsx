import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";

import { useAnalysisGate } from "@/components/analysis/AnalysisGate";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { GraphCanvasSkeleton, PageHeaderSkeleton } from "@/components/common/Skeleton";
import { CytoscapeGraph, type GraphHighlight } from "@/components/graph/CytoscapeGraph";
import { GraphToolbar, type ViewLevel } from "@/components/graph/GraphToolbar";
import { NodeInspector } from "@/components/graph/NodeInspector";
import { useComplexity, useDependencyGraph } from "@/hooks/useInsights";
import { useRepository } from "@/hooks/useRepositories";
import {
  aggregateEdges,
  buildAdjacency,
  computeClusters,
  computeImpact,
  folderPrefixes,
  reachable,
  type GraphUnit,
  type ImpactSummary,
} from "@/lib/graphModel";
import type { FileComplexity, GraphNode } from "@/types/api";

type FocusDirection = "both" | "up" | "down";

export function DependencyGraphPage() {
  const { repositoryId } = useParams<{ repositoryId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const gate = useAnalysisGate(repositoryId);
  const { data, isLoading, isError, error, refetch } = useDependencyGraph(
    repositoryId,
    gate.ready,
  );
  const { data: complexity } = useComplexity(repositoryId, 100, gate.ready);
  const { data: repository } = useRepository(repositoryId);

  // ---- view state -------------------------------------------------------
  const [level, setLevel] = useState<ViewLevel>("repository");
  const [expanded, setExpanded] = useState<ReadonlySet<string>>(new Set());
  const [layout, setLayout] = useState<"cose" | "dagre">("cose");
  const [selectedId, setSelectedId] = useState<string | undefined>();
  const [query, setQuery] = useState("");
  const [activeLanguages, setActiveLanguages] = useState<ReadonlySet<string>>(new Set());
  const [hideIsolated, setHideIsolated] = useState(false);
  const [cyclesOnly, setCyclesOnly] = useState(false);
  const [focusMode, setFocusMode] = useState(false);
  const [focusDirection, setFocusDirection] = useState<FocusDirection>("both");
  const [focusDepth, setFocusDepth] = useState<number>(Infinity);

  // ---- derived data (must be before early returns) ----------------------
  const nodes = useMemo(() => data?.nodes ?? [], [data]);
  const edges = useMemo(() => data?.edges ?? [], [data]);

  const nodeById = useMemo(() => {
    const m = new Map<string, GraphNode>();
    for (const n of nodes) m.set(n.id, n);
    return m;
  }, [nodes]);

  const adjacency = useMemo(() => buildAdjacency(edges), [edges]);

  const cycleFileIds = useMemo(() => {
    const s = new Set<string>();
    for (const cycle of data?.cycles ?? []) for (const id of cycle) s.add(id);
    return s;
  }, [data]);

  const complexityByPath = useMemo(() => {
    const m = new Map<string, FileComplexity>();
    for (const f of complexity?.top_files ?? []) m.set(f.path, f);
    return m;
  }, [complexity]);

  const languages = useMemo(
    () => [...new Set(nodes.map((n) => n.language))].sort(),
    [nodes],
  );

  const allPrefixes = useMemo(() => {
    const s = new Set<string>();
    for (const n of nodes) for (const p of folderPrefixes(n.path)) s.add(p);
    return s;
  }, [nodes]);

  const topLevelDirs = useMemo(
    () => new Set([...allPrefixes].filter((p) => !p.includes("/"))),
    [allPrefixes],
  );

  // Focus neighbourhood (file ids) when a single file is in focus.
  const focusFileId =
    selectedId && nodeById.has(selectedId) ? selectedId : undefined;

  const focusSets = useMemo(() => {
    if (!focusFileId) return null;
    const up =
      focusDirection !== "down"
        ? reachable(focusFileId, adjacency, "upstream", focusDepth)
        : new Set<string>();
    const down =
      focusDirection !== "up"
        ? reachable(focusFileId, adjacency, "downstream", focusDepth)
        : new Set<string>();
    return { up, down };
  }, [focusFileId, adjacency, focusDirection, focusDepth]);

  // Filtered set of files that will be rendered.
  const visibleFiles = useMemo(() => {
    let pool = nodes;
    if (focusMode && focusFileId && focusSets) {
      const keep = new Set<string>([focusFileId, ...focusSets.up, ...focusSets.down]);
      pool = pool.filter((n) => keep.has(n.id));
    }
    if (activeLanguages.size > 0) {
      pool = pool.filter((n) => activeLanguages.has(n.language));
    }
    if (cyclesOnly) {
      pool = pool.filter((n) => cycleFileIds.has(n.id));
    }
    if (hideIsolated) {
      pool = pool.filter(
        (n) => (adjacency.out.get(n.id)?.size ?? 0) + (adjacency.in.get(n.id)?.size ?? 0) > 0,
      );
    }
    return pool;
  }, [
    nodes,
    focusMode,
    focusFileId,
    focusSets,
    activeLanguages,
    cyclesOnly,
    cycleFileIds,
    hideIsolated,
    adjacency,
  ]);

  const visibleFileIds = useMemo(
    () => new Set(visibleFiles.map((n) => n.id)),
    [visibleFiles],
  );

  const clusters = useMemo(
    () => computeClusters(visibleFiles, expanded),
    [visibleFiles, expanded],
  );

  const aggregatedEdges = useMemo(
    () => aggregateEdges(edges, clusters.fileToUnit, visibleFileIds),
    [edges, clusters.fileToUnit, visibleFileIds],
  );

  const selectedUnit: GraphUnit | null = useMemo(() => {
    if (!selectedId) return null;
    const visible = clusters.units.find((u) => u.id === selectedId);
    if (visible) return visible;
    const node = nodeById.get(selectedId);
    if (!node) return null;
    return {
      id: node.id,
      kind: "file",
      label: node.path.split("/").pop() ?? node.path,
      path: node.path,
      fileIds: [node.id],
      fileCount: 1,
      language: node.language,
      totalLines: node.line_count,
      expandable: false,
      depth: 0,
    };
  }, [selectedId, clusters.units, nodeById]);

  const selectedImpact: ImpactSummary | null = useMemo(() => {
    if (!selectedUnit || selectedUnit.kind !== "file") return null;
    return computeImpact(selectedUnit.id, adjacency, nodes.length);
  }, [selectedUnit, adjacency, nodes.length]);

  const highlight: GraphHighlight | null = useMemo(() => {
    if (!selectedId) return null;
    // Only highlight when the selected id is actually a rendered unit.
    if (!clusters.units.some((u) => u.id === selectedId)) return null;

    // Focus mode: transitive reachability, mapped from file ids up to units.
    if (focusMode && focusFileId && focusSets) {
      const toUnits = (ids: Set<string>) => {
        const out = new Set<string>();
        for (const id of ids) {
          const unit = clusters.fileToUnit.get(id);
          if (unit) out.add(unit);
        }
        return out;
      };
      const focusUnit = clusters.fileToUnit.get(focusFileId) ?? focusFileId;
      const incoming = toUnits(focusSets.up);
      const outgoing = toUnits(focusSets.down);
      incoming.delete(focusUnit);
      outgoing.delete(focusUnit);
      return { focusId: focusUnit, incoming, outgoing };
    }

    // Plain selection: direct neighbours at the rendered-unit level. Works for
    // both files and collapsed folders since it reads the aggregated edges.
    const incoming = new Set<string>();
    const outgoing = new Set<string>();
    for (const e of aggregatedEdges) {
      if (e.target === selectedId) incoming.add(e.source); // source depends on selected
      if (e.source === selectedId) outgoing.add(e.target); // selected depends on target
    }
    if (incoming.size === 0 && outgoing.size === 0) return null;
    return { focusId: selectedId, incoming, outgoing };
  }, [
    selectedId,
    clusters.units,
    clusters.fileToUnit,
    focusMode,
    focusFileId,
    focusSets,
    aggregatedEdges,
  ]);

  const searchResults = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return [];
    return nodes
      .filter((n) => n.path.toLowerCase().includes(q))
      .slice(0, 30)
      .map((n) => ({ id: n.id, path: n.path }));
  }, [nodes, query]);

  // ---- actions ----------------------------------------------------------
  const applyLevel = useCallback(
    (next: ViewLevel) => {
      setLevel(next);
      if (next === "repository") setExpanded(new Set());
      else if (next === "modules") setExpanded(new Set(topLevelDirs));
      else setExpanded(new Set(allPrefixes));
    },
    [topLevelDirs, allPrefixes],
  );

  const toggleFolder = useCallback((path: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  }, []);

  const selectUnit = useCallback((unit: GraphUnit) => {
    setSelectedId(unit.id);
  }, []);

  const jumpToFile = useCallback(
    (id: string) => {
      const node = nodeById.get(id);
      if (!node) return;
      // Reveal the file by expanding all of its ancestor folders.
      setExpanded((prev) => {
        const next = new Set(prev);
        for (const p of folderPrefixes(node.path)) next.add(p);
        return next;
      });
      setSelectedId(id);
      setQuery("");
    },
    [nodeById],
  );

  const toggleLanguage = useCallback((lang: string) => {
    setActiveLanguages((prev) => {
      const next = new Set(prev);
      if (next.has(lang)) next.delete(lang);
      else next.add(lang);
      return next;
    });
  }, []);

  const focusDependents = useCallback(() => {
    setFocusDirection("up");
    setFocusMode(true);
  }, []);

  const focusDependencies = useCallback(() => {
    setFocusDirection("down");
    setFocusMode(true);
  }, []);

  const reset = useCallback(() => {
    setLevel("repository");
    setExpanded(new Set());
    setLayout("cose");
    setSelectedId(undefined);
    setQuery("");
    setActiveLanguages(new Set());
    setHideIsolated(false);
    setCyclesOnly(false);
    setFocusMode(false);
    setFocusDirection("both");
    setFocusDepth(Infinity);
  }, []);

  // Keyboard shortcuts: Esc clears the selection/focus, "f" toggles focus on
  // the current file. Ignored while typing in an input or textarea.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      if (target && /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName)) return;
      if (e.key === "Escape") {
        if (focusMode) setFocusMode(false);
        else setSelectedId(undefined);
      } else if ((e.key === "f" || e.key === "F") && focusFileId) {
        setFocusDirection("both");
        setFocusMode((v) => !v);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [focusMode, focusFileId]);

  // Deep link: ?focus=<fileId>&dir=up|down opens the graph with that file
  // focused (used by the Architecture view and AI assistant citations).
  const focusParam = searchParams.get("focus");
  useEffect(() => {
    if (!focusParam) return;
    const node = nodeById.get(focusParam);
    if (!node) return;
    setExpanded((prev) => {
      const next = new Set(prev);
      for (const p of folderPrefixes(node.path)) next.add(p);
      return next;
    });
    setSelectedId(focusParam);
    const dir = searchParams.get("dir");
    setFocusDirection(dir === "up" || dir === "down" ? dir : "both");
    setFocusMode(true);
    const next = new URLSearchParams(searchParams);
    next.delete("focus");
    next.delete("dir");
    setSearchParams(next, { replace: true });
  }, [focusParam, nodeById, searchParams, setSearchParams]);

  // ---- gates ------------------------------------------------------------
  if (gate.blocker) return gate.blocker;
  if (isLoading && !data) {
    return (
      <div className="mx-auto max-w-[1700px] space-y-4 p-4 sm:p-6">
        <PageHeaderSkeleton />
        <GraphCanvasSkeleton />
      </div>
    );
  }
  if (isError && !data) {
    return (
      <div className="p-4 sm:p-6">
        <ErrorState message={(error as Error).message} onRetry={() => void refetch()} />
      </div>
    );
  }
  if (!data || data.nodes.length === 0) {
    return (
      <div className="p-4 sm:p-6">
        <EmptyState
          title="No dependency data"
          description="Analysis hasn't produced any edges yet."
        />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-[1700px] space-y-4 p-4 sm:p-6">
      <header>
        <h1 className="text-xl font-semibold text-ink-900">Dependency graph</h1>
        <p className="text-sm text-ink-500">
          Start with the repository overview, then drill into modules and files.
          Double-click a folder to expand it; select any node to inspect and ask AI.
        </p>
      </header>

      <GraphToolbar
        level={level}
        onLevelChange={applyLevel}
        layout={layout}
        onLayoutChange={setLayout}
        query={query}
        onQueryChange={setQuery}
        searchResults={searchResults}
        onPickResult={jumpToFile}
        languages={languages}
        activeLanguages={activeLanguages}
        onToggleLanguage={toggleLanguage}
        hideIsolated={hideIsolated}
        onToggleIsolated={() => setHideIsolated((v) => !v)}
        cyclesOnly={cyclesOnly}
        onToggleCyclesOnly={() => setCyclesOnly((v) => !v)}
        focusEnabled={Boolean(focusFileId)}
        focusMode={focusMode}
        onToggleFocus={() => {
          setFocusDirection("both");
          setFocusMode((v) => !v);
        }}
        focusDepth={focusDepth}
        onFocusDepthChange={setFocusDepth}
        onReset={reset}
        stats={{
          totalFiles: data.nodes.length,
          totalEdges: data.edges.length,
          cycles: data.cycles.length,
          visibleUnits: clusters.units.length,
        }}
      />

      <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
        {clusters.units.length === 0 ? (
          <div className="flex h-[480px] items-center justify-center rounded-lg border border-ink-200 bg-surface lg:h-[640px]">
            <EmptyState
              title="Nothing matches these filters"
              description="Loosen the filters or reset the view to see the graph again."
            />
          </div>
        ) : (
          <CytoscapeGraph
            units={clusters.units}
            edges={aggregatedEdges}
            height={640}
            layout={layout}
            selectedId={selectedId}
            highlight={highlight}
            onSelectUnit={selectUnit}
            onToggleFolder={toggleFolder}
          />
        )}

        <aside className="h-[480px] overflow-hidden rounded-lg border border-ink-200 bg-surface lg:h-[640px]">
          <NodeInspector
            repositoryId={repositoryId as string}
            selected={selectedUnit}
            nodeById={nodeById}
            adjacency={adjacency}
            inCycle={selectedUnit ? cycleFileIds.has(selectedUnit.id) : false}
            complexity={selectedUnit ? complexityByPath.get(selectedUnit.path) : undefined}
            impact={selectedImpact}
            analyzedAt={repository?.analyzed_at}
            onSelectFile={jumpToFile}
            onFocusDependencies={focusDependencies}
            onFocusDependents={focusDependents}
            onToggleFolder={toggleFolder}
            folderExpanded={selectedUnit ? expanded.has(selectedUnit.path) : false}
          />
        </aside>
      </div>
    </div>
  );
}

