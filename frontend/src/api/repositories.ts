/** Repository CRUD client. */
import { apiClient } from "@/lib/api";
import type {
  AnalysisJob,
  Paginated,
  Repository,
  RepositoryCreateInput,
  RepositoryStatus,
} from "@/types/api";

export interface ListRepositoriesParams {
  page?: number;
  page_size?: number;
  status?: RepositoryStatus;
}

export const RepositoriesApi = {
  list: async (params: ListRepositoriesParams = {}): Promise<Paginated<Repository>> => {
    const { data } = await apiClient.get<Paginated<Repository>>("/repositories", {
      params,
    });
    return data;
  },

  get: async (id: string): Promise<Repository> => {
    const { data } = await apiClient.get<Repository>(`/repositories/${id}`);
    return data;
  },

  /** POST /repositories returns the *job* that was enqueued. */
  create: async (input: RepositoryCreateInput): Promise<AnalysisJob> => {
    const { data } = await apiClient.post<AnalysisJob>("/repositories", input);
    return data;
  },

  setVisibility: async (id: string, isPublic: boolean): Promise<Repository> => {
    const { data } = await apiClient.patch<Repository>(
      `/repositories/${id}/visibility`,
      { is_public: isPublic },
    );
    return data;
  },

  remove: async (id: string): Promise<void> => {
    await apiClient.delete(`/repositories/${id}`);
  },
};
