import { Boxes, Plus, WifiOff } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/common/Button";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { RepositoryGridSkeleton } from "@/components/common/Skeleton";
import { RepositoryAddDialog } from "@/components/repository/RepositoryAddDialog";
import { RepositoryCard } from "@/components/repository/RepositoryCard";
import { useRepositories } from "@/hooks/useRepositories";

export function RepositoryListPage() {
  const [open, setOpen] = useState(false);
  const { data, isLoading, isError, error, refetch, isFetching } = useRepositories({
    page: 1,
    page_size: 50,
  });

  // State precedence is deliberate and mutually exclusive:
  //   1. first-ever load  → skeletons (never a blank screen)
  //   2. load failed, no cached data → full error state
  //   3. have data        → always render it; a failed *background* refetch
  //      shows a subtle inline notice instead of blowing away the list.
  const isFirstLoad = isLoading && !data;
  const hasData = Boolean(data);
  const items = data?.items ?? [];
  const showBackgroundError = isError && hasData;

  return (
    <div className="mx-auto max-w-7xl p-4 sm:p-6">
      <header className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
        <div className="min-w-0">
          <h1 className="text-xl font-semibold text-ink-900">Repositories</h1>
          <p className="mt-1 text-sm text-ink-500">
            Submit a GitHub URL to clone, analyze, and explore.
          </p>
        </div>
        <Button
          onClick={() => setOpen(true)}
          leadingIcon={<Plus className="h-4 w-4" />}
          className="w-full whitespace-nowrap sm:w-auto sm:shrink-0"
        >
          Add repository
        </Button>
      </header>

      {showBackgroundError && (
        <div className="mb-4 flex items-center gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
          <WifiOff className="h-4 w-4 shrink-0" />
          <span className="flex-1">
            Couldn&apos;t refresh — showing the latest results we have.
          </span>
          <button
            type="button"
            onClick={() => void refetch()}
            className="font-medium underline-offset-2 hover:underline"
          >
            Retry
          </button>
        </div>
      )}

      {isFirstLoad && <RepositoryGridSkeleton />}

      {!isFirstLoad && isError && !hasData && (
        <ErrorState
          message={(error as Error).message}
          onRetry={() => void refetch()}
        />
      )}

      {hasData && items.length === 0 && (
        <EmptyState
          icon={<Boxes className="h-10 w-10" />}
          title="No repositories yet"
          description="Submit a GitHub repository above to start your first analysis."
          action={<Button onClick={() => setOpen(true)}>Add repository</Button>}
        />
      )}

      {hasData && items.length > 0 && (
        <div
          className={
            // Dim slightly while a background refetch is in flight so the page
            // feels responsive without a jarring spinner takeover.
            isFetching && !isFirstLoad ? "opacity-60 transition-opacity" : undefined
          }
        >
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {items.map((r) => (
              <RepositoryCard key={r.id} repo={r} />
            ))}
          </div>
        </div>
      )}

      <RepositoryAddDialog open={open} onClose={() => setOpen(false)} />
    </div>
  );
}

