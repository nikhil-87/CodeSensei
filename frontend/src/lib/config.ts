/**
 * Centralized configuration module for the frontend application.
 * 
 * All configurable values are defined here to ensure:
 * 1. Single source of truth for frontend configuration
 * 2. Easy environment-based overrides via import.meta.env
 * 3. Type-safe configuration access
 * 4. Consistent defaults across the application
 * 
 * Usage:
 *   import { config } from '@/lib/config';
 *   const timeout = config.api.timeout;
 */

// =============================================================================
// Environment Detection
// =============================================================================

export const isDevelopment = import.meta.env.DEV;
export const isProduction = import.meta.env.PROD;
export const mode = import.meta.env.MODE;

// =============================================================================
// API Configuration
// =============================================================================

export const apiConfig = {
  /** Base URL prefix for API calls (proxied in dev, direct in prod) */
  prefix: '/api/v1',
  
  /** Request timeout in milliseconds */
  timeout: Number(import.meta.env.VITE_API_TIMEOUT ?? 30000),
  
  /** Maximum file size for uploads in bytes (default: 50MB) */
  maxUploadSize: Number(import.meta.env.VITE_MAX_UPLOAD_SIZE ?? 52428800),
  
  /** Retry configuration */
  retry: {
    /** Maximum number of retry attempts */
    maxAttempts: Number(import.meta.env.VITE_API_RETRY_ATTEMPTS ?? 3),
    /** Base delay between retries in milliseconds */
    baseDelay: Number(import.meta.env.VITE_API_RETRY_DELAY ?? 1000),
  },
} as const;

// =============================================================================
// UI Configuration
// =============================================================================

export const uiConfig = {
  /** Default page size for paginated lists */
  defaultPageSize: Number(import.meta.env.VITE_DEFAULT_PAGE_SIZE ?? 20),
  
  /** Maximum items per page */
  maxPageSize: Number(import.meta.env.VITE_MAX_PAGE_SIZE ?? 100),
  
  /** Debounce delay for search inputs (ms) */
  searchDebounceMs: Number(import.meta.env.VITE_SEARCH_DEBOUNCE ?? 300),
  
  /** Toast notification duration (ms) */
  toastDurationMs: Number(import.meta.env.VITE_TOAST_DURATION ?? 5000),
  
  /** Auto-refresh interval for analysis status (ms) */
  analysisRefreshIntervalMs: Number(import.meta.env.VITE_ANALYSIS_REFRESH_INTERVAL ?? 2000),
} as const;

// =============================================================================
// Feature Flags
// =============================================================================

export const features = {
  /** Enable debug mode (shows extra info in UI) */
  debug: import.meta.env.VITE_DEBUG === 'true' || isDevelopment,
  
  /** Enable analytics tracking */
  analytics: import.meta.env.VITE_ENABLE_ANALYTICS === 'true',
  
  /** Enable SSE streaming for chat */
  streamingChat: import.meta.env.VITE_ENABLE_STREAMING !== 'false',
  
  /** Enable dark mode */
  darkMode: import.meta.env.VITE_ENABLE_DARK_MODE !== 'false',
} as const;

// =============================================================================
// Application Metadata
// =============================================================================

export const appMeta = {
  /** Application name */
  name: import.meta.env.VITE_APP_NAME ?? 'CodeSensei',
  
  /** Application version */
  version: import.meta.env.VITE_APP_VERSION ?? '1.0.0',
  
  /** Support email */
  supportEmail: import.meta.env.VITE_SUPPORT_EMAIL ?? '',
  
  /** Documentation URL */
  docsUrl: import.meta.env.VITE_DOCS_URL ?? '',
} as const;

// =============================================================================
// Combined Configuration Export
// =============================================================================

export const config = {
  api: apiConfig,
  ui: uiConfig,
  features,
  app: appMeta,
  isDevelopment,
  isProduction,
  mode,
} as const;

// Default export for convenience
export default config;

// =============================================================================
// Type Exports
// =============================================================================

export type ApiConfig = typeof apiConfig;
export type UIConfig = typeof uiConfig;
export type Features = typeof features;
export type AppMeta = typeof appMeta;
export type Config = typeof config;
