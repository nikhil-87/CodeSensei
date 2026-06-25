import { Moon, Sun } from "lucide-react";

import { cn } from "@/lib/format";
import { useThemeStore } from "@/store/themeStore";

/**
 * Discord-style pill switch that flips between light and dark themes. The knob
 * slides and swaps a sun/moon glyph; state is persisted by the theme store.
 */
export function ThemeToggle() {
  const theme = useThemeStore((s) => s.theme);
  const toggleTheme = useThemeStore((s) => s.toggleTheme);
  const isDark = theme === "dark";

  return (
    <button
      type="button"
      role="switch"
      aria-checked={isDark}
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
      title={isDark ? "Switch to light mode" : "Switch to dark mode"}
      onClick={toggleTheme}
      className={cn(
        "focus-ring relative inline-flex h-7 w-12 shrink-0 items-center rounded-full",
        "border border-ink-200 transition-colors",
        isDark ? "bg-accent-600" : "bg-ink-200",
      )}
    >
      <span
        className={cn(
          "inline-flex h-5 w-5 transform items-center justify-center rounded-full",
          "bg-white text-ink-700 shadow-sm transition-transform duration-200",
          isDark ? "translate-x-6" : "translate-x-0.5",
        )}
      >
        {isDark ? (
          <Moon className="h-3 w-3" />
        ) : (
          <Sun className="h-3 w-3 text-warning-500" />
        )}
      </span>
    </button>
  );
}
