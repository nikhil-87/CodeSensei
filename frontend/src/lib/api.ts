/**
 * Axios instance configured for the FastAPI backend.
 *
 * In dev: requests go to /api which Vite proxies to VITE_API_BASE_URL.
 * In prod: Nginx proxies /api to the backend container — same path.
 *
 * We deliberately do NOT throw on 4xx; consumers (TanStack Query) handle
 * status codes via the response and surface user-friendly errors.
 */
import axios, { AxiosError } from "axios";
import { apiConfig } from "./config";

export const API_PREFIX = apiConfig.prefix;

export const apiClient = axios.create({
  baseURL: API_PREFIX,
  timeout: apiConfig.timeout,
  headers: { "Content-Type": "application/json" },
  // Send the httpOnly session cookie on every request (same-origin in prod,
  // proxied in dev). Required for authenticated endpoints.
  withCredentials: true,
});

interface ApiErrorBody {
  /** Stable machine-readable code, e.g. "analysis_not_ready". */
  error?: string;
  /** Human-readable message from our DomainError handler. */
  message?: string;
  /** Structured, error-specific context (e.g. an existing repository_id). */
  details?: Record<string, unknown>;
  /** FastAPI default error shape (auth dependencies, raw HTTPException). */
  detail?: string;
}

apiClient.interceptors.response.use(
  (resp) => resp,
  (error: AxiosError<ApiErrorBody>) => {
    const status = error.response?.status ?? 0;
    const body = error.response?.data;

    // Translate low-level transport failures into calm, human guidance so a
    // user never sees raw text like "timeout of 30000ms exceeded" or
    // "Network Error". These have no HTTP response attached.
    let message: string;
    if (!error.response) {
      const isTimeout =
        error.code === "ECONNABORTED" || /timeout/i.test(error.message);
      message = isTimeout
        ? "This is taking longer than expected. Please check your connection and try again."
        : "We couldn't reach the server. Please check your connection and try again.";
    } else if (status === 401) {
      // Surfaced by guards; keep it gentle for the rare cases it reaches a view.
      message = "Your session has expired. Please sign in again.";
    } else if (status >= 500) {
      message =
        "Something went wrong on our end. Please try again in a moment.";
    } else {
      // 4xx domain errors carry a human message from our DomainError handler;
      // fall back through the FastAPI shapes, never to a bare status word.
      message =
        body?.message ??
        body?.detail ??
        "Something went wrong. Please try again.";
    }

    return Promise.reject(
      new ApiError(message, status, error, body?.error, body?.details),
    );
  },
);

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly cause?: unknown,
    /** Machine-readable code from the backend, e.g. "analysis_not_ready". */
    public readonly code?: string,
    /** Structured context from the backend's error body. */
    public readonly details?: Record<string, unknown>,
  ) {
    super(message);
    this.name = "ApiError";
  }
}
