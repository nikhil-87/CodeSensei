import { Link } from "react-router-dom";

import { StatusBadge } from "@/components/common/StatusBadge";
import { StarButton } from "@/components/repository/StarButton";
import { formatNumber, formatRelativeTime, parseLanguages, shortRepoName } from "@/lib/format";
import type { Repository } from "@/types/api";

interface RepositoryCardProps {
  repo: Repository;
}

export function RepositoryCard({ repo }: RepositoryCardProps) {
  const languages = parseLanguages(repo.languages).slice(0, 3);
  const name = shortRepoName(repo.url);
  return (
    <Link
      to={`/repos/${repo.id}/overview`}
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
        <StatusBadge status={repo.status} className="shrink-0 whitespace-nowrap" />
      </div>

      <dl className="grid grid-cols-3 gap-2 text-xs">
        <Stat label="Files" value={formatNumber(repo.file_count)} />
        <Stat label="Lines" value={formatNumber(repo.total_lines)} />
        <Stat label="Branch" value={repo.branch ?? repo.default_branch ?? "—"} />
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
          Analyzed {formatRelativeTime(repo.analyzed_at)}
        </p>
        <div className="flex shrink-0 items-center gap-1.5">
          {repo.freshness?.state === "stale" && (
            <span
              className="whitespace-nowrap rounded-full border border-amber-200 bg-amber-50 px-1.5 py-0.5 text-[10px] font-medium text-amber-700"
              title={repo.freshness.reasons[0] ?? "A newer analysis pipeline is available"}
            >
              Refresh recommended
            </span>
          )}
          <StarButton repo={repo} size="sm" />
        </div>
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
