/** Analysis-job control + SSE progress stream. */
import { apiClient, API_PREFIX } from "@/lib/api";
import { openSse } from "@/lib/sse";
import type { AnalysisJob, AnalysisProgressEvent } from "@/types/api";

export const AnalysisApi = {
  trigger: async (repositoryId: string): Promise<AnalysisJob> => {
    const { data } = await apiClient.post<AnalysisJob>(
      `/repositories/${repositoryId}/analyze`,
    );
    return data;
  },

  list: async (repositoryId: string): Promise<AnalysisJob[]> => {
    const { data } = await apiClient.get<AnalysisJob[]>(
      `/repositories/${repositoryId}/jobs`,
    );
    return data;
  },

  latest: async (repositoryId: string): Promise<AnalysisJob> => {
    const { data } = await apiClient.get<AnalysisJob>(
      `/repositories/${repositoryId}/jobs/latest`,
    );
    return data;
  },

  /**
   * Subscribe to the server-sent progress stream for a repository.
   *
   * The async iterator completes when the server emits a terminal event
   * (succeeded / failed) or when ``signal`` aborts.
   */
  events: async function* (
    repositoryId: string,
    signal?: AbortSignal,
  ): AsyncIterableIterator<AnalysisProgressEvent> {
    const stream = openSse({
      url: `${API_PREFIX}/repositories/${repositoryId}/events`,
      method: "GET",
      signal,
    });
    for await (const evt of stream) {
      try {
        yield JSON.parse(evt.data) as AnalysisProgressEvent;
      } catch {
        // ignore malformed event
      }
    }
  },
};
