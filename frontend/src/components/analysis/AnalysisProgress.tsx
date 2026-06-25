import {
  Boxes,
  Check,
  CircleDashed,
  FileSearch,
  FolderGit2,
  Gauge,
  Loader2,
  Network,
  Save,
  Sparkles,
  TriangleAlert,
  X,
} from "lucide-react";
import type { ComponentType } from "react";

import { cn } from "@/lib/format";

/**
 * Analysis pipeline stages. The percentage bands mirror the worker's
 * ``_STAGE_BANDS`` in ``worker/app/progress.py`` so the UI can derive a
 * per-stage state purely from the streamed ``progress`` value.
 */
interface StageDef {
  key: string;
  label: string;
  description: string;
  start: number;
  end: number;
  icon: ComponentType<{ className?: string }>;
}

const STAGES: StageDef[] = [
  { key: "clone", label: "Clone repository", description: "Fetching the source from GitHub", start: 0, end: 10, icon: FolderGit2 },
  { key: "walk", label: "Scan files", description: "Discovering source files", start: 10, end: 20, icon: FileSearch },
  { key: "parse", label: "Parse code", description: "Extracting symbols and structure", start: 20, end: 60, icon: Boxes },
  { key: "graph", label: "Dependency graph", description: "Linking files and modules", start: 60, end: 70, icon: Network },
  { key: "metrics", label: "Compute metrics", description: "Complexity and size metrics", start: 70, end: 75, icon: Gauge },
  { key: "dead_code", label: "Detect dead code", description: "Finding unreachable code", start: 75, end: 80, icon: TriangleAlert },
  { key: "architecture", label: "Analyze architecture", description: "Grouping layers and components", start: 80, end: 85, icon: Network },
  { key: "persist", label: "Save results", description: "Writing analysis to the database", start: 85, end: 92, icon: Save },
  { key: "index", label: "Build AI index", description: "Embedding code for the assistant", start: 92, end: 99, icon: Sparkles },
];

type StageState = "done" | "active" | "error" | "pending";

export interface AnalysisProgressProps {
  /** Overall progress 0-100. */
  progress: number;
  /** Latest human-readable status message from the worker. */
  message?: string | null;
  /** True once the job reached a successful terminal state. */
  succeeded?: boolean;
  /** True once the job failed. */
  failed?: boolean;
  /** Error text to surface when ``failed`` is true. */
  error?: string | null;
  className?: string;
}

function stageState(
  stage: StageDef,
  progress: number,
  succeeded: boolean,
  failed: boolean,
): StageState {
  if (succeeded) return "done";
  if (progress >= stage.end) return "done";
  if (progress >= stage.start && progress < stage.end) {
    return failed ? "error" : "active";
  }
  return "pending";
}

const ICON_WRAP: Record<StageState, string> = {
  done: "bg-success-100 text-success-500 ring-green-200",
  active: "bg-accent-100 text-accent-700 ring-accent-200",
  error: "bg-danger-100 text-danger-500 ring-red-200",
  pending: "bg-ink-50 text-ink-400 ring-ink-200",
};

const LABEL_COLOR: Record<StageState, string> = {
  done: "text-ink-900",
  active: "text-ink-900",
  error: "text-danger-500",
  pending: "text-ink-400",
};

export function AnalysisProgress({
  progress,
  message,
  succeeded = false,
  failed = false,
  error,
  className,
}: AnalysisProgressProps) {
  const clamped = Math.max(0, Math.min(100, Math.round(progress)));
  const activeStage = STAGES.find(
    (s) => clamped >= s.start && clamped < s.end,
  );

  return (
    <div className={cn("space-y-5", className)}>
      {/* Overall progress bar */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="font-medium text-ink-900">
            {succeeded
              ? "Analysis complete"
              : failed
                ? "Analysis failed"
                : (message ?? activeStage?.label ?? "Starting…")}
          </span>
          <span className="tabular-nums text-ink-500">{clamped}%</span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-ink-100">
          <div
            className={cn(
              "h-2 rounded-full transition-all duration-500",
              failed ? "bg-danger-500" : succeeded ? "bg-success-500" : "bg-accent-500",
            )}
            style={{ width: `${succeeded ? 100 : clamped}%` }}
          />
        </div>
      </div>

      {/* Stage stepper */}
      <ol className="relative space-y-1">
        {STAGES.map((stage, idx) => {
          const state = stageState(stage, clamped, succeeded, failed);
          const Icon = stage.icon;
          const isLast = idx === STAGES.length - 1;
          return (
            <li key={stage.key} className="flex gap-3">
              {/* Icon + connector */}
              <div className="flex flex-col items-center">
                <span
                  className={cn(
                    "flex h-8 w-8 shrink-0 items-center justify-center rounded-full ring-1 ring-inset transition-colors",
                    ICON_WRAP[state],
                  )}
                >
                  {state === "done" ? (
                    <Check className="h-4 w-4" />
                  ) : state === "active" ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : state === "error" ? (
                    <X className="h-4 w-4" />
                  ) : (
                    <Icon className="h-4 w-4" />
                  )}
                </span>
                {!isLast && (
                  <span
                    className={cn(
                      "my-0.5 w-0.5 flex-1 rounded-full transition-colors",
                      state === "done" ? "bg-success-200" : "bg-ink-100",
                    )}
                    style={{ minHeight: "1rem" }}
                  />
                )}
              </div>

              {/* Text */}
              <div className="pb-3 pt-1">
                <p className={cn("text-sm font-medium", LABEL_COLOR[state])}>
                  {stage.label}
                </p>
                <p className="text-xs text-ink-500">
                  {state === "active" && message ? message : stage.description}
                </p>
              </div>
            </li>
          );
        })}
      </ol>

      {/* Error detail */}
      {failed && error && (
        <div className="rounded-md border border-red-200 bg-danger-100/40 p-3">
          <div className="mb-1 flex items-center gap-1.5 text-sm font-medium text-danger-500">
            <TriangleAlert className="h-4 w-4" />
            Error
          </div>
          <pre className="max-h-48 overflow-auto whitespace-pre-wrap break-words text-xs text-danger-500">
            {error}
          </pre>
        </div>
      )}

      {/* Idle / queued hint */}
      {!succeeded && !failed && clamped === 0 && !activeStage && (
        <div className="flex items-center gap-2 text-sm text-ink-500">
          <CircleDashed className="h-4 w-4 animate-pulse" />
          Waiting for a worker to pick up the job…
        </div>
      )}
    </div>
  );
}
