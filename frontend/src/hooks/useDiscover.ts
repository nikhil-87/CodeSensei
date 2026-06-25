import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { DiscoverApi, type DiscoverParams } from "@/api/discover";

export const discoverQueryKeys = {
  all: ["discover"] as const,
  list: (params: DiscoverParams) => [...discoverQueryKeys.all, "list", params] as const,
  repository: (url: string, branch?: string | null) =>
    [...discoverQueryKeys.all, "repository", url, branch ?? null] as const,
};

export function useDiscover(params: DiscoverParams = {}) {
  return useQuery({
    queryKey: discoverQueryKeys.list(params),
    queryFn: () => DiscoverApi.list(params),
    placeholderData: keepPreviousData,
  });
}

export function useDiscoverRepository(
  url: string | undefined,
  branch?: string | null,
) {
  return useQuery({
    queryKey: discoverQueryKeys.repository(url ?? "", branch),
    queryFn: () => DiscoverApi.repository(url as string, branch),
    enabled: Boolean(url),
  });
}
