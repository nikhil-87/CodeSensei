import { QueryClient } from "@tanstack/react-query";

/**
 * Query client tuned for an analysis dashboard:
 *
 * - Long ``staleTime`` for read-heavy graph / metric endpoints — the
 *   backend snapshot only changes when an analysis job re-runs.
 * - One automatic retry on transient 5xx; never retry on 4xx (those are
 *   client-side errors we can't recover from by retrying).
 * - Refetch on window focus is disabled because most of our pages render
 *   thousands of nodes and a focus refetch would jitter the layout.
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000, // 1 minute
      gcTime: 5 * 60_000, // 5 minutes
      refetchOnWindowFocus: false,
      retry: (failureCount, error: unknown) => {
        const status =
          typeof error === "object" && error !== null && "status" in error
            ? (error as { status: number }).status
            : 0;
        if (status >= 400 && status < 500) return false;
        return failureCount < 1;
      },
    },
    mutations: {
      retry: false,
    },
  },
});
