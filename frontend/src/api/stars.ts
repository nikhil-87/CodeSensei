/** Star (GitHub-style) API client. */
import { apiClient } from "@/lib/api";
import type { Paginated, Repository, StarState } from "@/types/api";

export interface ListStarsParams {
  page?: number;
  page_size?: number;
}

export const StarsApi = {
  /** Star a repository (idempotent). */
  star: async (repositoryId: string): Promise<StarState> => {
    const { data } = await apiClient.put<StarState>(
      `/repositories/${repositoryId}/star`,
    );
    return data;
  },

  /** Remove a star (idempotent). */
  unstar: async (repositoryId: string): Promise<StarState> => {
    const { data } = await apiClient.delete<StarState>(
      `/repositories/${repositoryId}/star`,
    );
    return data;
  },

  /** Repositories the authenticated user has starred. */
  listMine: async (params: ListStarsParams = {}): Promise<Paginated<Repository>> => {
    const { data } = await apiClient.get<Paginated<Repository>>("/me/stars", {
      params,
    });
    return data;
  },
};
