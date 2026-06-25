/// <reference types="vite/client" />

interface ImportMetaEnv {
  // API Configuration
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_API_TIMEOUT?: string;
  readonly VITE_API_RETRY_ATTEMPTS?: string;
  readonly VITE_API_RETRY_DELAY?: string;
  readonly VITE_MAX_UPLOAD_SIZE?: string;

  // UI Configuration
  readonly VITE_DEFAULT_PAGE_SIZE?: string;
  readonly VITE_MAX_PAGE_SIZE?: string;
  readonly VITE_SEARCH_DEBOUNCE?: string;
  readonly VITE_TOAST_DURATION?: string;
  readonly VITE_ANALYSIS_REFRESH_INTERVAL?: string;

  // Feature Flags
  readonly VITE_DEBUG?: string;
  readonly VITE_ENABLE_ANALYTICS?: string;
  readonly VITE_ENABLE_STREAMING?: string;
  readonly VITE_ENABLE_DARK_MODE?: string;

  // Application Metadata
  readonly VITE_APP_NAME?: string;
  readonly VITE_APP_VERSION?: string;
  readonly VITE_SUPPORT_EMAIL?: string;
  readonly VITE_DOCS_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
