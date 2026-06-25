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
    retry: false,
  });

  return {
    user: query.data ?? null,
    isLoading: query.isLoading,
    isAuthenticated: !!query.data,
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
