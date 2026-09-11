import { describe, expect, it } from "vitest";
import {
  normalizePath,
  normalizeSymbols,
  stripCitations,
  buildCitationNumbers,
  INLINE_CITATION_RE,
} from "./MarkdownText";
import type { ChatCitation } from "@/types/api";

describe("MarkdownText Citation & Symbol Normalization", () => {
  it("normalizes non-breaking hyphens and narrow no-break spaces", () => {
    const raw = "console\u2011oriented weather\u2011forecast 100\u202fM+ queries";
    expect(normalizeSymbols(raw)).toBe("console-oriented weather-forecast 100 M+ queries");
  });

  it("normalizes paths with Unicode dashes", () => {
    expect(normalizePath("doc/talks/2026\u2011curlup/README.md")).toBe(
      "doc/talks/2026-curlup/readme.md",
    );
  });

  it("matches fullwidth brackets 【...】 and standard brackets [...]", () => {
    const text =
      "Overview【doc/talks/2026‑curlup/README.md:1-60】 and Integrations[doc/integrations.md:1-60]";
    const matches = Array.from(text.matchAll(INLINE_CITATION_RE));
    expect(matches).toHaveLength(2);
    expect(matches[0]?.[1]).toContain("doc/talks/2026");
    expect(matches[1]?.[1]).toBe("doc/integrations.md");
  });

  it("strips all citations cleanly from text", () => {
    const sample =
      "The service is console-friendly【doc/talks/2026‑curlup/README.md:1-60】 and fast[doc/integrations.md:1-60].";
    const stripped = stripCitations(sample);
    expect(stripped).toBe("The service is console-friendly and fast.");
    expect(stripped).not.toContain("【");
    expect(stripped).not.toContain("】");
    expect(stripped).not.toContain("[");
    expect(stripped).not.toContain("]");
  });

  it("maps CJK brackets with non-breaking hyphens to citation numbers", () => {
    const citations: ChatCitation[] = [
      {
        file_path: "doc/talks/2026-curlup/README.md",
        line_start: 1,
        line_end: 60,
        symbol: null,
        snippet: "",
      },
      {
        file_path: "doc/integrations.md",
        line_start: 1,
        line_end: 60,
        symbol: null,
        snippet: "",
      },
    ];

    const lookup = buildCitationNumbers(citations);
    const item = lookup.exact.get("doc/talks/2026-curlup/readme.md:1-60");
    expect(item).toBeDefined();
    expect(item?.n).toBe(1);

    const item2 = lookup.exact.get("doc/integrations.md:1-60");
    expect(item2).toBeDefined();
    expect(item2?.n).toBe(2);
  });
});
