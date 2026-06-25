import { apiClient } from "@/lib/api";
import type { DependencyGraph } from "@/types/api";

export const DependenciesApi = {
  graph: async (repositoryId: string): Promise<DependencyGraph> => {
    const { data } = await apiClient.get<DependencyGraph>(
      `/repositories/${repositoryId}/dependencies`,
    );
    return data;
  },
};
