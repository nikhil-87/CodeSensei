import { AlertTriangle, RefreshCw } from "lucide-react";

import { Button } from "@/components/common/Button";
import type { Repository } from "@/types/api";

interface AnalysisFreshnessBannerProps {
  repo: Repository;
  /** Only owners can trigger a re-analysis. */
  canRefresh: boolean;
  refreshing: boolean;
  onRefresh: () => void;
}

/**
 * Non-blocking banner shown when a repository's stored analysis was produced by
 * an older pipeline (``stale``) or before version tracking existed (``unknown``).
 *
 * We deliberately do NOT hide or fake the underlying data — we keep showing what
 * we have and tell the user plainly that it may be out of date, which features
 * are affected, and offer a one-click refresh. Fresh / unavailable analyses
 * render nothing.
 */
export function AnalysisFreshnessBanner({
  repo,
  canRefresh,
  refreshing,
  onRefresh,
}: AnalysisFreshnessBannerProps) {
  const freshness = repo.freshness;
  if (!freshness) return null;
  if (freshness.state !== "stale" && freshness.state !== "unknown") return null;

  const heading =
    freshness.state === "unknown"
      ? "This analysis predates version tracking"
      : "This analysis is out of date";

  return (
    <div
      role="status"
      className="rounded-lg border border-amber-300 bg-amber-50 p-4 dark:border-amber-500/40 dark:bg-amber-500/10"
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex gap-3">
          <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-amber-600 dark:text-amber-400" />
          <div className="space-y-2">
            <p className="text-sm font-semibold text-amber-900 dark:text-amber-200">
              {heading}
            </p>
            {freshness.reasons.length > 0 && (
              <ul className="list-disc space-y-0.5 pl-4 text-sm text-amber-800 dark:text-amber-200/90">
                {freshness.reasons.map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
            )}
            {freshness.affected_features.length > 0 && (
              <p className="text-xs text-amber-700 dark:text-amber-300/80">
                Affected: {freshness.affected_features.join(", ")}. Results shown
                below may be incomplete until you refresh.
              </p>
            )}
          </div>
        </div>

        {canRefresh && freshness.can_refresh && (
          <Button
            variant="secondary"
            leadingIcon={<RefreshCw className="h-4 w-4" />}
            loading={refreshing}
            onClick={onRefresh}
          >
            Refresh analysis
          </Button>
        )}
      </div>
    </div>
  );
}
