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
    } catch (error: unknown) {
      // 401 is the only genuine unauthenticated state; return null for it.
      const status =
        typeof error === "object" && error !== null && "status" in error
          ? (error as { status: number }).status
          : 0;
      if (status === 401) {
        return null;
      }
      // Re-throw network failures, timeouts, or 5xx errors so React Query
      // knows it's an error rather than wiping the authenticated session.
      throw error;
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
