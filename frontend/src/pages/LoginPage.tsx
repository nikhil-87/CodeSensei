import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { Compass, Github } from "lucide-react";

import { githubLoginUrl } from "@/api/auth";
import { Button } from "@/components/common/Button";
import { Logo } from "@/components/common/Logo";
import { Spinner } from "@/components/common/Spinner";
import { useDevLogin, useMe } from "@/hooks/useAuth";
import { isDevelopment } from "@/lib/config";

/**
 * Unauthenticated landing screen. Primary path is GitHub OAuth; a dev-only
 * password-less shortcut is shown when running locally so the multi-tenant
 * flow can be exercised without registering an OAuth app.
 *
 * If the visitor is already signed in (e.g. they navigated here by hand, or
 * mock auth is enabled), bounce them straight to their workspace — a logged-in
 * user should never sit on a login screen.
 */
export function LoginPage() {
  const navigate = useNavigate();
  const { isAuthenticated, isLoading } = useMe();
  const devLogin = useDevLogin();
  const [devUser, setDevUser] = useState("dev-user");

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-ink-50">
        <Spinner className="h-8 w-8" />
      </div>
    );
  }

  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  const handleDevLogin = () => {
    devLogin.mutate(devUser || "dev-user", {
      onSuccess: () => navigate("/", { replace: true }),
    });
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-ink-50 p-6">
      <div className="w-full max-w-md rounded-2xl border border-ink-200 bg-surface p-8 shadow-sm">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-4 flex h-20 w-20 items-center justify-center rounded-2xl bg-accent-500 shadow-card ring-1 ring-accent-600/20">
            <Logo className="h-14 w-14 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-ink-900">CodeSensei</h1>
          <p className="mt-2 text-sm text-ink-500">
            Sign in to analyze repositories and chat with your codebase.
          </p>
        </div>

        <a href={githubLoginUrl} className="block">
          <Button
            size="lg"
            className="w-full"
            leadingIcon={<Github className="h-5 w-5" />}
          >
            Continue with GitHub
          </Button>
        </a>

        {isDevelopment && (
          <div className="mt-6 border-t border-ink-200 pt-6">
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-ink-400">
              Developer login
            </p>
            <div className="flex gap-2">
              <input
                value={devUser}
                onChange={(e) => setDevUser(e.target.value)}
                placeholder="username"
                className="min-w-0 flex-1 rounded-md border border-ink-200 px-3 text-sm focus-ring"
              />
              <Button
                variant="secondary"
                onClick={handleDevLogin}
                loading={devLogin.isPending}
              >
                Dev sign in
              </Button>
            </div>
            {devLogin.isError && (
              <p className="mt-2 text-xs text-danger-500">
                Dev login is disabled on this server.
              </p>
            )}
          </div>
        )}

        {/* No account needed to explore what the community has shared. */}
        <div className="mt-6 border-t border-ink-200 pt-6 text-center">
          <Link
            to="/discover"
            className="inline-flex items-center gap-1.5 text-sm font-medium text-accent-700 hover:text-accent-800 hover:underline"
          >
            <Compass className="h-4 w-4" />
            Browse public repositories
          </Link>
          <p className="mt-1 text-xs text-ink-400">No account required</p>
        </div>
      </div>
    </div>
  );
}

