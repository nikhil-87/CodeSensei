import { apiClient } from "@/lib/api";
import type { ImpactRequest, ImpactResponse } from "@/types/api";

export const ImpactApi = {
  analyze: async (
    repositoryId: string,
    payload: ImpactRequest,
  ): Promise<ImpactResponse> => {
    const { data } = await apiClient.post<ImpactResponse>(
      `/repositories/${repositoryId}/impact`,
      payload,
    );
    return data;
  },
};
