/**
 * Pure formatting helpers — covered by unit tests.
 */
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** Tailwind-aware class merger — used by every component. */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

/** "1,234,567" — never throws, returns "—" for nullish. */
export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return new Intl.NumberFormat("en-US").format(value);
}

/** "1.2 KB", "5.3 MB" — short SI-style. */
export function formatBytes(bytes: number | null | undefined): string {
  if (bytes === null || bytes === undefined) return "—";
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB", "TB"];
  let v = bytes / 1024;
  let i = 0;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i++;
  }
  return `${v.toFixed(1)} ${units[i]}`;
}

/** Relative-time formatter ("2h ago", "yesterday"). */
export function formatRelativeTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const ts = new Date(iso).getTime();
  if (Number.isNaN(ts)) return "—";
  const diffSec = Math.round((ts - Date.now()) / 1000);
  const formatter = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
  const units: Array<[number, Intl.RelativeTimeFormatUnit]> = [
    [1, "second"],
    [60, "minute"],
    [60 * 60, "hour"],
    [60 * 60 * 24, "day"],
    [60 * 60 * 24 * 7, "week"],
    [60 * 60 * 24 * 30, "month"],
    [60 * 60 * 24 * 365, "year"],
  ];
  // Pick the largest unit that still produces a magnitude >= 1.
  let chosen: [number, Intl.RelativeTimeFormatUnit] = [1, "second"];
  for (const u of units) {
    if (Math.abs(diffSec) >= u[0]) chosen = u;
  }
  return formatter.format(Math.round(diffSec / chosen[0]), chosen[1]);
}

/** Parse the backend's "python:42,typescript:13" language string. */
export function parseLanguages(packed: string | null | undefined): Array<{
  language: string;
  count: number;
}> {
  if (!packed) return [];
  return packed
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean)
    .map((piece) => {
      const colon = piece.lastIndexOf(":");
      if (colon === -1) return { language: piece, count: 0 };
      const lang = piece.slice(0, colon);
      const count = Number.parseInt(piece.slice(colon + 1), 10);
      return { language: lang, count: Number.isNaN(count) ? 0 : count };
    });
}

/** "owner/name" from a github URL, or the URL itself if it can't be parsed. */
export function shortRepoName(url: string): string {
  try {
    const u = new URL(url);
    const parts = u.pathname.replace(/^\//, "").replace(/\.git$/, "").split("/");
    if (parts.length >= 2) return `${parts[0]}/${parts[1]}`;
    return url;
  } catch {
    return url;
  }
}

/** Truncate to N chars with ellipsis. Won't break in the middle of a word if possible. */
export function truncate(text: string, n: number): string {
  if (text.length <= n) return text;
  const cut = text.slice(0, n);
  const lastSpace = cut.lastIndexOf(" ");
  return (lastSpace > n * 0.6 ? cut.slice(0, lastSpace) : cut) + "…";
}
