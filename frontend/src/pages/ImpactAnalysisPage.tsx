import { useState } from "react";
import { useParams } from "react-router-dom";

import { ImpactApi } from "@/api/impact";
import { useAnalysisGate } from "@/components/analysis/AnalysisGate";
import { Button } from "@/components/common/Button";
import { Card } from "@/components/common/Card";
import { Skeleton } from "@/components/common/Skeleton";
import { formatNumber } from "@/lib/format";
import type { ImpactResponse } from "@/types/api";

export function ImpactAnalysisPage() {
  const { repositoryId } = useParams<{ repositoryId: string }>();
  const gate = useAnalysisGate(repositoryId);
  const [filePath, setFilePath] = useState("");
  const [maxDepth, setMaxDepth] = useState(5);
  const [result, setResult] = useState<ImpactResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!repositoryId || !filePath.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await ImpactApi.analyze(repositoryId, {
        file_path: filePath.trim(),
        max_depth: maxDepth,
      });
      setResult(res);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  if (gate.blocker) return gate.blocker;

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-4 sm:p-6">
      <header>
        <h1 className="text-xl font-semibold text-ink-900">Impact analysis</h1>
        <p className="text-sm text-ink-500">
          Estimate the blast-radius of changing a file — which other files transitively depend on it.
        </p>
      </header>

      <Card padded>
        <form className="grid gap-4 sm:grid-cols-[1fr_auto_auto]" onSubmit={run}>
          <label className="flex flex-col gap-1.5">
            <span className="text-xs font-medium text-ink-700">File path</span>
            <input
              value={filePath}
              onChange={(e) => setFilePath(e.target.value)}
              placeholder="src/services/payment.py"
              className="focus-ring h-10 rounded-md border border-ink-200 bg-surface px-3 text-sm text-ink-900"
            />
          </label>
          <label className="flex flex-col gap-1.5">
            <span className="text-xs font-medium text-ink-700">Max depth</span>
            <input
              type="number"
              min={1}
              max={20}
              value={maxDepth}
              onChange={(e) => setMaxDepth(Number(e.target.value))}
              className="focus-ring h-10 w-24 rounded-md border border-ink-200 bg-surface px-3 text-sm text-ink-900"
            />
          </label>
          <div className="flex items-end">
            <Button type="submit" loading={loading}>Analyze</Button>
          </div>
        </form>
        {error && (
          <p className="mt-3 rounded-md bg-danger-100 px-3 py-2 text-sm text-danger-500">{error}</p>
        )}
      </Card>

      {loading && (
        <Card>
          <div className="space-y-3">
            <Skeleton className="h-4 w-48" />
            <Skeleton className="h-2 w-32 rounded-full" />
            <div className="space-y-2 pt-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-9" />
              ))}
            </div>
          </div>
        </Card>
      )}

      {result && (
        <Card
          title={`Impacted ${result.impacted_files.length} files`}
          description={result.summary}
        >
          <div className="mb-4 flex items-center gap-3">
            <span className="text-xs font-medium text-ink-500">Risk score</span>
            <div className="h-2 w-32 overflow-hidden rounded-full bg-ink-100">
              <div
                className="h-2 rounded-full bg-danger-500"
                style={{ width: `${Math.round(result.risk_score * 100)}%` }}
              />
            </div>
            <span className="text-sm font-semibold text-ink-900">
              {(result.risk_score * 100).toFixed(0)}%
            </span>
          </div>

          <div className="overflow-x-auto rounded-md border border-ink-200">
            <table className="min-w-full divide-y divide-ink-200 text-sm">
              <thead className="bg-ink-50">
                <tr>
                  <Th>File</Th>
                  <Th>Distance</Th>
                  <Th>Risk</Th>
                </tr>
              </thead>
              <tbody className="divide-y divide-ink-100 bg-surface">
                {result.impacted_files.map((f) => (
                  <tr key={f.file_id}>
                    <Td className="font-mono text-xs">{f.path}</Td>
                    <Td>{f.distance}</Td>
                    <Td>
                      <span className="font-semibold tabular-nums text-ink-900">
                        {(f.risk_score * 100).toFixed(0)}%
                      </span>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-3 text-xs text-ink-400">
            {formatNumber(result.impacted_files.length)} files within depth {maxDepth}.
          </p>
        </Card>
      )}
    </div>
  );
}

function Th({ children }: { children: React.ReactNode }) {
  return <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-ink-500">{children}</th>;
}
function Td({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <td className={`px-3 py-2 ${className}`}>{children}</td>;
}
