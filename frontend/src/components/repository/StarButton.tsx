import { Star } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { useMe } from "@/hooks/useAuth";
import { useToggleStar } from "@/hooks/useStars";
import { cn, formatNumber } from "@/lib/format";
import type { Repository } from "@/types/api";

interface StarButtonProps {
  repo: Pick<Repository, "id" | "star_count" | "viewer_has_starred">;
  size?: "sm" | "md";
  /** When true, render only the icon toggle without the numeric count. */
  hideCount?: boolean;
  className?: string;
}

/**
 * GitHub-style star toggle.
 *
 * Fully controlled: the displayed state comes straight from ``repo`` (the
 * query cache), and the optimistic update lives in {@link useToggleStar}. This
 * is deliberate — keeping no local copy of the count means every star button
 * for the same repo stays in lock-step and a double-click can never
 * double-count. The button is disabled while a toggle is in flight, so a
 * second click can't race the first.
 *
 * Anonymous users are routed to sign-in. Safe to nest inside a clickable card:
 * it stops propagation so the toggle never triggers the parent navigation.
 */
export function StarButton({ repo, size = "md", hideCount, className }: StarButtonProps) {
  const navigate = useNavigate();
  const { isAuthenticated } = useMe();
  const toggle = useToggleStar();

  const starred = repo.viewer_has_starred;
  const compact = size === "sm";

  const handleClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();

    if (!isAuthenticated) {
      navigate("/login");
      return;
    }
    if (toggle.isPending) return;

    toggle.mutate({ repositoryId: repo.id, starred });
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={toggle.isPending}
      aria-pressed={starred}
      aria-label={starred ? "Unstar repository" : "Star repository"}
      title={isAuthenticated ? (starred ? "Unstar" : "Star") : "Sign in to star"}
      className={cn(
        "group inline-flex items-center gap-1.5 rounded-full border font-medium transition-all focus-ring",
        "disabled:cursor-not-allowed disabled:opacity-70",
        compact ? "h-7 px-2.5 text-xs" : "h-8 px-3 text-sm",
        starred
          ? "border-amber-200 bg-amber-50 text-amber-700 hover:border-amber-300 hover:bg-amber-100"
          : "border-ink-200 bg-surface text-ink-600 hover:border-ink-300 hover:bg-ink-50 hover:text-ink-800",
        className,
      )}
    >
      <Star
        className={cn(
          "shrink-0 transition-transform group-active:scale-90",
          compact ? "h-3.5 w-3.5" : "h-4 w-4",
          starred ? "fill-amber-400 text-amber-500" : "text-ink-400",
        )}
      />
      {!hideCount && (
        <span className="tabular-nums">{formatNumber(repo.star_count)}</span>
      )}
    </button>
  );
}

