import { apiClient } from "@/lib/api";
import type { ComplexityRanking } from "@/types/api";

export const MetricsApi = {
  complexity: async (
    repositoryId: string,
    topN = 10,
  ): Promise<ComplexityRanking> => {
    const { data } = await apiClient.get<ComplexityRanking>(
      `/repositories/${repositoryId}/complexity`,
      { params: { top_n: topN } },
    );
    return data;
  },
};
