import { ChevronLeft, ChevronRight } from "lucide-react";

import { cn } from "@/lib/format";

interface PaginationProps {
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  /** Optional summary text shown on the left (e.g. "128 repositories"). */
  summary?: string;
  className?: string;
}

/**
 * A production-grade, responsive pager.
 *
 *  - Mobile: compact "Prev / Page x of y / Next" with icon-only chevrons so it
 *    never overflows a narrow viewport.
 *  - ≥ sm: numbered page buttons with leading/trailing ellipsis for long ranges.
 *
 * Always centres the controls; the optional summary floats left on wider
 * screens and stacks above on mobile.
 */
export function Pagination({
  page,
  totalPages,
  onPageChange,
  summary,
  className,
}: PaginationProps) {
  if (totalPages <= 1 && !summary) return null;

  const go = (p: number) => onPageChange(Math.min(totalPages, Math.max(1, p)));
  const canPrev = page > 1;
  const canNext = page < totalPages;

  return (
    <nav
      aria-label="Pagination"
      className={cn(
        "mt-6 flex flex-col items-center gap-3 sm:flex-row sm:justify-between",
        className,
      )}
    >
      {summary ? (
        <p className="order-2 text-xs text-ink-500 sm:order-1 sm:text-sm">{summary}</p>
      ) : (
        <span className="hidden sm:block" />
      )}

      {totalPages > 1 && (
        <div className="order-1 flex items-center gap-1 sm:order-2">
          <PagerButton
            ariaLabel="Previous page"
            disabled={!canPrev}
            onClick={() => go(page - 1)}
          >
            <ChevronLeft className="h-4 w-4" />
            <span className="hidden sm:inline">Prev</span>
          </PagerButton>

          {/* Numbered pages — sm and up. */}
          <ul className="hidden items-center gap-1 sm:flex">
            {buildPages(page, totalPages).map((p, i) =>
              p === "…" ? (
                <li
                  key={`gap-${i}`}
                  className="px-1.5 text-sm text-ink-400 select-none"
                  aria-hidden
                >
                  …
                </li>
              ) : (
                <li key={p}>
                  <button
                    type="button"
                    onClick={() => go(p)}
                    aria-label={`Page ${p}`}
                    aria-current={p === page ? "page" : undefined}
                    className={cn(
                      "focus-ring inline-flex h-8 min-w-[2rem] items-center justify-center rounded-md px-2 text-sm font-medium transition-colors",
                      p === page
                        ? "bg-accent-600 text-white"
                        : "text-ink-600 hover:bg-ink-100",
                    )}
                  >
                    {p}
                  </button>
                </li>
              ),
            )}
          </ul>

          {/* Compact indicator — mobile only. */}
          <span className="px-2 text-sm text-ink-600 sm:hidden">
            {page} / {totalPages}
          </span>

          <PagerButton
            ariaLabel="Next page"
            disabled={!canNext}
            onClick={() => go(page + 1)}
          >
            <span className="hidden sm:inline">Next</span>
            <ChevronRight className="h-4 w-4" />
          </PagerButton>
        </div>
      )}
    </nav>
  );
}

function PagerButton({
  children,
  onClick,
  disabled,
  ariaLabel,
}: {
  children: React.ReactNode;
  onClick: () => void;
  disabled: boolean;
  ariaLabel: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={ariaLabel}
      className="focus-ring inline-flex h-8 items-center gap-1 rounded-md border border-ink-200 bg-surface px-2 text-sm font-medium text-ink-700 transition-colors hover:bg-ink-50 disabled:cursor-not-allowed disabled:opacity-50 sm:px-2.5"
    >
      {children}
    </button>
  );
}

/**
 * Returns the page tokens to render, e.g. [1, "…", 4, 5, 6, "…", 20].
 * Always shows first/last and a window around the current page.
 */
function buildPages(current: number, total: number): (number | "…")[] {
  const delta = 1;
  const range: number[] = [];
  for (
    let i = Math.max(2, current - delta);
    i <= Math.min(total - 1, current + delta);
    i++
  ) {
    range.push(i);
  }

  const pages: (number | "…")[] = [1];
  if (range.length > 0) {
    const first = range[0]!;
    const last = range[range.length - 1]!;
    if (first > 2) pages.push("…");
    pages.push(...range);
    if (last < total - 1) pages.push("…");
  } else if (total > 2) {
    pages.push("…");
  }
  if (total > 1) pages.push(total);

  return pages;
}
