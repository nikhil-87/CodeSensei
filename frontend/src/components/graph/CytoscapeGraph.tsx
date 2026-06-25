import { useCallback, useEffect, useMemo, useRef } from "react";
import cytoscape, { type Core, type ElementDefinition } from "cytoscape";
// @ts-expect-error — layout plugins ship no types; the runtime is a function.
import dagre from "cytoscape-dagre";
// @ts-expect-error — layout plugins ship no types; the runtime is a function.
import coseBilkent from "cytoscape-cose-bilkent";
import CytoscapeComponent from "react-cytoscapejs";
import { Crosshair, Maximize2, Minus, Plus } from "lucide-react";

import { cn } from "@/lib/format";
import {
  colorForLanguage,
  type AggregatedEdge,
  type GraphUnit,
} from "@/lib/graphModel";
import { useThemeStore } from "@/store/themeStore";

// Register layouts once. Calling .use multiple times is safe.
cytoscape.use(dagre);
cytoscape.use(coseBilkent);

// Relationship-direction palette — shared with the inspector legend.
const COLOR_FOCUS = "#1f5fef"; // selected node
const COLOR_INCOMING = "#2563eb"; // dependents — files that depend on the focus
const COLOR_OUTGOING = "#d97706"; // dependencies — files the focus depends on

export interface GraphHighlight {
  /** The file/unit at the centre of focus. */
  focusId: string;
  /** Unit ids that depend on the focus (incoming edges → blue). */
  incoming: ReadonlySet<string>;
  /** Unit ids the focus depends on (outgoing edges → amber). */
  outgoing: ReadonlySet<string>;
}

export interface ClusterGraphProps {
  units: GraphUnit[];
  edges: AggregatedEdge[];
  height?: number;
  selectedId?: string;
  highlight?: GraphHighlight | null;
  layout?: "dagre" | "cose";
  onSelectUnit?: (unit: GraphUnit) => void;
  onToggleFolder?: (folderPath: string) => void;
  className?: string;
}

