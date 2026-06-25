import { apiClient } from "@/lib/api";
import type { DeadCodeReport } from "@/types/api";

export const DeadCodeApi = {
  report: async (repositoryId: string): Promise<DeadCodeReport> => {
    const { data } = await apiClient.get<DeadCodeReport>(
      `/repositories/${repositoryId}/dead-code`,
    );
    return data;
  },
};
