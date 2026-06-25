import type { DeadCodeItem } from "@/types/api";

interface DeadCodeTableProps {
  items: DeadCodeItem[];
}

export function DeadCodeTable({ items }: DeadCodeTableProps) {
  if (items.length === 0) {
    return <p className="text-sm text-ink-400">No dead code detected.</p>;
  }
  return (
    <div className="overflow-x-auto rounded-md border border-ink-200">
      <table className="min-w-full divide-y divide-ink-200 text-sm">
        <thead className="bg-ink-50">
          <tr>
            <Th>File</Th>
            <Th>Symbol</Th>
            <Th>Kind</Th>
            <Th>Line</Th>
            <Th>Confidence</Th>
            <Th>Reason</Th>
          </tr>
        </thead>
        <tbody className="divide-y divide-ink-100 bg-surface">
          {items.map((it) => (
            <tr key={`${it.file_id}-${it.symbol_name}-${it.line_start}`}>
              <Td className="font-mono text-xs text-ink-700">{it.path}</Td>
              <Td className="font-medium text-ink-900">{it.symbol_name}</Td>
              <Td>
                <span className="rounded bg-ink-100 px-1.5 py-0.5 text-xs text-ink-700">
                  {it.kind}
                </span>
              </Td>
              <Td className="text-ink-500">{it.line_start}</Td>
              <Td>
                <ConfidenceBar value={it.confidence} />
              </Td>
              <Td className="text-ink-500">{it.reason}</Td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Th({ children }: { children: React.ReactNode }) {
  return (
    <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-ink-500">
      {children}
    </th>
  );
}

function Td({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <td className={`px-3 py-2 align-middle ${className}`}>{children}</td>;
}

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-20 rounded-full bg-ink-100">
        <div
          className="h-1.5 rounded-full bg-warning-500"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs tabular-nums text-ink-600">{pct}%</span>
    </div>
  );
}
