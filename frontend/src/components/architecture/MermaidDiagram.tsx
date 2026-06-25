/**
 * Lazy-loaded Mermaid diagram renderer.
 *
 * Mermaid is ~500KB gzip — we import it dynamically only when this
 * component first renders, keeping it out of the initial vendor chunk.
 */
import { useEffect, useRef, useState } from "react";

import { useThemeStore } from "@/store/themeStore";

interface MermaidDiagramProps {
  source: string;
  className?: string;
}

let idCounter = 0;

export function MermaidDiagram({ source, className }: MermaidDiagramProps) {
  const [svg, setSvg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const id = useRef(`mermaid-${++idCounter}`);
  const theme = useThemeStore((s) => s.theme);

  useEffect(() => {
    let cancelled = false;
    setError(null);

    (async () => {
      try {
        const mermaid = (await import("mermaid")).default;
        mermaid.initialize({
          startOnLoad: false,
          securityLevel: "strict",
          theme: theme === "dark" ? "dark" : "neutral",
          fontFamily: "Inter, system-ui, sans-serif",
        });
        const { svg } = await mermaid.render(id.current, source);
        if (!cancelled) setSvg(svg);
      } catch (e) {
        if (!cancelled) setError((e as Error).message ?? "Failed to render diagram");
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [source, theme]);

  if (error) {
    return (
      <pre className="overflow-auto rounded-md bg-ink-50 p-4 text-xs text-ink-700">
        <code>{source}</code>
        <p className="mt-2 text-danger-500">Render error: {error}</p>
      </pre>
    );
  }
  if (!svg) {
    return (
      <div className="flex h-40 items-center justify-center text-sm text-ink-400">
        Rendering diagram…
      </div>
    );
  }
  // Mermaid produces an SVG string; we trust it (securityLevel=strict).
  return (
    <div
      className={className}
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}
