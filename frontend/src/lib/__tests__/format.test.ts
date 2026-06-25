import { describe, expect, it } from "vitest";

import {
  formatBytes,
  formatNumber,
  parseLanguages,
  shortRepoName,
  truncate,
} from "../format";

describe("formatNumber", () => {
  it("formats with thousands separators", () => {
    expect(formatNumber(1234567)).toBe("1,234,567");
  });
  it("returns an em-dash for nullish or NaN", () => {
    expect(formatNumber(null)).toBe("—");
    expect(formatNumber(undefined)).toBe("—");
    expect(formatNumber(Number.NaN)).toBe("—");
  });
  it("handles zero", () => {
    expect(formatNumber(0)).toBe("0");
  });
});

describe("formatBytes", () => {
  it("returns bytes verbatim under 1 KiB", () => {
    expect(formatBytes(512)).toBe("512 B");
  });
  it("scales through KB/MB/GB", () => {
    expect(formatBytes(2048)).toBe("2.0 KB");
    expect(formatBytes(5 * 1024 * 1024)).toBe("5.0 MB");
    expect(formatBytes(3 * 1024 ** 3)).toBe("3.0 GB");
  });
  it("returns em-dash for nullish", () => {
    expect(formatBytes(undefined)).toBe("—");
  });
});

describe("parseLanguages", () => {
  it("parses the canonical packed format", () => {
    expect(parseLanguages("python:42,typescript:13")).toEqual([
      { language: "python", count: 42 },
      { language: "typescript", count: 13 },
    ]);
  });
  it("ignores trailing whitespace and empty pieces", () => {
    expect(parseLanguages("python:42, typescript:13, ")).toEqual([
      { language: "python", count: 42 },
      { language: "typescript", count: 13 },
    ]);
  });
  it("returns an empty array for nullish input", () => {
    expect(parseLanguages(null)).toEqual([]);
    expect(parseLanguages(undefined)).toEqual([]);
    expect(parseLanguages("")).toEqual([]);
  });
  it("treats non-numeric counts as zero", () => {
    expect(parseLanguages("rust:abc")).toEqual([{ language: "rust", count: 0 }]);
  });
  it("supports languages with colons in the name", () => {
    // lastIndexOf-based parsing splits on the final colon.
    expect(parseLanguages("c++:5")).toEqual([{ language: "c++", count: 5 }]);
  });
});

describe("shortRepoName", () => {
  it("extracts owner/name from a github URL", () => {
    expect(shortRepoName("https://github.com/torvalds/linux")).toBe("torvalds/linux");
  });
  it("strips a trailing .git", () => {
    expect(shortRepoName("https://github.com/owner/repo.git")).toBe("owner/repo");
  });
  it("returns the original string for unparseable URLs", () => {
    expect(shortRepoName("not-a-url")).toBe("not-a-url");
  });
});

describe("truncate", () => {
  it("returns the input unchanged when shorter than the limit", () => {
    expect(truncate("short", 20)).toBe("short");
  });
  it("appends an ellipsis when truncated", () => {
    expect(truncate("a".repeat(50), 10).endsWith("…")).toBe(true);
  });
  it("prefers a word-boundary cut when possible", () => {
    // 18-char limit on "the quick brown fox jumps" cuts mid-"fox";
    // implementation should fall back to the last space (index 15).
    const out = truncate("the quick brown fox jumps over", 18);
    expect(out).toBe("the quick brown…");
  });
});
