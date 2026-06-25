import { Star, UserCircle2 } from "lucide-react";
import { useState } from "react";
import { useParams } from "react-router-dom";

import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { Pagination } from "@/components/common/Pagination";
import { RepositoryGridSkeleton } from "@/components/common/Skeleton";
import { Spinner } from "@/components/common/Spinner";
import { RepositoryCard } from "@/components/repository/RepositoryCard";
import { useProfile, useProfileRepositories } from "@/hooks/useProfile";
import { formatNumber } from "@/lib/format";
import type { ApiError } from "@/lib/api";
import type { RepositorySort } from "@/types/api";

const PAGE_SIZE = 24;

const SORT_OPTIONS: { value: RepositorySort; label: string }[] = [
  { value: "stars", label: "Most starred" },
  { value: "recent", label: "Recently analyzed" },
  { value: "name", label: "Name (A–Z)" },
];

export function ProfilePage() {
  const { username } = useParams<{ username: string }>();
  const [sort, setSort] = useState<RepositorySort>("stars");
  const [page, setPage] = useState(1);

  const profile = useProfile(username);
  const repos = useProfileRepositories(username, { page, page_size: PAGE_SIZE, sort });

  if (profile.isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spinner />
      </div>
    );
  }

  if (profile.isError) {
    const status = (profile.error as ApiError)?.status;
    if (status === 404) {
      return (
        <div className="mx-auto max-w-3xl p-4 sm:p-6">
          <EmptyState
            icon={<UserCircle2 className="h-10 w-10" />}
            title="Profile not found"
            description={`We couldn't find a user named "${username}".`}
          />
        </div>
      );
    }
    return (
      <div className="p-4 sm:p-6">
        <ErrorState
          message={(profile.error as Error).message}
          onRetry={() => void profile.refetch()}
        />
      </div>
    );
  }

  const data = profile.data;
  if (!data) return null;

  const total = repos.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const items = repos.data?.items ?? [];
  const reposFirstLoad = repos.isLoading && !repos.data;

  return (
    <div className="mx-auto max-w-7xl p-4 sm:p-6">
      <header className="mb-8 flex flex-col items-start gap-4 sm:flex-row sm:items-center">
        {data.avatar_url ? (
          <img
            src={data.avatar_url}
            alt={data.username}
            className="h-20 w-20 rounded-full border border-ink-200"
          />
        ) : (
          <span className="flex h-20 w-20 items-center justify-center rounded-full bg-accent-100 text-2xl font-semibold text-accent-700">
            {data.username.slice(0, 2).toUpperCase()}
          </span>
        )}
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold text-ink-900">
            {data.display_name ?? data.username}
          </h1>
          <p className="text-sm text-ink-500">@{data.username}</p>
          <div className="mt-3 flex flex-wrap gap-4 text-sm text-ink-600">
            <span>
              <strong className="text-ink-900">
                {formatNumber(data.public_repository_count)}
              </strong>{" "}
              public {data.public_repository_count === 1 ? "repository" : "repositories"}
            </span>
            <span className="inline-flex items-center gap-1">
              <Star className="h-4 w-4 fill-amber-400 text-amber-500" />
              <strong className="text-ink-900">{formatNumber(data.total_stars)}</strong>{" "}
              stars received
            </span>
          </div>
        </div>
      </header>

      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-ink-500">
          Public repositories
        </h2>
        {items.length > 0 && (
          <select
            value={sort}
            onChange={(e) => {
              setSort(e.target.value as RepositorySort);
              setPage(1);
            }}
            className="h-9 rounded-md border border-ink-200 bg-surface px-3 text-sm text-ink-800 focus-ring"
            aria-label="Sort repositories"
          >
            {SORT_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        )}
      </div>

      {reposFirstLoad && <RepositoryGridSkeleton count={4} />}

      {!reposFirstLoad && items.length === 0 && (
        <EmptyState
          icon={<UserCircle2 className="h-10 w-10" />}
          title="No public repositories"
          description={`${data.username} hasn't shared any analyzed repositories yet.`}
        />
      )}

      {items.length > 0 && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {items.map((r) => (
              <RepositoryCard key={r.id} repo={r} />
            ))}
          </div>

          <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
        </>
      )}
    </div>
  );
}
