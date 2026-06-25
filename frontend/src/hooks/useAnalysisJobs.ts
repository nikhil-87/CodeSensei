import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { AnalysisApi } from "@/api/analysis";

export const analysisQueryKeys = {
  list: (id: string) => ["analysis", id, "jobs"] as const,
  latest: (id: string) => ["analysis", id, "latest"] as const,
};

export function useAnalysisJobs(repositoryId: string | undefined) {
  return useQuery({
    queryKey: analysisQueryKeys.list(repositoryId ?? ""),
    queryFn: () => AnalysisApi.list(repositoryId as string),
    enabled: Boolean(repositoryId),
  });
}

export function useLatestAnalysisJob(repositoryId: string | undefined) {
  return useQuery({
    queryKey: analysisQueryKeys.latest(repositoryId ?? ""),
    queryFn: () => AnalysisApi.latest(repositoryId as string),
    enabled: Boolean(repositoryId),
  });
}

export function useTriggerAnalysis() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (repositoryId: string) => AnalysisApi.trigger(repositoryId),
    onSuccess: (_, repositoryId) => {
      qc.invalidateQueries({ queryKey: ["analysis", repositoryId] });
      qc.invalidateQueries({ queryKey: ["repositories"] });
    },
  });
}
