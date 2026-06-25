import { Star } from "lucide-react";
import { Link } from "react-router-dom";
import { useState } from "react";

import { Button } from "@/components/common/Button";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { Pagination } from "@/components/common/Pagination";
import { RepositoryGridSkeleton } from "@/components/common/Skeleton";
import { RepositoryCard } from "@/components/repository/RepositoryCard";
import { useStarredRepositories } from "@/hooks/useStars";

const PAGE_SIZE = 24;

export function StarredPage() {
  const [page, setPage] = useState(1);
  const { data, isLoading, isError, error, refetch } = useStarredRepositories({
    page,
    page_size: PAGE_SIZE,
  });

  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const items = data?.items ?? [];
  const isFirstLoad = isLoading && !data;
  const hasData = Boolean(data);

  return (
    <div className="mx-auto max-w-7xl p-4 sm:p-6">
      <header className="mb-6">
        <div className="flex items-center gap-2">
          <Star className="h-5 w-5 fill-amber-400 text-amber-500" />
          <h1 className="text-xl font-semibold text-ink-900">Your stars</h1>
        </div>
        <p className="mt-1 text-sm text-ink-500">
          Repositories you&apos;ve starred, most recently starred first.
        </p>
      </header>

      {isFirstLoad && <RepositoryGridSkeleton />}

      {!isFirstLoad && isError && !hasData && (
        <ErrorState message={(error as Error).message} onRetry={() => void refetch()} />
      )}

      {hasData && items.length === 0 && (
        <EmptyState
          icon={<Star className="h-10 w-10" />}
          title="No starred repositories yet"
          description="Star repositories from the discovery hub or any repository page to keep track of them here."
          action={
            <Link to="/discover">
              <Button>Explore repositories</Button>
            </Link>
          }
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
