import { apiClient } from "@/lib/api";
import type { ArchitectureReport } from "@/types/api";

export const ArchitectureApi = {
  report: async (repositoryId: string): Promise<ArchitectureReport> => {
    const { data } = await apiClient.get<ArchitectureReport>(
      `/repositories/${repositoryId}/architecture`,
    );
    return data;
  },
};