export function CytoscapeGraph({
  units,
  edges,
  height = 640,
  selectedId,
  highlight,
  layout = "cose",
  onSelectUnit,
  onToggleFolder,
  className,
}: ClusterGraphProps) {
  const cyRef = useRef<Core | null>(null);
  const theme = useThemeStore((s) => s.theme);
  const isDark = theme === "dark";
  const labelColor = isDark ? "#e3e5e8" : "#22273a";
  const nodeBorder = isDark ? "#1e1f22" : "#ffffff";
  const edgeColor = isDark ? "#3f444d" : "#c2c8d4";

  // Index units so the (singly-bound) tap handlers can resolve the latest data.
  const unitById = useMemo(() => {
    const m = new Map<string, GraphUnit>();
    for (const u of units) m.set(u.id, u);
    return m;
  }, [units]);
  const handlersRef = useRef({ onSelectUnit, onToggleFolder, unitById });
  handlersRef.current = { onSelectUnit, onToggleFolder, unitById };

  const elements: ElementDefinition[] = useMemo(() => {
    const nodeEls: ElementDefinition[] = units.map((u) => ({
      data: {
        id: u.id,
        kind: u.kind,
        label: u.kind === "folder" ? `${u.label}/  ·  ${u.fileCount}` : u.label,
        color: colorForLanguage(u.language),
        size:
          u.kind === "folder"
            ? 34 + Math.min(70, Math.sqrt(u.fileCount) * 7)
            : 14 + Math.min(40, Math.log10(Math.max(u.totalLines, 1)) * 12),
      },
    }));
    const edgeEls: ElementDefinition[] = edges.map((e, i) => ({
      data: {
        id: `e${i}`,
        source: e.source,
        target: e.target,
        weight: e.weight,
        width: 1 + Math.min(6, Math.log2(e.weight + 1)),
      },
    }));
    return [...nodeEls, ...edgeEls];
  }, [units, edges]);

  // Re-run layout whenever the visible structure changes.
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    const opts =
      layout === "dagre"
        ? {
            name: "dagre",
            rankDir: "LR",
            nodeSep: 28,
            rankSep: 70,
            animate: false,
            fit: true,
            padding: 40,
          }
        : {
            name: "cose-bilkent",
            animate: false,
            nodeDimensionsIncludeLabels: true,
            idealEdgeLength: 90,
            nodeRepulsion: 7000,
            tile: true,
            randomize: false,
            fit: true,
            padding: 40,
          };
    const run = cy.layout(opts);
    // Always re-fit once positions are final. Guards against the degenerate
    // case where an early fit latches onto collapsed/overlapping coordinates
    // and clamps zoom to the max, leaving the graph panned off-screen. A short
    // settle delay lets react-cytoscapejs's own preset layout finish first so
    // our fit isn't immediately overridden.
    run.run();
    const t = window.setTimeout(() => {
      if (cyRef.current && cyRef.current.elements().nonempty()) {
        cyRef.current.fit(cyRef.current.elements(), 40);
      }
    }, 250);
    return () => window.clearTimeout(t);
  }, [elements, layout]);

  // Selection + directional relationship highlighting.
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.batch(() => {
      cy.elements().removeClass(
        "selected dimmed focus dep-in dep-out edge-in edge-out edge-related",
      );
      if (selectedId) cy.getElementById(selectedId).addClass("selected");
      if (highlight) {
        const related = new Set<string>([
          highlight.focusId,
          ...highlight.incoming,
          ...highlight.outgoing,
        ]);
        cy.nodes().forEach((n) => {
          const id = n.id();
          if (id === highlight.focusId) n.addClass("focus");
          else if (highlight.incoming.has(id)) n.addClass("dep-in");
          else if (highlight.outgoing.has(id)) n.addClass("dep-out");
          if (!related.has(id)) n.addClass("dimmed");
        });
        cy.edges().forEach((e) => {
          const s = e.source().id();
          const t = e.target().id();
          // Edges point source → target where source depends on target.
          if (t === highlight.focusId && highlight.incoming.has(s)) {
            e.addClass("edge-in");
          } else if (s === highlight.focusId && highlight.outgoing.has(t)) {
            e.addClass("edge-out");
          } else if (related.has(s) && related.has(t)) {
            e.addClass("edge-related");
          } else {
            e.addClass("dimmed");
          }
        });
      }
    });
  }, [selectedId, highlight, elements]);

  // Hover emphasis — lifts the hovered node's immediate edges/neighbours.
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    const onOver = (evt: cytoscape.EventObject) => {
      const node = evt.target;
      node.addClass("hovered");
      node.connectedEdges().addClass("hovered");
      node.connectedEdges().connectedNodes().addClass("hovered-neighbour");
    };
    const onOut = () => {
      cy.elements().removeClass("hovered hovered-neighbour");
    };
    cy.on("mouseover", "node", onOver);
    cy.on("mouseout", "node", onOut);
    return () => {
      cy.removeListener("mouseover", "node", onOver);
      cy.removeListener("mouseout", "node", onOut);
    };
  }, [elements]);

  // ---- on-canvas navigation controls -----------------------------------
  const zoomBy = useCallback((factor: number) => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.animate(
      {
        zoom: {
          level: cy.zoom() * factor,
          position: { x: cy.width() / 2, y: cy.height() / 2 },
        },
      },
      { duration: 160 },
    );
  }, []);

  const fitAll = useCallback(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.animate({ fit: { eles: cy.elements(), padding: 40 } }, { duration: 220 });
  }, []);

  const fitSelection = useCallback(() => {
    const cy = cyRef.current;
    if (!cy || !highlight) {
      fitAll();
      return;
    }
    const ids = [highlight.focusId, ...highlight.incoming, ...highlight.outgoing];
    const eles = cy.collection(
      ids.map((id) => cy.getElementById(id)).filter((e) => e.nonempty()),
    );
    if (eles.nonempty()) {
      cy.animate(
        { fit: { eles: eles.closedNeighborhood(), padding: 60 } },
        { duration: 240 },
      );
    }
  }, [highlight, fitAll]);

  // Auto-frame the selection when a node gains focus so it's never off-screen.
  useEffect(() => {
    if (!highlight) return undefined;
    const id = window.setTimeout(() => fitSelection(), 90);
    return () => window.clearTimeout(id);
  }, [highlight, fitSelection]);

  return (
    <div
      className={cn(
        "cytoscape-host relative w-full overflow-hidden rounded-lg border border-ink-200 bg-surface",
        className,
      )}
      style={{ height }}
    >
      <CytoscapeComponent
        elements={elements}
        layout={{ name: "preset" }}
        style={{ width: "100%", height: "100%" }}
        minZoom={0.1}
        maxZoom={2.5}
        cy={(cy: Core) => {
          cyRef.current = cy;
          cy.removeListener("tap");
          cy.on("tap", "node", (evt) => {
            const unit = handlersRef.current.unitById.get(evt.target.id());
            if (unit) handlersRef.current.onSelectUnit?.(unit);
          });
          cy.on("dbltap", "node", (evt) => {
            const unit = handlersRef.current.unitById.get(evt.target.id());
            if (unit?.kind === "folder" && unit.expandable) {
              handlersRef.current.onToggleFolder?.(unit.path);
            }
          });
        }}
        stylesheet={[
          {
            selector: "node",
            style: {
              "background-color": "data(color)",
              label: "data(label)",
              "font-size": 10,
              "font-family": "Inter, system-ui, sans-serif",
              color: labelColor,
              "text-valign": "bottom",
              "text-margin-y": 5,
              "text-max-width": "120px",
              "text-wrap": "ellipsis",
              width: "data(size)",
              height: "data(size)",
              "border-color": nodeBorder,
              "border-width": 1.5,
              "transition-property": "opacity, border-width, border-color",
              "transition-duration": 150,
            },
          },
          {
            selector: "node[kind = 'folder']",
            style: {
              shape: "round-rectangle",
              "background-opacity": 0.18,
              "border-width": 2,
              "border-color": "data(color)",
              "font-weight": 600,
              "font-size": 11,
            },
          },
          {
            selector: "node.selected",
            style: { "border-color": COLOR_FOCUS, "border-width": 4 },
          },
          {
            selector: "node.focus",
            style: {
              "border-color": COLOR_FOCUS,
              "border-width": 5,
              "font-weight": 700,
              "z-index": 100,
            },
          },
          {
            selector: "node.dep-in",
            style: {
              "border-color": COLOR_INCOMING,
              "border-width": 4,
              "z-index": 50,
            },
          },
          {
            selector: "node.dep-out",
            style: {
              "border-color": COLOR_OUTGOING,
              "border-width": 4,
              "z-index": 50,
            },
          },
          {
            selector: "node.hovered",
            style: { "border-width": 4, "z-index": 90 },
          },
          {
            selector: "node.hovered-neighbour",
            style: { opacity: 1 },
          },
          {
            selector: "edge",
            style: {
              width: "data(width)",
              "line-color": edgeColor,
              "target-arrow-color": edgeColor,
              "target-arrow-shape": "triangle",
              "arrow-scale": 0.8,
              "curve-style": "bezier",
              opacity: 0.5,
              "transition-property": "opacity, line-color, width",
              "transition-duration": 150,
            },
          },
          {
            selector: "edge.edge-in",
            style: {
              "line-color": COLOR_INCOMING,
              "target-arrow-color": COLOR_INCOMING,
              opacity: 0.95,
              "z-index": 60,
            },
          },
          {
            selector: "edge.edge-out",
            style: {
              "line-color": COLOR_OUTGOING,
              "target-arrow-color": COLOR_OUTGOING,
              opacity: 0.95,
              "z-index": 60,
            },
          },
          {
            selector: "edge.edge-related",
            style: { opacity: 0.4 },
          },
          {
            selector: "edge.hovered",
            style: { opacity: 0.95, width: 3 },
          },
          {
            selector: ".dimmed",
            style: { opacity: 0.12 },
          },
        ]}
      />

      {/* On-canvas navigation controls. */}
      <div
        data-graph-overlay
        className="absolute bottom-3 right-3 flex flex-col gap-1 rounded-lg border border-ink-200 bg-surface/95 p-1 shadow-sm backdrop-blur"
      >
        <CtrlButton label="Zoom in" onClick={() => zoomBy(1.3)}>
          <Plus className="h-4 w-4" />
        </CtrlButton>
        <CtrlButton label="Zoom out" onClick={() => zoomBy(1 / 1.3)}>
          <Minus className="h-4 w-4" />
        </CtrlButton>
        <CtrlButton
          label="Fit to selection"
          onClick={fitSelection}
          disabled={!highlight}
        >
          <Crosshair className="h-4 w-4" />
        </CtrlButton>
        <CtrlButton label="Fit graph" onClick={fitAll}>
          <Maximize2 className="h-4 w-4" />
        </CtrlButton>
      </div>

      {/* Relationship legend — appears only while something is highlighted. */}
      {highlight && (
        <div
          data-graph-overlay
          className="pointer-events-none absolute left-3 top-3 flex flex-col gap-1 rounded-lg border border-ink-200 bg-surface/95 px-2.5 py-2 text-[11px] shadow-sm backdrop-blur"
        >
          <LegendRow color={COLOR_FOCUS} label="Selected" />
          <LegendRow color={COLOR_INCOMING} label="Depends on this" />
          <LegendRow color={COLOR_OUTGOING} label="This depends on" />
        </div>
      )}
    </div>
  );
}

function CtrlButton({
  children,
  label,
  onClick,
  disabled,
}: {
  children: React.ReactNode;
  label: string;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      title={label}
      className="focus-ring inline-flex h-7 w-7 items-center justify-center rounded-md text-ink-600 transition-colors hover:bg-ink-100 disabled:cursor-not-allowed disabled:opacity-40"
    >
      {children}
    </button>
  );
}

function LegendRow({ color, label }: { color: string; label: string }) {
  return (
    <span className="flex items-center gap-1.5 text-ink-600">
      <span className="h-2 w-2 rounded-full" style={{ backgroundColor: color }} />
      {label}
    </span>
  );
}
