import React, { useMemo, useState } from "react";
import { Check, Copy } from "lucide-react";
import { cn } from "@/lib/format";
import type { ChatCitation } from "@/types/api";

export interface MarkdownTextProps {
  content: string;
  citations?: ChatCitation[];
  isStreaming?: boolean;
  className?: string;
}

// ---------------------------------------------------------------------------
// Regex & Normalization
// ---------------------------------------------------------------------------

/**
 * Matches inline citations emitted by various LLM architectures:
 * - Standard brackets: [path/to/file.ts:1-60] or [path/to/file.ts]
 * - CJK/Fullwidth brackets: 【doc/talks/README.md:1-60】 or 【doc/talks/README.md】
 * - Backtick wrapped: `[path:1-60]` or `【path:1-60】`
 * - OpenAI source markers: 【4:0†source】 or 【source】
 */
export const INLINE_CITATION_RE =
  /(?:`?[\[【]`?\s*([^\]】`]+?)(?::(\d+)(?:[-–—\u2011](\d+))?)?\s*`?[\]】]`?|【[^】]*†source】|【source】)/gu;

/** Normalize exotic Unicode hyphens and spaces to clean standard ASCII. */
export function normalizeSymbols(text: string): string {
  if (!text) return "";
  return text
    // Non-breaking hyphen \u2011, figure dash \u2012 -> standard hyphen -
    .replace(/[\u2010\u2011\u2012]/g, "-")
    // Narrow no-break space \u202F, no-break space \u00A0 -> regular space
    .replace(/[\u202F\u00A0]/g, " ");
}

/** Clean path string for fuzzy matching against citation file paths. */
export function normalizePath(p: string): string {
  return p
    .replace(/[\u2010-\u2015\u2212]/g, "-")
    .trim()
    .toLowerCase()
    .replace(/^\.\//, "")
    .replace(/^["'`]|["'`]$/g, "");
}

/** Remove citation tokens from text (useful for raw previews or clean copy). */
export function stripCitations(text: string): string {
  if (!text) return "";
  return normalizeSymbols(text)
    .replace(INLINE_CITATION_RE, "")
    // Remove any trailing unclosed citation bracket while streaming
    .replace(/[\[【][^\]】\n]*$/, "")
    .replace(/[ \t]{2,}/g, " ");
}

// ---------------------------------------------------------------------------
// Citation Mapping
// ---------------------------------------------------------------------------

export interface CitationMatch {
  n: number;
  citation: ChatCitation;
}

export function buildCitationNumbers(citations: ChatCitation[] = []) {
  const exact = new Map<string, CitationMatch>();
  const byPath = new Map<string, CitationMatch>();
  const byBaseName = new Map<string, CitationMatch>();

  citations.forEach((c, i) => {
    const norm = normalizePath(c.file_path);
    const item: CitationMatch = { n: i + 1, citation: c };
    exact.set(`${norm}:${c.line_start}-${c.line_end}`, item);
    if (!byPath.has(norm)) byPath.set(norm, item);
    const base = norm.split("/").pop();
    if (base && !byBaseName.has(base)) byBaseName.set(base, item);
  });

  return { exact, byPath, byBaseName };
}

export function CitationMarker({ n, label }: { n: number; label: string }) {
  return (
    <sup
      title={label}
      aria-label={`Source citation ${n}: ${label}`}
      className="mx-0.5 inline-flex h-4 min-w-4 cursor-help select-none items-center justify-center rounded bg-accent-100 border border-accent-200 px-1 align-super text-[9.5px] font-semibold leading-none text-accent-700 shadow-xs transition-colors hover:bg-accent-200"
    >
      {n}
    </sup>
  );
}

// ---------------------------------------------------------------------------
// Code Block Component (Theme & Dark-Mode Friendly)
// ---------------------------------------------------------------------------

