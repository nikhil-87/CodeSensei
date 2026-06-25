/** Public discovery hub API client (repository-centric). */
import { apiClient } from "@/lib/api";
import type {
  DiscoverRepository,
  Paginated,
  RepositoryGroupDetail,
  RepositorySort,
} from "@/types/api";

export interface DiscoverParams {
  page?: number;
  page_size?: number;
  sort?: RepositorySort;
  q?: string;
  language?: string;
}

export const DiscoverApi = {
  /** Browse public repositories — one entry per (url, branch). */
  list: async (params: DiscoverParams = {}): Promise<Paginated<DiscoverRepository>> => {
    const { data } = await apiClient.get<Paginated<DiscoverRepository>>(
      "/discover/repositories",
      { params },
    );
    return data;
  },

  /** Fetch a repository's public analyses (the overview / history page). */
  repository: async (
    url: string,
    branch?: string | null,
  ): Promise<RepositoryGroupDetail> => {
    const { data } = await apiClient.get<RepositoryGroupDetail>(
      "/discover/repository",
      { params: { url, branch: branch ?? undefined } },
    );
    return data;
  },
};
