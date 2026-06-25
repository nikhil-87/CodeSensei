import {
  ArrowDownRight,
  ArrowUpRight,
  Boxes,
  Braces,
  ChevronRight,
  FileCode2,
  GitFork,
  Layers,
  MessageSquarePlus,
  Network,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/common/Button";
import {
  SessionPickerModal,
  type AskAiTarget,
} from "@/components/ai-chat/SessionPickerModal";
import { cn, formatNumber } from "@/lib/format";
import {
  classifyLayer,
  layerLabel,
  type Adjacency,
  type GraphUnit,
  type ImpactSummary,
} from "@/lib/graphModel";
import type { FileComplexity, GraphNode } from "@/types/api";

interface NodeInspectorProps {
  repositoryId: string;
  selected: GraphUnit | null;
  nodeById: Map<string, GraphNode>;
  adjacency: Adjacency;
  inCycle: boolean;
  complexity?: FileComplexity;
  impact?: ImpactSummary | null;
  analyzedAt?: string | null;
  onSelectFile: (id: string) => void;
  onFocusDependencies: () => void;
  onFocusDependents: () => void;
  onToggleFolder?: (path: string) => void;
  folderExpanded?: boolean;
}

/** Prompt templates that embed the file path so the RAG model has context. */
const AI_ACTIONS: { label: string; build: (path: string) => string }[] = [
  { label: "Explain this file", build: (p) => `Explain the file \`${p}\`. What is its purpose and the key responsibilities it owns?` },
  { label: "Summarize responsibilities", build: (p) => `Summarise the responsibilities of \`${p}\` as a concise bulleted list of what it owns and provides.` },
  { label: "Find potential risks", build: (p) => `Review \`${p}\` for potential risks: bugs, fragile patterns, tight coupling, missing error handling, and maintainability concerns.` },
  { label: "Show impact of changes", build: (p) => `If I change \`${p}\`, what is the blast radius? Which files and behaviours could break, and what should I test?` },
  { label: "Explain dependencies", build: (p) => `What does \`${p}\` depend on, and why? Summarise its key dependencies and what each is used for.` },
  { label: "Explain dependents", build: (p) => `What depends on \`${p}\`? Explain the blast radius and impact of changing this file.` },
  { label: "Explain complexity", build: (p) => `Explain the complexity of \`${p}\` and point out where it could be simplified.` },
  { label: "Onboarding explainer", build: (p) => `I'm new to this codebase. Give me an onboarding explanation of \`${p}\` and how it fits into the overall architecture.` },
];

export function NodeInspector({
  repositoryId,
  selected,
  nodeById,
  adjacency,
  inCycle,
  complexity,
  impact,
  analyzedAt,
  onSelectFile,
  onFocusDependencies,
  onFocusDependents,
  onToggleFolder,
  folderExpanded,
}: NodeInspectorProps) {
  const [askTarget, setAskTarget] = useState<AskAiTarget | null>(null);

  if (!selected) {
    return (
      <div className="flex h-full flex-col items-center justify-center px-6 py-12 text-center">
        <Boxes className="mb-3 h-8 w-8 text-ink-300" />
        <p className="text-sm font-medium text-ink-600">Nothing selected</p>
        <p className="mt-1 text-xs text-ink-400">
          Click any node to inspect it. Double-click a folder to expand it.
        </p>
      </div>
    );
  }

  if (selected.kind === "folder") {
    return (
      <>
        <FolderPanel
          repositoryId={repositoryId}
          unit={selected}
          nodeById={nodeById}
          expanded={folderExpanded}
          onToggleFolder={onToggleFolder}
          onAskAI={(prompt) =>
            setAskTarget({ label: `${selected.path}/`, prompt })
          }
        />
        <SessionPickerModal
          repositoryId={repositoryId}
          target={askTarget}
          onClose={() => setAskTarget(null)}
        />
      </>
    );
  }

  const file = nodeById.get(selected.id);
  if (!file) return null;

  const layer = classifyLayer(file.path);
  const module = file.path.includes("/") ? file.path.split("/")[0] ?? "." : ".";
  const fileType = fileTypeLabel(file.path);
  const dependencies = [...(adjacency.out.get(file.id) ?? [])];
  const dependents = [...(adjacency.in.get(file.id) ?? [])];

  const openChat = (prompt?: string) => {
    setAskTarget({
      label: file.path,
      file: { id: file.id, path: file.path, language: file.language },
      prompt,
    });
  };

  return (
    <>
      <div className="flex h-full flex-col">
        <div className="flex-1 space-y-5 overflow-y-auto p-4">
          {/* Identity */}
          <div>
            <div className="flex items-start gap-2">
              <FileCode2 className="mt-0.5 h-4 w-4 shrink-0 text-accent-600" />
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-ink-900" title={file.path}>
                  {selected.label}
                </p>
                <code className="mt-0.5 block break-all font-mono text-[11px] text-ink-500">
                  {file.path}
                </code>
              </div>
            </div>
            <div className="mt-2 flex flex-wrap gap-1.5">
              <Badge tone="layer">
                <Layers className="h-3 w-3" /> {layerLabel(layer)}
              </Badge>
              <Badge tone="neutral">{file.language}</Badge>
              <Badge tone="neutral">{fileType}</Badge>
              {inCycle && <Badge tone="danger">In dependency cycle</Badge>}
            </div>
          </div>

          {/* Ask AI — primary CTA */}
          <Button
            variant="primary"
            size="sm"
            className="w-full"
            leadingIcon={<MessageSquarePlus className="h-4 w-4" />}
            onClick={() => openChat()}
          >
            Ask AI about this file
          </Button>

          {/* Impact analysis — criticality + blast radius */}
          {impact && (
            <Section icon={<ShieldAlert className="h-3 w-3" />} title="Impact analysis">
              <CriticalityMeter impact={impact} />
              <div className="mt-2 grid grid-cols-2 gap-2">
                <Metric
                  label="Impact scope"
                  value={formatNumber(impact.impactScope)}
                  hint="Files affected if changed"
                />
                <Metric
                  label="Depends on"
                  value={formatNumber(impact.dependencyReach)}
                  hint="Files it transitively needs"
                />
                <Metric
                  label="Impact depth"
                  value={`${impact.impactDepth} ${impact.impactDepth === 1 ? "hop" : "hops"}`}
                  hint="Longest dependent chain"
                />
                <Metric
                  label="Dependency depth"
                  value={`${impact.dependencyDepth} ${impact.dependencyDepth === 1 ? "hop" : "hops"}`}
                  hint="Longest dependency chain"
                />
              </div>
            </Section>
          )}

          {/* Code structure */}
          <Section icon={<Braces className="h-3 w-3" />} title="Code structure">
            <div className="grid grid-cols-2 gap-2">
              <Metric label="Lines of code" value={formatNumber(file.line_count)} />
              {complexity ? (
                <Metric
                  label="Functions"
                  value={formatNumber(complexity.function_count)}
                  hint={`${formatNumber(complexity.class_count)} classes`}
                />
              ) : (
                <Metric label="Module" value={module} mono />
              )}
              <Metric
                label="Dependents"
                value={formatNumber(dependents.length)}
                hint="Imported by"
              />
              <Metric
                label="Dependencies"
                value={formatNumber(dependencies.length)}
                hint="Imports"
              />
              {complexity && (
                <>
                  <Metric
                    label="Cyclomatic"
                    value={formatNumber(complexity.cyclomatic)}
                  />
                  <Metric
                    label="Cognitive"
                    value={formatNumber(complexity.cognitive)}
                  />
                </>
              )}
            </div>
          </Section>

          {/* Explore relationships */}
          <Section icon={<Network className="h-3 w-3" />} title="Explore relationships">
            <div className="grid grid-cols-2 gap-2">
              <RelButton
                icon={<ArrowUpRight className="h-3.5 w-3.5" />}
                label="Dependents"
                count={dependents.length}
                onClick={onFocusDependents}
                tone="up"
              />
              <RelButton
                icon={<ArrowDownRight className="h-3.5 w-3.5" />}
                label="Dependencies"
                count={dependencies.length}
                onClick={onFocusDependencies}
                tone="down"
              />
            </div>
          </Section>

          {/* Usage — related files */}
          {(dependencies.length > 0 || dependents.length > 0) && (
            <Section title="Usage">
              <RelatedList
                title="Depended on by"
                accent="up"
                ids={dependents}
                nodeById={nodeById}
                onSelect={onSelectFile}
              />
              <RelatedList
                title="Depends on"
                accent="down"
                ids={dependencies}
                nodeById={nodeById}
                onSelect={onSelectFile}
              />
            </Section>
          )}

          {/* Repository context */}
          <Section title="Repository context">
            <div className="grid grid-cols-2 gap-2">
              <Metric label="Layer" value={layerLabel(layer)} />
              <Metric label="Module" value={module} mono />
            </div>
          </Section>

          {/* AI context actions */}
          <Section
            icon={<Sparkles className="h-3 w-3 text-accent-500" />}
            title="AI actions"
          >
            <div className="flex flex-wrap gap-1.5">
              {AI_ACTIONS.map((a) => (
                <button
                  key={a.label}
                  type="button"
                  onClick={() => openChat(a.build(file.path))}
                  className="focus-ring rounded-full border border-ink-200 bg-surface px-2.5 py-1 text-[11px] font-medium text-ink-700 transition-colors hover:border-accent-300 hover:bg-accent-50 hover:text-accent-800"
                >
                  {a.label}
                </button>
              ))}
            </div>
          </Section>

          {analyzedAt && (
            <p className="border-t border-ink-100 pt-3 text-[11px] text-ink-400">
              Analysis from {new Date(analyzedAt).toLocaleString()}
            </p>
          )}
        </div>
      </div>
      <SessionPickerModal
        repositoryId={repositoryId}
        target={askTarget}
        onClose={() => setAskTarget(null)}
      />
    </>
  );
}

function FolderPanel({
  repositoryId: _repositoryId,
  unit,
  nodeById,
  expanded,
  onToggleFolder,
  onAskAI,
}: {
  repositoryId: string;
  unit: GraphUnit;
  nodeById: Map<string, GraphNode>;
  expanded?: boolean;
  onToggleFolder?: (path: string) => void;
  onAskAI: (prompt: string) => void;
}) {
  const langCounts = new Map<string, number>();
  const layerCounts = new Map<string, number>();
  for (const id of unit.fileIds) {
    const f = nodeById.get(id);
    if (!f) continue;
    langCounts.set(f.language, (langCounts.get(f.language) ?? 0) + 1);
    const l = classifyLayer(f.path);
    layerCounts.set(l, (layerCounts.get(l) ?? 0) + 1);
  }
  const topLayers = [...layerCounts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 3);

  return (
    <div className="flex h-full flex-col gap-4 p-4">
      <div>
        <div className="flex items-center gap-2">
          <GitFork className="h-4 w-4 text-accent-600" />
          <p className="truncate text-sm font-semibold text-ink-900">{unit.label}/</p>
        </div>
        <code className="mt-0.5 block break-all font-mono text-[11px] text-ink-500">
          {unit.path}
        </code>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <Metric label="Files" value={formatNumber(unit.fileCount)} />
        <Metric label="Lines" value={formatNumber(unit.totalLines)} />
      </div>

      {topLayers.length > 0 && (
        <div className="space-y-1.5">
          <SectionLabel>Dominant layers</SectionLabel>
          <div className="flex flex-wrap gap-1.5">
            {topLayers.map(([l, n]) => (
              <Badge key={l} tone="layer">
                {layerLabel(l)} · {n}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {unit.expandable && (
        <Button
          variant="secondary"
          size="sm"
          className="w-full"
          leadingIcon={<ChevronRight className={cn("h-4 w-4 transition-transform", expanded && "rotate-90")} />}
          onClick={() => onToggleFolder?.(unit.path)}
        >
          {expanded ? "Collapse module" : "Expand module"}
        </Button>
      )}

      <Button
        variant="primary"
        size="sm"
        className="w-full"
        leadingIcon={<MessageSquarePlus className="h-4 w-4" />}
        onClick={() =>
          onAskAI(
            `Give me an overview of the \`${unit.path}/\` module: its responsibilities, the main files in it, and how it relates to the rest of the codebase.`,
          )
        }
      >
        Ask AI about this module
      </Button>
    </div>
  );
}

// --------------------------------------------------------------------------
// small presentational helpers
// --------------------------------------------------------------------------
function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[11px] font-medium uppercase tracking-wide text-ink-400">
      {children}
    </p>
  );
}

/** A titled block with an optional leading icon. */
function Section({
  title,
  icon,
  children,
}: {
  title: string;
  icon?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-2">
      <p className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wide text-ink-400">
        {icon}
        {title}
      </p>
      {children}
    </div>
  );
}

/** Criticality score bar with a colour that tracks the severity label. */
function CriticalityMeter({ impact }: { impact: ImpactSummary }) {
  const tone =
    impact.criticalityLabel === "Critical"
      ? { bar: "bg-danger-500", text: "text-danger-500" }
      : impact.criticalityLabel === "High"
        ? { bar: "bg-amber-500", text: "text-amber-600" }
        : impact.criticalityLabel === "Moderate"
          ? { bar: "bg-accent-500", text: "text-accent-600" }
          : { bar: "bg-success-500", text: "text-success-500" };
  return (
    <div className="rounded-md border border-ink-100 bg-ink-50/60 px-2.5 py-2">
      <div className="flex items-center justify-between">
        <span className="text-[10px] uppercase tracking-wide text-ink-400">
          Criticality
        </span>
        <span className={cn("text-xs font-semibold", tone.text)}>
          {impact.criticalityLabel} · {impact.criticality}
        </span>
      </div>
      <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-ink-200">
        <div
          className={cn("h-full rounded-full transition-all", tone.bar)}
          style={{ width: `${Math.max(4, impact.criticality)}%` }}
        />
      </div>
    </div>
  );
}

/** A friendly file-type label derived from the extension. */
function fileTypeLabel(path: string): string {
  const base = path.split("/").pop() ?? path;
  const dot = base.lastIndexOf(".");
  if (dot <= 0) return "File";
  return `.${base.slice(dot + 1).toLowerCase()}`;
}

function Metric({
  label,
  value,
  hint,
  mono,
}: {
  label: string;
  value: string;
  hint?: string;
  mono?: boolean;
}) {
  return (
    <div className="rounded-md border border-ink-100 bg-ink-50/60 px-2.5 py-2">
      <p className="text-[10px] uppercase tracking-wide text-ink-400">{label}</p>
      <p className={cn("mt-0.5 truncate text-sm font-semibold text-ink-900", mono && "font-mono text-xs")} title={value}>
        {value}
      </p>
      {hint && <p className="text-[10px] text-ink-400">{hint}</p>}
    </div>
  );
}

function Badge({
  children,
  tone,
}: {
  children: React.ReactNode;
  tone: "layer" | "neutral" | "danger";
}) {
  const tones = {
    layer: "border-accent-200 bg-accent-50 text-accent-800",
    neutral: "border-ink-200 bg-ink-50 text-ink-600",
    danger: "border-danger-200 bg-danger-100 text-danger-500",
  } as const;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium",
        tones[tone],
      )}
    >
      {children}
    </span>
  );
}

function RelButton({
  icon,
  label,
  count,
  onClick,
  tone,
}: {
  icon: React.ReactNode;
  label: string;
  count: number;
  onClick: () => void;
  tone: "up" | "down";
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={count === 0}
      className={cn(
        "focus-ring flex items-center justify-between rounded-md border px-2.5 py-2 text-xs font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-40",
        tone === "up"
          ? "border-blue-200 text-blue-700 hover:bg-blue-50"
          : "border-amber-200 text-amber-700 hover:bg-amber-50",
      )}
    >
      <span className="flex items-center gap-1.5">
        {icon}
        {label}
      </span>
      <span className="tabular-nums">{count}</span>
    </button>
  );
}

function RelatedList({
  title,
  ids,
  nodeById,
  onSelect,
  accent,
}: {
  title: string;
  ids: string[];
  nodeById: Map<string, GraphNode>;
  onSelect: (id: string) => void;
  accent?: "up" | "down";
}) {
  if (ids.length === 0) return null;
  const shown = ids.slice(0, 8);
  const dot =
    accent === "up" ? "bg-blue-500" : accent === "down" ? "bg-amber-500" : "bg-ink-300";
  return (
    <div>
      <p className="mb-1 flex items-center gap-1.5 text-[11px] text-ink-500">
        <span className={cn("h-1.5 w-1.5 rounded-full", dot)} />
        {title} <span className="text-ink-400">({ids.length})</span>
      </p>
      <ul className="space-y-0.5">
        {shown.map((id) => {
          const node = nodeById.get(id);
          if (!node) return null;
          return (
            <li key={id}>
              <button
                type="button"
                onClick={() => onSelect(id)}
                className="focus-ring block w-full truncate rounded px-2 py-1 text-left font-mono text-[11px] text-ink-600 transition-colors hover:bg-accent-50 hover:text-accent-800"
                title={node.path}
              >
                {node.path}
              </button>
            </li>
          );
        })}
        {ids.length > shown.length && (
          <li className="px-2 text-[11px] text-ink-400">
            + {ids.length - shown.length} more
          </li>
        )}
      </ul>
    </div>
  );
}
