import { useQuery } from "@tanstack/react-query";

import { ArchitectureApi } from "@/api/architecture";
import { DeadCodeApi } from "@/api/dead-code";
import { DependenciesApi } from "@/api/dependencies";
import { MetricsApi } from "@/api/metrics";

/** All read-only insights share the same staleness profile. */
const insightOptions = (enabled: boolean) =>
  ({ enabled, staleTime: 5 * 60_000 }) as const;

export function useDependencyGraph(
  repositoryId: string | undefined,
  enabled = true,
) {
  return useQuery({
    queryKey: ["dependencies", repositoryId],
    queryFn: () => DependenciesApi.graph(repositoryId as string),
    ...insightOptions(Boolean(repositoryId) && enabled),
  });
}

export function useComplexity(
  repositoryId: string | undefined,
  topN = 10,
  enabled = true,
) {
  return useQuery({
    queryKey: ["complexity", repositoryId, topN],
    queryFn: () => MetricsApi.complexity(repositoryId as string, topN),
    ...insightOptions(Boolean(repositoryId) && enabled),
  });
}

export function useDeadCode(repositoryId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: ["dead-code", repositoryId],
    queryFn: () => DeadCodeApi.report(repositoryId as string),
    ...insightOptions(Boolean(repositoryId) && enabled),
  });
}

export function useArchitecture(
  repositoryId: string | undefined,
  enabled = true,
) {
  return useQuery({
    queryKey: ["architecture", repositoryId],
    queryFn: () => ArchitectureApi.report(repositoryId as string),
    ...insightOptions(Boolean(repositoryId) && enabled),
  });
}
