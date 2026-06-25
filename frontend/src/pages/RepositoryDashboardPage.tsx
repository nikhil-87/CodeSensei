import { useEffect, useState } from "react";
import { Check, ExternalLink, Globe, Link2, Lock, RefreshCw, Trash2 } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";

import { AnalysisProgress } from "@/components/analysis/AnalysisProgress";
import { AnalysisFreshnessBanner } from "@/components/analysis/AnalysisFreshnessBanner";
import { Button } from "@/components/common/Button";
import { Card } from "@/components/common/Card";
import { ErrorState } from "@/components/common/ErrorState";
import { Spinner } from "@/components/common/Spinner";
import { StatusBadge } from "@/components/common/StatusBadge";
import { LanguageChart } from "@/components/metrics/LanguageChart";
import { StarButton } from "@/components/repository/StarButton";
import { useMe } from "@/hooks/useAuth";
import { useTriggerAnalysis } from "@/hooks/useAnalysisJobs";
import { useAnalysisProgress } from "@/hooks/useAnalysisProgress";
import {
  repositoryQueryKeys,
  useDeleteRepository,
  useRepository,
  useSetVisibility,
} from "@/hooks/useRepositories";
import { ApiError } from "@/lib/api";
import { formatNumber, formatRelativeTime, shortRepoName } from "@/lib/format";

export function RepositoryDashboardPage() {
  const { repositoryId } = useParams<{ repositoryId: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { user } = useMe();
  const { data: repo, isLoading, error, refetch } = useRepository(repositoryId);
  const { event } = useAnalysisProgress(
    repositoryId,
    Boolean(repositoryId) &&
      (repo?.status === "analyzing" ||
        repo?.status === "pending" ||
        repo?.status === "failed"),
  );
  const trigger = useTriggerAnalysis();
  const remove = useDeleteRepository();
  const setVisibility = useSetVisibility();
  const [copied, setCopied] = useState(false);

  // Refresh the repository (and lists) once the pipeline finishes so the
  // summary metrics replace the live progress panel without a manual reload.
  useEffect(() => {
    if (event?.event === "succeeded") {
      qc.invalidateQueries({
        queryKey: repositoryQueryKeys.detail(repositoryId ?? ""),
      });
      qc.invalidateQueries({ queryKey: repositoryQueryKeys.all });
    }
  }, [event?.event, qc, repositoryId]);

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spinner />
      </div>
    );
  }
  // Only surface a full error screen when we have nothing to show. A failed
  // background refetch while the repository is already loaded must not wipe
  // the dashboard out from under the user.
  if (!repo) {
    return (
      <div className="p-4 sm:p-6">
        <ErrorState
          title={
            (error as ApiError | undefined)?.status === 404
              ? "Repository not found"
              : "Something went wrong"
          }
          message={
            (error as ApiError | undefined)?.status === 404
              ? "This repository doesn't exist or isn't shared with you."
              : (error as Error)?.message
          }
          onRetry={() => void refetch()}
        />
      </div>
    );
  }

  const isOwner = Boolean(user && repo.owner_id && repo.owner_id === user.id);

  const handleDelete = async () => {
    if (!confirm("Delete this repository and all its analysis data?")) return;
    await remove.mutateAsync(repo.id);
    navigate("/");
  };

  const handleCopyLink = async () => {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* clipboard unavailable — no-op */
    }
  };

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-4 sm:p-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-semibold text-ink-900">
              {shortRepoName(repo.url)}
            </h1>
            <StatusBadge status={repo.status} />
            {repo.is_public && (
              <span className="inline-flex items-center gap-1 rounded-full bg-accent-50 px-2 py-0.5 text-xs font-medium text-accent-700">
                <Globe className="h-3 w-3" />
                Public
              </span>
            )}
            <StarButton repo={repo} />
          </div>
          <a
            href={repo.url}
            target="_blank"
            rel="noreferrer"
            className="mt-1 inline-flex items-center gap-1 text-sm text-accent-700 hover:underline"
          >
            {repo.url}
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
        </div>

        {isOwner && (
          <div className="flex flex-wrap gap-2">
            <Button
              variant="secondary"
              leadingIcon={
                repo.is_public ? <Lock className="h-4 w-4" /> : <Globe className="h-4 w-4" />
              }
              loading={setVisibility.isPending}
              onClick={() =>
                setVisibility.mutate({ id: repo.id, isPublic: !repo.is_public })
              }
            >
              {repo.is_public ? "Make private" : "Make public"}
            </Button>
            {repo.is_public && (
              <Button
                variant="ghost"
                leadingIcon={
                  copied ? <Check className="h-4 w-4" /> : <Link2 className="h-4 w-4" />
                }
                onClick={handleCopyLink}
              >
                {copied ? "Copied" : "Copy link"}
              </Button>
            )}
            <Button
              variant="secondary"
              leadingIcon={<RefreshCw className="h-4 w-4" />}
              loading={trigger.isPending}
              onClick={() => trigger.mutate(repo.id)}
            >
              Re-analyze
            </Button>
            <Button
              variant="ghost"
              leadingIcon={<Trash2 className="h-4 w-4" />}
              onClick={handleDelete}
            >
              Delete
            </Button>
          </div>
        )}
      </header>

      {(repo.status === "analyzing" || repo.status === "pending") && (
        <Card
          title="Analysis status"
          description="Live progress of the repository analysis pipeline"
        >
          <AnalysisProgress
            progress={event?.progress ?? 0}
            message={event?.message ?? repo.error_message}
            succeeded={event?.event === "succeeded"}
            failed={event?.event === "failed"}
            error={event?.error}
          />
        </Card>
      )}

      {repo.status === "failed" && (
        <Card
          title="Analysis failed"
          description="The pipeline stopped before completing"
        >
          <AnalysisProgress
            progress={event?.progress ?? 0}
            message={event?.message}
            failed
            error={event?.error ?? repo.error_message}
          />
        </Card>
      )}

      {repo.status === "ready" && (
        <AnalysisFreshnessBanner
          repo={repo}
          canRefresh={isOwner}
          refreshing={trigger.isPending}
          onRefresh={() => trigger.mutate(repo.id)}
        />
      )}

      <div className="grid gap-6 md:grid-cols-3">
        <Card title="Files"><Big>{formatNumber(repo.file_count)}</Big></Card>
        <Card title="Lines"><Big>{formatNumber(repo.total_lines)}</Big></Card>
        <Card title="Last analyzed">
          <Big>{formatRelativeTime(repo.analyzed_at)}</Big>
          {repo.commit_hash && (
            <p className="mt-1 font-mono text-xs text-ink-500">
              commit {repo.commit_hash.slice(0, 7)}
            </p>
          )}
        </Card>
      </div>

      <Card title="Language breakdown">
        <LanguageChart packed={repo.languages} />
      </Card>
    </div>
  );
}

function Big({ children }: { children: React.ReactNode }) {
  return <p className="text-2xl font-semibold text-ink-900">{children}</p>;
}
