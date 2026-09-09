/** Auth state via TanStack Query — the `/auth/me` endpoint is the source of truth. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { AuthApi } from "@/api/auth";
import type { User } from "@/types/api";

export const ME_QUERY_KEY = ["auth", "me"] as const;

export function useMe() {
  const query = useQuery<User | null>({
    queryKey: ME_QUERY_KEY,
    queryFn: AuthApi.me,
    staleTime: 5 * 60 * 1000,
    retry: (failureCount, error) => {
      const status =
        typeof error === "object" && error !== null && "status" in error
          ? (error as { status: number }).status
          : 0;
      if (status === 401) return false;
      return failureCount < 2;
    },
  });

  return {
    user: query.data ?? null,
    isLoading: query.isPending || query.isLoading,
    isPending: query.isPending,
    isError: query.isError,
    error: query.error,
    isAuthenticated: Boolean(query.data),
    refetch: query.refetch,
  };
}

export function useLogout() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: AuthApi.logout,
    onSuccess: () => {
      qc.setQueryData(ME_QUERY_KEY, null);
      qc.clear();
    },
  });
}

export function useDevLogin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (username?: string) => AuthApi.devLogin(username),
    onSuccess: (user) => {
      qc.setQueryData(ME_QUERY_KEY, user);
    },
  });
}
