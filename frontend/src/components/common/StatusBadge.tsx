import { cn } from "@/lib/format";
import type { AnalysisJobStatus, RepositoryStatus } from "@/types/api";

type Status = AnalysisJobStatus | RepositoryStatus;

interface StatusBadgeProps {
  status: Status;
  label?: string;
  className?: string;
}

const STATUS_CLASSES: Record<Status, string> = {
  // Repository
  pending: "bg-ink-100 text-ink-700 ring-ink-200",
  analyzing: "bg-accent-100 text-accent-700 ring-accent-200",
  ready: "bg-success-100 text-success-500 ring-green-200",
  failed: "bg-danger-100 text-danger-500 ring-red-200",
  // Job (queued/running shadow analyzing)
  queued: "bg-ink-100 text-ink-700 ring-ink-200",
  running: "bg-accent-100 text-accent-700 ring-accent-200",
  succeeded: "bg-success-100 text-success-500 ring-green-200",
  cancelled: "bg-ink-100 text-ink-500 ring-ink-200",
};

export function StatusBadge({ status, label, className }: StatusBadgeProps) {
  return (
    <span
      data-status={status}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset",
        STATUS_CLASSES[status],
        className,
      )}
    >
      <span className="inline-block h-1.5 w-1.5 rounded-full bg-current opacity-70" />
      {label ?? status}
    </span>
  );
}