function CodeBlock({ code, language }: { code: string; language?: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // ignore
    }
  };

  return (
    <div className="relative my-3 overflow-hidden rounded-lg border border-ink-200 bg-[#15171c] text-[#e3e5e8] shadow-sm">
      <div className="flex items-center justify-between border-b border-[#252830] bg-[#1a1d24] px-3 py-1.5 text-xs text-[#949ba4]">
        <span className="font-mono text-[10.5px] uppercase tracking-wider font-medium text-[#949ba4]">
          {language || "code"}
        </span>
        <button
          type="button"
          onClick={handleCopy}
          className="flex items-center gap-1 rounded px-2 py-0.5 text-[11px] text-[#949ba4] transition hover:bg-[#252830] hover:text-[#f2f3f5]"
          title="Copy code"
        >
          {copied ? (
            <Check className="h-3 w-3 text-emerald-400" />
          ) : (
            <Copy className="h-3 w-3" />
          )}
          <span>{copied ? "Copied" : "Copy"}</span>
        </button>
      </div>
      <pre className="overflow-x-auto p-3 font-mono text-xs leading-relaxed text-[#e3e5e8]">
        <code>{code}</code>
      </pre>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Table Component (Markdown Table in Chat)
// ---------------------------------------------------------------------------

function MarkdownTable({
  headers,
  rows,
  citationsLookup,
}: {
  headers: string[];
  rows: string[][];
  citationsLookup: ReturnType<typeof buildCitationNumbers>;
}) {
  return (
    <div className="my-3 overflow-x-auto rounded-lg border border-ink-200 shadow-sm">
      <table className="w-full border-collapse text-left text-xs">
        <thead className="border-b border-ink-200 bg-ink-100 text-ink-900 font-semibold">
          <tr>
            {headers.map((h, idx) => (
              <th key={`th-${idx}`} className="px-3 py-2 font-semibold">
                {parseInlineTokens(h.trim(), citationsLookup)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-ink-200/60 bg-surface">
          {rows.map((row, rIdx) => (
            <tr
              key={`tr-${rIdx}`}
              className="transition-colors hover:bg-ink-100/50"
            >
              {row.map((cell, cIdx) => (
                <td
                  key={`td-${rIdx}-${cIdx}`}
                  className="px-3 py-2 text-ink-800 align-top leading-relaxed"
                >
                  {parseInlineTokens(cell.trim(), citationsLookup)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Inline Tokenizer (Markdown + Citations + Line Breaks)
// ---------------------------------------------------------------------------

function parseInlineTokens(
  text: string,
  citationsLookup: ReturnType<typeof buildCitationNumbers>,
): React.ReactNode[] {
  const { exact, byPath, byBaseName } = citationsLookup;
  const nodes: React.ReactNode[] = [];
  let key = 0;

  // Split by line break tags `<br>` or `<br/>` first if present
  const brParts = text.split(/<br\s*\/?>/gi);
  if (brParts.length > 1) {
    brParts.forEach((part, idx) => {
      if (idx > 0) {
        nodes.push(<br key={`br-${key++}`} />);
      }
      nodes.push(...parseInlineTokens(part, citationsLookup));
    });
    return nodes;
  }

  const COMBINED_INLINE_RE =
    /(`[^`]+`)|((?:`?[\[【]`?\s*[^\]】`]+?(?::\d+(?:[-–—\u2011]\d+)?)?\s*`?[\]】]`?|【[^】]*†source】|【source】))|(\*\*[^*]+\*\*|__[^_]+__)|(?<!\*)\*([^*]+)\*(?!\*)|\[([^\]]+)\]\(([^)]+)\)/gu;

  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = COMBINED_INLINE_RE.exec(text)) !== null) {
    const matchIndex = match.index;
    if (matchIndex > lastIndex) {
      nodes.push(text.slice(lastIndex, matchIndex));
    }

    const full = match[0];
    const codeSpan = match[1];
    const citationSpan = match[2];
    const boldSpan = match[3];
    const italicSpan = match[4];
    const linkText = match[5];
    const linkUrl = match[6];

    if (codeSpan) {
      const codeContent = codeSpan.slice(1, -1);
      nodes.push(
        <code
          key={`code-${key++}`}
          className="rounded bg-ink-100 border border-ink-200 px-1.5 py-0.5 font-mono text-[12px] font-medium text-accent-700 shadow-xs"
        >
          {codeContent}
        </code>,
      );
    } else if (citationSpan) {
      const subMatch =
        /`?[\[【]`?\s*([^\]】`:]+?)(?::(\d+)(?:[-–—\u2011](\d+))?)?\s*`?[\]】]`?/u.exec(
          citationSpan,
        );
      if (subMatch && subMatch[1]) {
        const rawPath = subMatch[1];
        const start = subMatch[2];
        const end = subMatch[3];
        const normPath = normalizePath(rawPath);

        let cMatch = end ? exact.get(`${normPath}:${start}-${end}`) : undefined;
        if (!cMatch && start) {
          cMatch = exact.get(`${normPath}:${start}-${start}`);
        }
        if (!cMatch) {
          cMatch = byPath.get(normPath);
        }
        if (!cMatch) {
          for (const [p, item] of byPath.entries()) {
            if (p.endsWith(normPath) || normPath.endsWith(p)) {
              cMatch = item;
              break;
            }
          }
        }
        if (!cMatch) {
          const base = normPath.split("/").pop();
          if (base) cMatch = byBaseName.get(base);
        }

        if (cMatch) {
          const label = end
            ? `${cMatch.citation.file_path} L${start}–${end}`
            : start
              ? `${cMatch.citation.file_path} L${start}`
              : cMatch.citation.file_path;
          nodes.push(<CitationMarker key={`cite-${key++}`} n={cMatch.n} label={label} />);
        }
      }
    } else if (boldSpan) {
      const inner = boldSpan.slice(2, -2);
      nodes.push(
        <strong key={`b-${key++}`} className="font-semibold text-ink-950">
          {parseInlineTokens(inner, citationsLookup)}
        </strong>,
      );
    } else if (italicSpan) {
      nodes.push(
        <em key={`i-${key++}`} className="italic text-ink-800">
          {parseInlineTokens(italicSpan, citationsLookup)}
        </em>,
      );
    } else if (linkText && linkUrl) {
      nodes.push(
        <a
          key={`link-${key++}`}
          href={linkUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="font-medium text-accent-700 underline decoration-accent-300 transition hover:text-accent-800"
        >
          {linkText}
        </a>,
      );
    }

    lastIndex = matchIndex + full.length;
  }

  if (lastIndex < text.length) {
    nodes.push(text.slice(lastIndex));
  }

  return nodes;
}

// ---------------------------------------------------------------------------
// Block Parsing & Rendering (Light & Dark Friendly)
// ---------------------------------------------------------------------------

export function MarkdownText({
  content,
  citations = [],
  isStreaming = false,
  className,
}: MarkdownTextProps) {
  const citationsLookup = useMemo(() => buildCitationNumbers(citations), [citations]);

  // Clean raw symbols & Unicode anomalies
  const cleanContent = useMemo(() => {
    let text = normalizeSymbols(content || "");
    if (isStreaming) {
      // Incomplete trailing citation marker while streaming
      text = text.replace(/[\[【][^\]】\n]*$/, "");
    }
    return text.trim();
  }, [content, isStreaming]);

  // Split into blocks: code blocks, tables, headings, lists, blockquotes, paragraphs
  const renderedBlocks = useMemo(() => {
    if (!cleanContent) return null;

    const elements: React.ReactNode[] = [];
    const lines = cleanContent.split("\n");
    let i = 0;
    let blockKey = 0;

    while (i < lines.length) {
      const currentLine = lines[i];
      if (currentLine === undefined) {
        i++;
        continue;
      }

      const trimmedLine = currentLine.trim();

      // 1. Code block ```
      if (trimmedLine.startsWith("```")) {
        const lang = trimmedLine.slice(3).trim();
        const codeLines: string[] = [];
        i++;
        while (i < lines.length) {
          const codeLine = lines[i];
          if (codeLine !== undefined && codeLine.trim().startsWith("```")) {
            break;
          }
          if (codeLine !== undefined) {
            codeLines.push(codeLine);
          }
          i++;
        }
        i++; // skip closing ```
        elements.push(
          <CodeBlock
            key={`block-${blockKey++}`}
            code={codeLines.join("\n")}
            language={lang}
          />,
        );
        continue;
      }

      // 2. Empty line
      if (!trimmedLine) {
        i++;
        continue;
      }

      // 3. Markdown Table (| Col 1 | Col 2 |)
      if (
        trimmedLine.startsWith("|") &&
        trimmedLine.endsWith("|") &&
        i + 1 < lines.length &&
        lines[i + 1]?.trim().startsWith("|") &&
        lines[i + 1]?.includes("---")
      ) {
        const parseRow = (line: string): string[] => {
          const stripped = line.trim().replace(/^\|/, "").replace(/\|$/, "");
          return stripped.split("|");
        };

        const headers = parseRow(trimmedLine);
        i += 2; // skip header and divider row
        const rows: string[][] = [];

        while (
          i < lines.length &&
          lines[i]?.trim().startsWith("|") &&
          lines[i]?.trim().endsWith("|")
        ) {
          const rowLine = lines[i];
          if (rowLine) {
            rows.push(parseRow(rowLine));
          }
          i++;
        }

        elements.push(
          <MarkdownTable
            key={`table-${blockKey++}`}
            headers={headers}
            rows={rows}
            citationsLookup={citationsLookup}
          />,
        );
        continue;
      }

      // 4. Headings (#, ##, ###)
      const headingMatch = currentLine.match(/^(#{1,6})\s+(.+)$/);
      if (headingMatch && headingMatch[1] && headingMatch[2]) {
        const level = headingMatch[1].length;
        const text = headingMatch[2];
        const headingContent = parseInlineTokens(text, citationsLookup);
        if (level === 1) {
          elements.push(
            <h3
              key={`h-${blockKey++}`}
              className="mb-2 mt-3 text-base font-bold text-ink-950"
            >
              {headingContent}
            </h3>,
          );
        } else if (level === 2) {
          elements.push(
            <h4
              key={`h-${blockKey++}`}
              className="mb-1.5 mt-2.5 text-sm font-semibold text-ink-950"
            >
              {headingContent}
            </h4>,
          );
        } else {
          elements.push(
            <h5
              key={`h-${blockKey++}`}
              className="mb-1 mt-2 text-xs font-semibold uppercase tracking-wider text-ink-500"
            >
              {headingContent}
            </h5>,
          );
        }
        i++;
        continue;
      }

      // 5. Horizontal Rule
      if (/^(\*\*\*|---|___)$/.test(trimmedLine)) {
        elements.push(
          <hr
            key={`hr-${blockKey++}`}
            className="my-3 border-ink-200"
          />,
        );
        i++;
        continue;
      }

      // 6. Blockquote
      if (currentLine.startsWith(">")) {
        const quoteLines: string[] = [];
        while (i < lines.length) {
          const qLine = lines[i];
          if (qLine === undefined || !qLine.startsWith(">")) break;
          quoteLines.push(qLine.replace(/^>\s?/, ""));
          i++;
        }
        elements.push(
          <blockquote
            key={`quote-${blockKey++}`}
            className="my-2 border-l-2 border-accent-500 bg-ink-50/50 py-1 pl-3 italic text-ink-700 rounded-r"
          >
            {parseInlineTokens(quoteLines.join(" "), citationsLookup)}
          </blockquote>,
        );
        continue;
      }

      // 7. Unordered List (*, -, +)
      if (/^(\s*)[*+-]\s+/.test(currentLine)) {
        const listItems: React.ReactNode[] = [];
        while (i < lines.length) {
          const lLine = lines[i];
          if (lLine === undefined || !/^(\s*)[*+-]\s+/.test(lLine)) break;
          const itemText = lLine.replace(/^(\s*)[*+-]\s+/, "");
          listItems.push(
            <li
              key={`li-${listItems.length}`}
              className="flex items-start gap-2"
            >
              <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-accent-500" />
              <div className="flex-1 leading-relaxed text-ink-900">
                {parseInlineTokens(itemText, citationsLookup)}
              </div>
            </li>,
          );
          i++;
        }
        elements.push(
          <ul key={`ul-${blockKey++}`} className="my-2 space-y-1.5 pl-1">
            {listItems}
          </ul>,
        );
        continue;
      }

      // 8. Ordered List (1., 2.)
      if (/^\s*\d+\.\s+/.test(currentLine)) {
        const listItems: React.ReactNode[] = [];
        let num = 1;
        while (i < lines.length) {
          const oLine = lines[i];
          if (oLine === undefined || !/^\s*\d+\.\s+/.test(oLine)) break;
          const itemText = oLine.replace(/^\s*\d+\.\s+/, "");
          listItems.push(
            <li
              key={`ol-li-${listItems.length}`}
              className="flex items-start gap-2"
            >
              <span className="mt-0.5 inline-flex h-4 min-w-4 items-center justify-center rounded bg-ink-100 border border-ink-200 text-[10px] font-semibold text-ink-700">
                {num++}
              </span>
              <div className="flex-1 leading-relaxed text-ink-900">
                {parseInlineTokens(itemText, citationsLookup)}
              </div>
            </li>,
          );
          i++;
        }
        elements.push(
          <ol key={`ol-${blockKey++}`} className="my-2 space-y-1.5 pl-1">
            {listItems}
          </ol>,
        );
        continue;
      }

      // 9. Regular Paragraph
      const paraLines: string[] = [];
      while (i < lines.length) {
        const pLine = lines[i];
        if (pLine === undefined) break;
        const pTrimmed = pLine.trim();
        if (!pTrimmed) break;
        if (pTrimmed.startsWith("```")) break;
        if (pLine.match(/^#{1,6}\s+/)) break;
        if (/^(\s*)[*+-]\s+/.test(pLine)) break;
        if (/^\s*\d+\.\s+/.test(pLine)) break;
        if (pLine.startsWith(">")) break;
        if (/^(\*\*\*|---|___)$/.test(pTrimmed)) break;
        if (pTrimmed.startsWith("|") && pTrimmed.endsWith("|")) break;

        paraLines.push(pLine);
        i++;
      }

      if (paraLines.length > 0) {
        elements.push(
          <p
            key={`p-${blockKey++}`}
            className="mb-2.5 last:mb-0 leading-relaxed text-ink-900"
          >
            {parseInlineTokens(paraLines.join(" "), citationsLookup)}
          </p>,
        );
      }
    }

    return elements;
  }, [cleanContent, citationsLookup]);

  return (
    <div className={cn("prose-sm max-w-none text-ink-900", className)}>
      {renderedBlocks}
    </div>
  );
}
