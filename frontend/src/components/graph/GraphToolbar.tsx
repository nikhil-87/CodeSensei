import {
  Crosshair,
  GitBranch,
  Layers,
  Network,
  RotateCcw,
  Search,
  X,
} from "lucide-react";
import { useState } from "react";

import { cn } from "@/lib/format";
import { colorForLanguage } from "@/lib/graphModel";

export type ViewLevel = "repository" | "modules" | "files";

export interface GraphToolbarStats {
  totalFiles: number;
  totalEdges: number;
  cycles: number;
  visibleUnits: number;
}

export interface GraphSearchResult {
  id: string;
  path: string;
}

export interface GraphToolbarProps {
  level: ViewLevel;
  onLevelChange: (level: ViewLevel) => void;
  layout: "cose" | "dagre";
  onLayoutChange: (layout: "cose" | "dagre") => void;

  query: string;
  onQueryChange: (q: string) => void;
  searchResults: GraphSearchResult[];
  onPickResult: (id: string) => void;

  languages: string[];
  activeLanguages: ReadonlySet<string>;
  onToggleLanguage: (lang: string) => void;

  hideIsolated: boolean;
  onToggleIsolated: () => void;
  cyclesOnly: boolean;
  onToggleCyclesOnly: () => void;

  focusEnabled: boolean;
  focusMode: boolean;
  onToggleFocus: () => void;
  focusDepth: number;
  onFocusDepthChange: (depth: number) => void;

  onReset: () => void;
  stats: GraphToolbarStats;
}

const LEVELS: { value: ViewLevel; label: string; hint: string }[] = [
  { value: "repository", label: "Repository", hint: "Top-level folders" },
  { value: "modules", label: "Modules", hint: "One level deeper" },
  { value: "files", label: "Files", hint: "Every file (large)" },
];

export function GraphToolbar(props: GraphToolbarProps) {
  return (
    <div className="space-y-3 rounded-lg border border-ink-200 bg-surface p-3">
      <div className="flex flex-wrap items-center gap-2">
        <SearchBox
          query={props.query}
          onQueryChange={props.onQueryChange}
          results={props.searchResults}
          onPick={props.onPickResult}
        />

        <Segmented
          icon={<Layers className="h-3.5 w-3.5" />}
          options={LEVELS.map((l) => ({ value: l.value, label: l.label, title: l.hint }))}
          value={props.level}
          onChange={(v) => props.onLevelChange(v as ViewLevel)}
        />

        <Segmented
          options={[
            { value: "cose", label: "Organic", title: "Force-directed clusters", icon: <Network className="h-3.5 w-3.5" /> },
            { value: "dagre", label: "Hierarchy", title: "Layered left-to-right", icon: <GitBranch className="h-3.5 w-3.5" /> },
          ]}
          value={props.layout}
          onChange={(v) => props.onLayoutChange(v as "cose" | "dagre")}
        />

        <Toggle
          active={props.focusMode}
          disabled={!props.focusEnabled}
          onClick={props.onToggleFocus}
          icon={<Crosshair className="h-3.5 w-3.5" />}
          title={props.focusEnabled ? "Isolate the selected file and its dependencies" : "Select a file to focus"}
        >
          Focus
        </Toggle>

        {props.focusMode && (
          <label className="inline-flex items-center gap-1.5 text-xs text-ink-500">
            <span className="hidden sm:inline">Depth</span>
            <select
              value={Number.isFinite(props.focusDepth) ? props.focusDepth : 0}
              onChange={(e) => {
                const v = Number(e.target.value);
                props.onFocusDepthChange(v === 0 ? Infinity : v);
              }}
              aria-label="Dependency depth"
              className="focus-ring h-8 rounded-md border border-ink-200 bg-surface px-2 text-xs text-ink-700"
            >
              <option value={1}>1 hop</option>
              <option value={2}>2 hops</option>
              <option value={3}>3 hops</option>
              <option value={0}>All</option>
            </select>
          </label>
        )}

        <button
          type="button"
          onClick={props.onReset}
          title="Reset view, filters and focus"
          className="focus-ring ml-auto inline-flex h-8 items-center gap-1.5 rounded-md border border-ink-200 px-2.5 text-xs font-medium text-ink-600 transition-colors hover:bg-ink-50"
        >
          <RotateCcw className="h-3.5 w-3.5" /> Reset
        </button>
      </div>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <LanguageFilter
          languages={props.languages}
          active={props.activeLanguages}
          onToggle={props.onToggleLanguage}
        />
        <div className="flex items-center gap-2">
          <Toggle active={props.hideIsolated} onClick={props.onToggleIsolated} title="Hide files with no dependencies">
            Hide isolated
          </Toggle>
          <Toggle active={props.cyclesOnly} onClick={props.onToggleCyclesOnly} title="Show only files involved in dependency cycles">
            Cycles only
          </Toggle>
        </div>

        <p className="ml-auto text-xs text-ink-500">
          {props.stats.visibleUnits} nodes shown · {props.stats.totalFiles} files ·{" "}
          {props.stats.totalEdges} edges
          {props.stats.cycles > 0 && (
            <> · <span className="text-danger-500">{props.stats.cycles} cycles</span></>
          )}
        </p>
      </div>
    </div>
  );
}

