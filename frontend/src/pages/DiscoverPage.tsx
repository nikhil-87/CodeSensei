import { Compass, Search } from "lucide-react";
import { useState } from "react";

import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { Pagination } from "@/components/common/Pagination";
import { RepositoryGridSkeleton } from "@/components/common/Skeleton";
import { DiscoverRepositoryCard } from "@/components/repository/DiscoverRepositoryCard";
import { useDiscover } from "@/hooks/useDiscover";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import type { RepositorySort } from "@/types/api";

const PAGE_SIZE = 24;

const SORT_OPTIONS: { value: RepositorySort; label: string }[] = [
  { value: "stars", label: "Most starred" },
  { value: "recent", label: "Recently analyzed" },
  { value: "name", label: "Name (A–Z)" },
];

export function DiscoverPage() {
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<RepositorySort>("stars");
  const [page, setPage] = useState(1);

  const q = useDebouncedValue(search.trim(), 300);
  const { data, isLoading, isError, error, refetch, isFetching } = useDiscover({
    page,
    page_size: PAGE_SIZE,
    sort,
    q: q || undefined,
  });

  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const items = data?.items ?? [];
  const isFirstLoad = isLoading && !data;
  const hasData = Boolean(data);

  // Any filter change resets to the first page.
  const onSearchChange = (value: string) => {
    setSearch(value);
    setPage(1);
  };
  const onSortChange = (value: RepositorySort) => {
    setSort(value);
    setPage(1);
  };

  return (
    <div className="mx-auto max-w-7xl p-4 sm:p-6">
      <header className="mb-6">
        <div className="flex items-center gap-2">
          <Compass className="h-5 w-5 text-accent-600" />
          <h1 className="text-xl font-semibold text-ink-900">Discover</h1>
        </div>
        <p className="mt-1 text-sm text-ink-500">
          Browse public repositories analyzed by the community. Each repository
          may have multiple public analyses — open one to compare them.
        </p>
      </header>

      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-400" />
          <input
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search by repository or owner…"
            className="h-10 w-full rounded-md border border-ink-200 bg-surface pl-9 pr-3 text-sm text-ink-800 placeholder:text-ink-400 focus-ring"
          />
        </div>
        <select
          value={sort}
          onChange={(e) => onSortChange(e.target.value as RepositorySort)}
          className="h-10 rounded-md border border-ink-200 bg-surface px-3 text-sm text-ink-800 focus-ring"
          aria-label="Sort repositories"
        >
          {SORT_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </div>

      {isFirstLoad && <RepositoryGridSkeleton />}

      {!isFirstLoad && isError && !hasData && (
        <ErrorState message={(error as Error).message} onRetry={() => void refetch()} />
      )}

      {hasData && items.length === 0 && (
        <EmptyState
          icon={<Compass className="h-10 w-10" />}
          title={q ? "No matching repositories" : "Nothing public yet"}
          description={
            q
              ? "Try a different search term or clear the filter."
              : "Public repositories will appear here once they've been analyzed and shared."
          }
        />
      )}

      {items.length > 0 && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {items.map((r) => (
              <DiscoverRepositoryCard
                key={`${r.url}\u0000${r.branch ?? ""}`}
                repo={r}
              />
            ))}
          </div>

          <Pagination
            page={page}
            totalPages={totalPages}
            onPageChange={setPage}
            summary={`${total.toLocaleString()} ${
              total === 1 ? "repository" : "repositories"
            }${isFetching ? " · updating…" : ""}`}
          />
        </>
      )}
    </div>
  );
}
