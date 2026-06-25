/**
 * Shared "is this repository ready?" gate for every insight page.
 *
 * Insight endpoints (dependencies, complexity, dead code, architecture,
 * impact, AI) return ``409 analysis_not_ready`` until the pipeline finishes.
 * Rather than letting each page surface that as a scary error, this hook
 * inspects the repository status and returns a friendly *blocker* element to
 * render in place of the page content:
 *
 *   - loading            → spinner
 *   - not found / error  → ErrorState with retry
 *   - pending/analyzing  → live AnalysisProgress with guidance
 *   - failed             → failure panel with a Re-analyze action
 *   - ready              → ``{ ready: true, blocker: null }`` (render content)
 *
 * Pages pass ``gate.ready`` to their insight hooks so the underlying query
 * stays disabled (no wasted 409 requests) until the data actually exists.
 * When the SSE stream reports success, the repository query is invalidated so
 * the page unlocks automatically without a manual refresh.
 */
import { useEffect, type ReactNode } from "react";
import { RefreshCw } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/common/Button";
import { Card } from "@/components/common/Card";
import { ErrorState } from "@/components/common/ErrorState";
import { Spinner } from "@/components/common/Spinner";
import { useTriggerAnalysis } from "@/hooks/useAnalysisJobs";
import { useAnalysisProgress } from "@/hooks/useAnalysisProgress";
import { repositoryQueryKeys, useRepository } from "@/hooks/useRepositories";
import { AnalysisProgress } from "./AnalysisProgress";

export interface AnalysisGateResult {
  /** True only when the repository has finished analysis and data exists. */
  ready: boolean;
  /** Element to render instead of page content while not ready, else null. */
  blocker: ReactNode | null;
}

export function useAnalysisGate(
  repositoryId: string | undefined,
): AnalysisGateResult {
  const qc = useQueryClient();
  const { data: repo, isLoading, isError, error, refetch } =
    useRepository(repositoryId);

  const isActive = repo?.status === "analyzing" || repo?.status === "pending";
  const { event } = useAnalysisProgress(
    repositoryId,
    Boolean(repositoryId) && isActive,
  );
  const trigger = useTriggerAnalysis();

  // When the pipeline finishes, refresh the repository so the gate flips to
  // ready and the page unlocks on its own.
  useEffect(() => {
    if (event?.event === "succeeded") {
      qc.invalidateQueries({
        queryKey: repositoryQueryKeys.detail(repositoryId ?? ""),
      });
      qc.invalidateQueries({ queryKey: repositoryQueryKeys.all });
    }
  }, [event?.event, qc, repositoryId]);

  if (isLoading) {
    return {
      ready: false,
      blocker: (
        <div className="flex h-64 items-center justify-center">
          <Spinner />
        </div>
      ),
    };
  }

  if (isError || !repo) {
    return {
      ready: false,
      blocker: (
        <div className="mx-auto max-w-3xl p-6">
          <ErrorState
            title="Couldn't load this repository"
            message={(error as Error)?.message}
            onRetry={() => void refetch()}
          />
        </div>
      ),
    };
  }

  if (repo.status === "ready") {
    return { ready: true, blocker: null };
  }

  if (repo.status === "failed") {
    return {
      ready: false,
      blocker: (
        <div className="mx-auto max-w-3xl space-y-4 p-6">
          <Card
            title="Analysis didn't finish"
            description="The pipeline stopped before this view could be generated. You can re-run it without re-entering anything."
          >
            <AnalysisProgress
              progress={event?.progress ?? 0}
              message={event?.message}
              failed
              error={event?.error ?? repo.error_message}
            />
            <div className="mt-5 flex justify-end">
              <Button
                leadingIcon={<RefreshCw className="h-4 w-4" />}
                loading={trigger.isPending}
                onClick={() => trigger.mutate(repo.id)}
              >
                Re-analyze
              </Button>
            </div>
          </Card>
        </div>
      ),
    };
  }

  // pending | analyzing
  return {
    ready: false,
    blocker: (
      <div className="mx-auto max-w-3xl space-y-4 p-6">
        <Card
          title="Analysis in progress"
          description="This usually takes a minute or two. You can leave this page — analysis keeps running in the background."
        >
          <AnalysisProgress
            progress={event?.progress ?? 0}
            message={event?.message ?? "Preparing analysis…"}
            succeeded={event?.event === "succeeded"}
            failed={event?.event === "failed"}
            error={event?.error}
          />
          <p className="mt-5 text-sm text-ink-500">
            This view unlocks automatically the moment analysis completes — no
            need to refresh.
          </p>
        </Card>
      </div>
    ),
  };
}
