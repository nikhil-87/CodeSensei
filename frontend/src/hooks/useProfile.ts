import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { ProfilesApi, type ProfileReposParams } from "@/api/profiles";

export const profileQueryKeys = {
  all: ["profile"] as const,
  detail: (username: string) => [...profileQueryKeys.all, "detail", username] as const,
  repositories: (username: string, params: ProfileReposParams) =>
    [...profileQueryKeys.all, "repositories", username, params] as const,
};

export function useProfile(username: string | undefined) {
  return useQuery({
    queryKey: profileQueryKeys.detail(username ?? ""),
    queryFn: () => ProfilesApi.get(username as string),
    enabled: Boolean(username),
  });
}

export function useProfileRepositories(
  username: string | undefined,
  params: ProfileReposParams = {},
) {
  return useQuery({
    queryKey: profileQueryKeys.repositories(username ?? "", params),
    queryFn: () => ProfilesApi.repositories(username as string, params),
    enabled: Boolean(username),
    placeholderData: keepPreviousData,
  });
}
