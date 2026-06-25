/** Authentication client (GitHub OAuth + cookie session). */
import { apiClient, API_PREFIX } from "@/lib/api";
import type { User } from "@/types/api";

/** Full-page redirect target that kicks off the GitHub OAuth dance. */
export const githubLoginUrl = `${API_PREFIX}/auth/github/login`;

export const AuthApi = {
  /** Returns the signed-in user, or `null` when unauthenticated (401). */
  me: async (): Promise<User | null> => {
    try {
      const { data } = await apiClient.get<User>("/auth/me");
      return data;
    } catch {
      return null;
    }
  },

  logout: async (): Promise<void> => {
    await apiClient.post("/auth/logout");
  },

  /** Dev-only password-less login. 404s in production. */
  devLogin: async (username = "dev-user"): Promise<User> => {
    const { data } = await apiClient.post<User>("/auth/dev-login", { username });
    return data;
  },
};
