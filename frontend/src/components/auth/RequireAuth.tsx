import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";

import { Spinner } from "@/components/common/Spinner";
import { useMe } from "@/hooks/useAuth";

/**
 * Gate for routes that require a signed-in user. While the session is being
 * resolved we show a spinner; unauthenticated visitors are redirected to the
 * login screen. Public/shared repository routes deliberately do NOT use this
 * guard — anonymous access there is enforced (and limited) by the backend.
 */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { isLoading, isAuthenticated, isError, refetch } = useMe();

  if (isLoading) {
    return (
      <div className="flex h-full min-h-[60vh] items-center justify-center">
        <Spinner className="h-8 w-8" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex h-full min-h-[60vh] flex-col items-center justify-center gap-3">
        <p className="text-sm text-ink-600">Unable to verify your session.</p>
        <button
          type="button"
          onClick={() => void refetch()}
          className="rounded-md bg-accent-600 px-3.5 py-1.5 text-xs font-medium text-white hover:bg-accent-700"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}