function SearchBox({
  query,
  onQueryChange,
  results,
  onPick,
}: {
  query: string;
  onQueryChange: (q: string) => void;
  results: GraphSearchResult[];
  onPick: (id: string) => void;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="relative w-full sm:w-auto">
      <div className="flex h-8 w-full items-center gap-2 rounded-md border border-ink-200 bg-surface px-2 focus-within:border-accent-400 focus-within:ring-2 focus-within:ring-accent-500/25 sm:w-72">
        <Search className="h-3.5 w-3.5 text-ink-400" />
        <input
          value={query}
          onChange={(e) => {
            onQueryChange(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 120)}
          placeholder="Search & jump to a file…"
          aria-label="Search files"
          className="h-full flex-1 border-0 bg-transparent text-xs text-ink-900 placeholder:text-ink-400 focus:outline-none focus:ring-0"
        />
        {query && (
          <button
            type="button"
            onClick={() => onQueryChange("")}
            aria-label="Clear search"
            className="text-ink-400 hover:text-ink-700"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        )}
      </div>
      {open && query.trim() && (
        <ul className="absolute z-20 mt-1 max-h-72 w-[28rem] overflow-auto rounded-md border border-ink-200 bg-surface p-1 shadow-lg">
          {results.length === 0 ? (
            <li className="px-2 py-2 text-xs text-ink-400">No matching files.</li>
          ) : (
            results.map((r) => (
              <li key={r.id}>
                <button
                  type="button"
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => {
                    onPick(r.id);
                    setOpen(false);
                  }}
                  className="focus-ring block w-full truncate rounded px-2 py-1.5 text-left font-mono text-xs text-ink-700 hover:bg-accent-50 hover:text-accent-800"
                  title={r.path}
                >
                  {r.path}
                </button>
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  );
}

function LanguageFilter({
  languages,
  active,
  onToggle,
}: {
  languages: string[];
  active: ReadonlySet<string>;
  onToggle: (lang: string) => void;
}) {
  if (languages.length <= 1) return null;
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <span className="text-[11px] uppercase tracking-wide text-ink-400">Language</span>
      {languages.map((lang) => {
        const on = active.size === 0 || active.has(lang);
        return (
          <button
            key={lang}
            type="button"
            onClick={() => onToggle(lang)}
            className={cn(
              "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium transition-colors",
              on
                ? "border-ink-200 bg-ink-50 text-ink-800"
                : "border-transparent text-ink-400 hover:text-ink-600",
            )}
          >
            <span
              className="h-2 w-2 rounded-full"
              style={{ backgroundColor: colorForLanguage(lang) }}
            />
            {lang}
          </button>
        );
      })}
    </div>
  );
}

function Segmented({
  options,
  value,
  onChange,
  icon,
}: {
  options: { value: string; label: string; title?: string; icon?: React.ReactNode }[];
  value: string;
  onChange: (v: string) => void;
  icon?: React.ReactNode;
}) {
  return (
    <div className="inline-flex items-center gap-0.5 rounded-md border border-ink-200 bg-ink-50 p-0.5">
      {icon && <span className="px-1 text-ink-400">{icon}</span>}
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          title={o.title}
          onClick={() => onChange(o.value)}
          className={cn(
            "inline-flex h-7 items-center gap-1 rounded px-2.5 text-xs font-medium transition-colors",
            value === o.value
              ? "bg-surface text-ink-900 shadow-sm"
              : "text-ink-500 hover:text-ink-800",
          )}
        >
          {o.icon}
          {o.label}
        </button>
      ))}
    </div>
  );
}

function Toggle({
  active,
  disabled,
  onClick,
  icon,
  title,
  children,
}: {
  active: boolean;
  disabled?: boolean;
  onClick: () => void;
  icon?: React.ReactNode;
  title?: string;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={title}
      className={cn(
        "inline-flex h-8 items-center gap-1.5 rounded-md border px-2.5 text-xs font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-40",
        active
          ? "border-accent-300 bg-accent-50 text-accent-800"
          : "border-ink-200 text-ink-600 hover:bg-ink-50",
      )}
    >
      {icon}
      {children}
    </button>
  );
}
