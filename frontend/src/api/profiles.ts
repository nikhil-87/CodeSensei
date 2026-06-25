/** Public profile API client (/users/{username}). */
import { apiClient } from "@/lib/api";
import type {
  Paginated,
  PublicProfile,
  Repository,
  RepositorySort,
} from "@/types/api";

export interface ProfileReposParams {
  page?: number;
  page_size?: number;
  sort?: RepositorySort;
}

export const ProfilesApi = {
  get: async (username: string): Promise<PublicProfile> => {
    const { data } = await apiClient.get<PublicProfile>(
      `/users/${encodeURIComponent(username)}`,
    );
    return data;
  },

  repositories: async (
    username: string,
    params: ProfileReposParams = {},
  ): Promise<Paginated<Repository>> => {
    const { data } = await apiClient.get<Paginated<Repository>>(
      `/users/${encodeURIComponent(username)}/repositories`,
      { params },
    );
    return data;
  },
};
