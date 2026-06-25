import {
  ArrowLeft,
  CalendarClock,
  ExternalLink,
  GitBranch,
  Layers,
  Star,
  UserCircle2,
} from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";

import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { PageHeaderSkeleton, TableSkeleton } from "@/components/common/Skeleton";
import { useDiscoverRepository } from "@/hooks/useDiscover";
import { cn, formatNumber, formatRelativeTime, shortRepoName } from "@/lib/format";
import type { PublicAnalysis } from "@/types/api";

/**
 * Repository overview / analysis-history page.
 *
 * Reached from a Discover card. A repository (url + branch) may have several
 * public analyses by different users; this page shows the repository header
 * plus each public analysis as a separate, selectable card. Only public
 * analyses are ever returned by the API.
 */
export function RepositoryAnalysesPage() {
  const [params] = useSearchParams();
  const url = params.get("u") ?? undefined;
  const branch = params.get("b");

  const { data, isLoading, isError, error, refetch } = useDiscoverRepository(
    url,
    branch,
  );

  if (!url) {
    return (
      <div className="mx-auto max-w-5xl p-4 sm:p-6">
        <EmptyState
          icon={<Layers className="h-10 w-10" />}
          title="No repository specified"
          description="Open this page from the Discover grid."
          action={
            <Link to="/discover" className="text-sm font-medium text-accent-600 hover:underline">
              Go to Discover
            </Link>
          }
        />
      </div>
    );
  }

  if (isLoading && !data) {
    return (
      <div className="mx-auto max-w-5xl space-y-6 p-4 sm:p-6">
        <PageHeaderSkeleton />
        <TableSkeleton rows={3} cols={4} />
      </div>
    );
  }

  if (isError && !data) {
    return (
      <div className="mx-auto max-w-5xl p-4 sm:p-6">
        <ErrorState
          title="Repository not found"
          message={(error as Error).message}
          onRetry={() => void refetch()}
        />
      </div>
    );
  }

  if (!data) return null;
  const name = shortRepoName(data.url);

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-4 sm:p-6">
      <Link
        to="/discover"
        className="inline-flex items-center gap-1.5 text-sm text-ink-500 transition-colors hover:text-ink-800"
      >
        <ArrowLeft className="h-4 w-4" /> Discover
      </Link>

      {/* Repository header */}
      <header className="space-y-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <h1 className="truncate text-xl font-semibold text-ink-900" title={name}>
              {name}
            </h1>
            <a
              href={data.url}
              target="_blank"
              rel="noreferrer noopener"
              className="mt-0.5 inline-flex items-center gap-1 break-all text-sm text-accent-600 hover:underline"
            >
              {data.url} <ExternalLink className="h-3.5 w-3.5 shrink-0" />
            </a>
          </div>
          {data.branch && (
            <span className="inline-flex shrink-0 items-center gap-1 whitespace-nowrap rounded-full border border-ink-200 bg-ink-50 px-2.5 py-1 text-xs font-medium text-ink-600">
              <GitBranch className="h-3.5 w-3.5" /> {data.branch}
            </span>
          )}
        </div>

        <div className="flex flex-wrap gap-2">
          <HeaderStat
            icon={<Layers className="h-3.5 w-3.5" />}
            label={`${data.analyses_count} public ${data.analyses_count === 1 ? "analysis" : "analyses"}`}
          />
          <HeaderStat
            icon={<Star className="h-3.5 w-3.5 text-amber-500" />}
            label={`${formatNumber(data.total_stars)} stars`}
          />
          <HeaderStat
            icon={<CalendarClock className="h-3.5 w-3.5" />}
            label={`Latest ${formatRelativeTime(data.latest_analyzed_at)}`}
          />
        </div>
      </header>

      {/* Analyses */}
      <section className="space-y-3">
        <h2 className="text-[11px] font-medium uppercase tracking-wide text-ink-400">
          Public analyses ({data.analyses.length})
        </h2>
        {data.analyses.length === 0 ? (
          <EmptyState
            icon={<Layers className="h-10 w-10" />}
            title="No public analyses"
            description="No one has shared a public analysis of this repository yet."
          />
        ) : (
          <ul className="space-y-3">
            {data.analyses.map((a, i) => (
              <li key={a.repository_id}>
                <AnalysisCard analysis={a} index={data.analyses.length - i} />
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function HeaderStat({ icon, label }: { icon: React.ReactNode; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-ink-200 bg-surface px-2.5 py-1 text-xs font-medium text-ink-600">
      {icon}
      {label}
    </span>
  );
}

function AnalysisCard({
  analysis,
  index,
}: {
  analysis: PublicAnalysis;
  index: number;
}) {
  const a = analysis;
  const analystName = a.analyst.username ?? "Unknown";
  const fresh = a.freshness?.state;
  return (
    <div className="surface flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex min-w-0 items-start gap-3">
        {a.analyst.avatar_url ? (
          <img
            src={a.analyst.avatar_url}
            alt={analystName}
            className="h-9 w-9 shrink-0 rounded-full"
          />
        ) : (
          <UserCircle2 className="h-9 w-9 shrink-0 text-ink-300" />
        )}
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-semibold text-ink-900">
              Analysis #{index}
            </span>
            {fresh && <FreshnessPill state={fresh} />}
          </div>
          <p className="mt-0.5 truncate text-xs text-ink-500">
            by{" "}
            {a.analyst.username ? (
              <Link
                to={`/u/${a.analyst.username}`}
                className="font-medium text-accent-600 hover:underline"
              >
                {a.analyst.display_name ?? a.analyst.username}
              </Link>
            ) : (
              <span className="text-ink-600">{analystName}</span>
            )}{" "}
            · {formatRelativeTime(a.analyzed_at)}
          </p>
          <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-ink-400">
            <span>{formatNumber(a.file_count)} files</span>
            <span>{formatNumber(a.total_lines)} lines</span>
            <span className="inline-flex items-center gap-1">
              <Star className="h-3 w-3 text-amber-500" /> {formatNumber(a.star_count)}
            </span>
            {a.analysis_version != null && <span>engine v{a.analysis_version}</span>}
          </div>
        </div>
      </div>
      <Link
        to={`/repos/${a.repository_id}/overview`}
        className="focus-ring inline-flex shrink-0 items-center justify-center gap-1.5 rounded-md bg-accent-600 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-700"
      >
        Open analysis
      </Link>
    </div>
  );
}

function FreshnessPill({ state }: { state: string }) {
  const map: Record<string, { label: string; cls: string }> = {
    fresh: { label: "Latest available", cls: "border-success-200 bg-success-100 text-success-500" },
    stale: { label: "Refresh recommended", cls: "border-amber-200 bg-amber-50 text-amber-700" },
    unknown: { label: "Version unknown", cls: "border-ink-200 bg-ink-50 text-ink-500" },
    unavailable: { label: "Unavailable", cls: "border-ink-200 bg-ink-50 text-ink-500" },
  };
  const v = map[state] ?? map.unknown;
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-medium",
        v!.cls,
      )}
    >
      {v!.label}
    </span>
  );
}
