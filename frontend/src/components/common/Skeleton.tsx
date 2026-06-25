import { cn } from "@/lib/format";

/**
 * A neutral, animated placeholder block used while data loads. Prefer these
 * over a lone centred spinner: matching the shape of the eventual content
 * eliminates layout shift and the "blank then pop" flash.
 */
export function Skeleton({
  className,
  style,
}: {
  className?: string;
  style?: React.CSSProperties;
}) {
  return (
    <div
      aria-hidden
      style={style}
      className={cn("animate-pulse rounded-md bg-ink-200/70", className)}
    />
  );
}

/** A skeleton shaped like a {@link RepositoryCard}, for list/grid loading. */
export function RepositoryCardSkeleton() {
  return (
    <div className="surface flex flex-col gap-3 p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1 space-y-2">
          <Skeleton className="h-4 w-2/3" />
          <Skeleton className="h-3 w-full" />
        </div>
        <Skeleton className="h-5 w-16 rounded-full" />
      </div>
      <div className="grid grid-cols-3 gap-2">
        <Skeleton className="h-8" />
        <Skeleton className="h-8" />
        <Skeleton className="h-8" />
      </div>
      <div className="flex gap-1.5">
        <Skeleton className="h-4 w-20 rounded-full" />
        <Skeleton className="h-4 w-16 rounded-full" />
      </div>
      <div className="flex items-center justify-between pt-1">
        <Skeleton className="h-3 w-24" />
        <Skeleton className="h-7 w-14 rounded-full" />
      </div>
    </div>
  );
}

/** A responsive grid of {@link RepositoryCardSkeleton}s. */
export function RepositoryGridSkeleton({ count = 8 }: { count?: number }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {Array.from({ length: count }).map((_, i) => (
        <RepositoryCardSkeleton key={i} />
      ))}
    </div>
  );
}

/** Page title + one-line description placeholder, for analysis page headers. */
export function PageHeaderSkeleton() {
  return (
    <div className="space-y-2">
      <Skeleton className="h-6 w-48" />
      <Skeleton className="h-4 w-80 max-w-full" />
    </div>
  );
}

/** A bordered card containing a bar-chart-shaped placeholder. */
export function ChartSkeleton({ bars = 12 }: { bars?: number }) {
  return (
    <div className="surface p-5">
      <Skeleton className="mb-4 h-4 w-40" />
      <div className="flex h-48 items-end gap-2">
        {Array.from({ length: bars }).map((_, i) => (
          <Skeleton
            key={i}
            className="flex-1"
            // Deterministic varied heights so it reads like a chart, not blocks.
            style={{ height: `${30 + ((i * 37) % 65)}%` }}
          />
        ))}
      </div>
    </div>
  );
}

/** A bordered card containing a header row + data rows, for tables. */
export function TableSkeleton({ rows = 8, cols = 5 }: { rows?: number; cols?: number }) {
  return (
    <div className="surface overflow-hidden p-0">
      <div className="flex gap-4 border-b border-ink-200 bg-ink-50 px-4 py-3">
        {Array.from({ length: cols }).map((_, i) => (
          <Skeleton key={i} className="h-3 flex-1" />
        ))}
      </div>
      <div className="divide-y divide-ink-100">
        {Array.from({ length: rows }).map((_, r) => (
          <div key={r} className="flex items-center gap-4 px-4 py-3">
            {Array.from({ length: cols }).map((_, c) => (
              <Skeleton key={c} className={cn("h-3 flex-1", c === 0 && "flex-[2]")} />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

/** A large canvas placeholder with scattered node dots, for graph views. */
export function GraphCanvasSkeleton() {
  const dots = [
    { top: "20%", left: "18%" },
    { top: "32%", left: "44%" },
    { top: "24%", left: "70%" },
    { top: "52%", left: "28%" },
    { top: "58%", left: "60%" },
    { top: "44%", left: "82%" },
    { top: "72%", left: "40%" },
    { top: "68%", left: "74%" },
    { top: "80%", left: "16%" },
  ];
  return (
    <div className="surface relative h-[60vh] min-h-[400px] overflow-hidden">
      {dots.map((d, i) => (
        <div
          key={i}
          aria-hidden
          className="absolute h-10 w-10 animate-pulse rounded-full bg-ink-200/70"
          style={{ top: d.top, left: d.left }}
        />
      ))}
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-sm text-ink-400">Building graph…</span>
      </div>
    </div>
  );
}

