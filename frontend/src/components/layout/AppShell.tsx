import { useEffect } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { X } from "lucide-react";

import { cn } from "@/lib/format";
import { useUiStore } from "@/store/uiStore";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

/**
 * Three-zone layout: persistent sidebar, sticky topbar, scrolling content.
 *
 * Responsive behaviour:
 *  - ≥ lg: the sidebar is in-flow (collapsible to an icon rail).
 *  - < lg: the sidebar is hidden and opens as an off-canvas drawer over a
 *    backdrop (the GitHub/Linear mobile pattern). It auto-closes on navigation
 *    and on Escape so it never traps the user.
 */
export function AppShell() {
  const mobileNavOpen = useUiStore((s) => s.mobileNavOpen);
  const closeMobileNav = useUiStore((s) => s.closeMobileNav);
  const location = useLocation();

  // Auto-close the drawer whenever the route changes.
  useEffect(() => {
    closeMobileNav();
  }, [location.pathname, closeMobileNav]);

  // Close on Escape; lock body scroll while the drawer is open.
  useEffect(() => {
    if (!mobileNavOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") closeMobileNav();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [mobileNavOpen, closeMobileNav]);

  return (
    <div className="flex h-full min-h-screen">
      {/* Desktop sidebar — in-flow, collapsible. */}
      <div className="hidden lg:flex">
        <Sidebar />
      </div>

      {/* Mobile drawer + backdrop. */}
      <div
        className={cn(
          "fixed inset-0 z-50 lg:hidden",
          mobileNavOpen ? "pointer-events-auto" : "pointer-events-none",
        )}
        aria-hidden={!mobileNavOpen}
      >
        <div
          className={cn(
            "absolute inset-0 bg-ink-900/50 transition-opacity duration-200",
            mobileNavOpen ? "opacity-100" : "opacity-0",
          )}
          onClick={closeMobileNav}
        />
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Navigation"
          className={cn(
            "absolute inset-y-0 left-0 flex w-[82%] max-w-xs flex-col shadow-elev transition-transform duration-200",
            mobileNavOpen ? "translate-x-0" : "-translate-x-full",
          )}
        >
          <button
            type="button"
            onClick={closeMobileNav}
            aria-label="Close navigation"
            className="focus-ring absolute right-2 top-2 z-10 rounded-md p-1.5 text-ink-500 hover:bg-ink-100"
          >
            <X className="h-5 w-5" />
          </button>
          <Sidebar mobile onNavigate={closeMobileNav} />
        </div>
      </div>

      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar />
        <main className="min-h-0 flex-1 overflow-y-auto bg-ink-50 [scrollbar-gutter:stable]">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
