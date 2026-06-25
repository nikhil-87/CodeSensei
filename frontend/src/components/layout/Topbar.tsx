import { LogOut, Menu } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";

import { Button } from "@/components/common/Button";
import { ThemeToggle } from "@/components/common/ThemeToggle";
import { useLogout, useMe } from "@/hooks/useAuth";
import { useUiStore } from "@/store/uiStore";

export function Topbar() {
  const toggle = useUiStore((s) => s.toggleSidebar);
  const openMobileNav = useUiStore((s) => s.openMobileNav);
  const navigate = useNavigate();
  const { user, isAuthenticated } = useMe();
  const logout = useLogout();

  const handleLogout = () => {
    logout.mutate(undefined, {
      onSuccess: () => navigate("/login", { replace: true }),
    });
  };

  return (
    <header className="flex h-14 items-center justify-between border-b border-ink-200 bg-surface px-3 sm:px-4">
      <div className="flex items-center gap-3">
        {/* Mobile: open the off-canvas drawer. */}
        <Button
          variant="ghost"
          size="sm"
          className="lg:hidden"
          onClick={openMobileNav}
          aria-label="Open navigation"
        >
          <Menu className="h-4 w-4" />
        </Button>
        {/* Desktop: collapse the in-flow sidebar to an icon rail. */}
        <Button
          variant="ghost"
          size="sm"
          className="hidden lg:inline-flex"
          onClick={toggle}
          aria-label="Toggle sidebar"
        >
          <Menu className="h-4 w-4" />
        </Button>
      </div>
      <div className="flex items-center gap-2">
        <ThemeToggle />
        {isAuthenticated && user ? (
          <div className="flex items-center gap-2 pl-2">
            <Link
              to={`/u/${user.username}`}
              className="flex items-center gap-2 rounded-md px-1 py-0.5 hover:bg-ink-100"
              title="View your public profile"
            >
              {user.avatar_url ? (
                <img
                  src={user.avatar_url}
                  alt={user.username}
                  className="h-7 w-7 rounded-full border border-ink-200"
                />
              ) : (
                <span className="flex h-7 w-7 items-center justify-center rounded-full bg-accent-100 text-xs font-semibold text-accent-700">
                  {user.username.slice(0, 2).toUpperCase()}
                </span>
              )}
              <span className="hidden text-sm text-ink-700 sm:inline">
                {user.username}
              </span>
            </Link>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleLogout}
              loading={logout.isPending}
              aria-label="Sign out"
              leadingIcon={<LogOut className="h-4 w-4" />}
            >
              <span className="hidden sm:inline">Sign out</span>
            </Button>
          </div>
        ) : (
          <Button
            variant="secondary"
            size="sm"
            onClick={() => navigate("/login")}
          >
            Sign in
          </Button>
        )}
      </div>
    </header>
  );
}
