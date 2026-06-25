import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
  type QueryClient,
} from "@tanstack/react-query";

import { StarsApi, type ListStarsParams } from "@/api/stars";
import { repositoryQueryKeys } from "@/hooks/useRepositories";
import type { Paginated, Repository, StarState } from "@/types/api";

export const starQueryKeys = {
  all: ["stars"] as const,
  mine: (params: ListStarsParams) => [...starQueryKeys.all, "mine", params] as const,
};

export function useStarredRepositories(params: ListStarsParams = {}) {
  return useQuery({
    queryKey: starQueryKeys.mine(params),
    queryFn: () => StarsApi.listMine(params),
    placeholderData: keepPreviousData,
  });
}

// ---------------------------------------------------------------------------
// Cache helpers
// ---------------------------------------------------------------------------
function isRepository(value: unknown): value is Repository {
  return (
    typeof value === "object" &&
    value !== null &&
    "id" in value &&
    "viewer_has_starred" in value
  );
}

function isPaginatedRepositories(value: unknown): value is Paginated<Repository> {
  return (
    typeof value === "object" &&
    value !== null &&
    "items" in value &&
    Array.isArray((value as Paginated<Repository>).items)
  );
}

/**
 * Apply a patch to *every* cached query that references this repository — the
 * detail query and any paginated list (repositories, discovery, profile,
 * stars). Centralizing the mutation here is what guarantees a single source of
 * truth: there is no per-component star state to drift or double-count.
 *
 * ``deriveCount`` receives the repo's current count in each cache so we can
 * either apply an authoritative value (on success) or a relative delta
 * (optimistically) consistently across caches.
 */
function patchRepositoryEverywhere(
  qc: QueryClient,
  repositoryId: string,
  patch: { starred: boolean; deriveCount: (current: number) => number },
): void {
  const caches = qc.getQueryCache().findAll();
  for (const cache of caches) {
    const data = cache.state.data;
    if (!data) continue;

    if (isRepository(data) && data.id === repositoryId) {
      const next: Repository = {
        ...data,
        viewer_has_starred: patch.starred,
        star_count: Math.max(0, patch.deriveCount(data.star_count)),
      };
      qc.setQueryData(cache.queryKey, next);
      continue;
    }

    if (isPaginatedRepositories(data)) {
      if (!data.items.some((r) => r.id === repositoryId)) continue;
      const next: Paginated<Repository> = {
        ...data,
        items: data.items.map((r) =>
          r.id === repositoryId
            ? {
                ...r,
                viewer_has_starred: patch.starred,
                star_count: Math.max(0, patch.deriveCount(r.star_count)),
              }
            : r,
        ),
      };
      qc.setQueryData(cache.queryKey, next);
    }
  }
}

interface ToggleVars {
  repositoryId: string;
  /** The repo's *current* starred state — i.e. the direction to toggle from. */
  starred: boolean;
}

/**
 * Toggle a star with centralized, race-safe optimistic updates.
 *
 * - ``onMutate`` cancels in-flight repo queries and optimistically flips the
 *   star in every cache, snapshotting them for rollback.
 * - ``onError`` restores the snapshot.
 * - ``onSuccess`` writes the server's authoritative count to every cache.
 * - ``onSettled`` invalidates the stars list (membership changed) so it
 *   re-fetches in the background.
 *
 * Because all state lives in the query cache, multiple star buttons for the
 * same repo always agree, and a double-submit cannot double-count.
 */
export function useToggleStar() {
  const qc = useQueryClient();

  return useMutation<
    StarState,
    Error,
    ToggleVars,
    { snapshot: Array<[readonly unknown[], unknown]> }
  >({
    mutationFn: ({ repositoryId, starred }: ToggleVars) =>
      starred ? StarsApi.unstar(repositoryId) : StarsApi.star(repositoryId),

    onMutate: async ({ repositoryId, starred }) => {
      await qc.cancelQueries({ queryKey: repositoryQueryKeys.all });

      // Snapshot every cache so we can roll back on failure.
      const snapshot = qc
        .getQueryCache()
        .findAll()
        .map((c) => [c.queryKey, c.state.data] as [readonly unknown[], unknown]);

      const delta = starred ? -1 : 1;
      patchRepositoryEverywhere(qc, repositoryId, {
        starred: !starred,
        deriveCount: (current) => current + delta,
      });

      return { snapshot };
    },

    onError: (_err, _vars, context) => {
      if (!context) return;
      for (const [key, data] of context.snapshot) {
        qc.setQueryData(key, data);
      }
    },

    onSuccess: (state, { repositoryId }) => {
      patchRepositoryEverywhere(qc, repositoryId, {
        starred: state.starred,
        deriveCount: () => state.star_count,
      });
    },

    onSettled: () => {
      // Membership of the "your stars" list changed — refetch in background.
      qc.invalidateQueries({ queryKey: starQueryKeys.all });
    },
  });
}

