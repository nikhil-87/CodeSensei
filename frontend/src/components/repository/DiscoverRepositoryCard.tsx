import { GitBranch, Layers, Star } from "lucide-react";
import { Link } from "react-router-dom";

import { formatNumber, formatRelativeTime, parseLanguages, shortRepoName } from "@/lib/format";
import type { DiscoverRepository } from "@/types/api";

interface DiscoverRepositoryCardProps {
  repo: DiscoverRepository;
}

/**
 * A repository-centric Discover card. One card per (url, branch) — it
 * represents *all* public analyses of a repository, not a single analysis.
 * Clicking opens the repository overview, which lists every public analysis.
 */
export function DiscoverRepositoryCard({ repo }: DiscoverRepositoryCardProps) {
  const languages = parseLanguages(repo.languages).slice(0, 3);
  const name = shortRepoName(repo.url);
  const to = {
    pathname: "/discover/r",
    search: `?u=${encodeURIComponent(repo.url)}${
      repo.branch ? `&b=${encodeURIComponent(repo.branch)}` : ""
    }`,
  };

  return (
    <Link
      to={to}
      className="surface group flex min-w-0 flex-col gap-3 p-5 transition-colors hover:border-accent-200 hover:bg-accent-50/40"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <h3
            className="truncate text-sm font-semibold text-ink-900 group-hover:text-accent-700"
            title={name}
          >
            {name}
          </h3>
          <p className="truncate text-xs text-ink-500" title={repo.url}>
            {repo.url}
          </p>
        </div>
        {repo.branch && (
          <span
            className="inline-flex shrink-0 items-center gap-1 whitespace-nowrap rounded-full border border-ink-200 bg-ink-50 px-2 py-0.5 text-[11px] font-medium text-ink-600"
            title={`Branch ${repo.branch}`}
          >
            <GitBranch className="h-3 w-3" /> {repo.branch}
          </span>
        )}
      </div>

      <dl className="grid grid-cols-3 gap-2 text-xs">
        <Stat label="Analyses" value={formatNumber(repo.analyses_count)} />
        <Stat label="Files" value={formatNumber(repo.file_count)} />
        <Stat label="Lines" value={formatNumber(repo.total_lines)} />
      </dl>

      {languages.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {languages.map((l) => (
            <span
              key={l.language}
              className="max-w-full truncate rounded-full bg-ink-100 px-2 py-0.5 text-[11px] font-medium text-ink-600"
            >
              {l.language} · {formatNumber(l.count)}
            </span>
          ))}
        </div>
      )}

      <div className="mt-auto flex items-center justify-between gap-2 pt-1">
        <p className="min-w-0 truncate text-[11px] text-ink-400">
          Latest analysis {formatRelativeTime(repo.latest_analyzed_at)}
        </p>
        <span className="inline-flex shrink-0 items-center gap-2 text-[11px] text-ink-500">
          <span
            className="inline-flex items-center gap-1"
            title={`${repo.analyses_count} public ${repo.analyses_count === 1 ? "analysis" : "analyses"}`}
          >
            <Layers className="h-3.5 w-3.5" /> {formatNumber(repo.analyses_count)}
          </span>
          <span className="inline-flex items-center gap-1" title="Total stars">
            <Star className="h-3.5 w-3.5 text-amber-500" /> {formatNumber(repo.total_stars)}
          </span>
        </span>
      </div>
    </Link>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="min-w-0">
      <dt className="text-[11px] uppercase tracking-wide text-ink-400">{label}</dt>
      <dd className="truncate text-sm font-medium text-ink-800" title={String(value)}>
        {value}
      </dd>
    </div>
  );
}
