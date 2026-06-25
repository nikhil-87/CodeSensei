import { useParams } from "react-router-dom";

import { useAnalysisGate } from "@/components/analysis/AnalysisGate";
import { Card } from "@/components/common/Card";
import { ErrorState } from "@/components/common/ErrorState";
import {
  ChartSkeleton,
  PageHeaderSkeleton,
  TableSkeleton,
} from "@/components/common/Skeleton";
import { ComplexityChart } from "@/components/metrics/ComplexityChart";
import { useComplexity } from "@/hooks/useInsights";

export function ComplexityPage() {
  const { repositoryId } = useParams<{ repositoryId: string }>();
  const gate = useAnalysisGate(repositoryId);
  const { data, isLoading, isError, error, refetch } = useComplexity(
    repositoryId,
    15,
    gate.ready,
  );

  if (gate.blocker) return gate.blocker;
  if (isLoading && !data) {
    return (
      <div className="mx-auto max-w-7xl space-y-6 p-4 sm:p-6">
        <PageHeaderSkeleton />
        <ChartSkeleton />
        <TableSkeleton rows={10} cols={7} />
      </div>
    );
  }
  if (isError && !data)
    return (
      <div className="p-4 sm:p-6">
        <ErrorState message={(error as Error).message} onRetry={() => void refetch()} />
      </div>
    );
  if (!data) return null;

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-4 sm:p-6">
      <header>
        <h1 className="text-xl font-semibold text-ink-900">Complexity</h1>
        <p className="text-sm text-ink-500">
          Top files ranked by cyclomatic complexity. Average cyclomatic{" "}
          <strong>{data.average_cyclomatic.toFixed(1)}</strong>, average cognitive{" "}
          <strong>{data.average_cognitive.toFixed(1)}</strong>.
        </p>
      </header>

      <Card title="Top complex files">
        <ComplexityChart files={data.top_files} />
      </Card>

      <Card title="Detail">
        <div className="overflow-x-auto rounded-md border border-ink-200">
          <table className="min-w-full divide-y divide-ink-200 text-sm">
            <thead className="bg-ink-50">
              <tr>
                <Th>File</Th>
                <Th>Lang</Th>
                <Th>LOC</Th>
                <Th>Cyclomatic</Th>
                <Th>Cognitive</Th>
                <Th>Functions</Th>
                <Th>Classes</Th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ink-100 bg-surface">
              {data.top_files.map((f) => (
                <tr key={f.file_id}>
                  <Td className="font-mono text-xs">{f.path}</Td>
                  <Td>{f.language}</Td>
                  <Td>{f.lines_of_code}</Td>
                  <Td className="font-medium text-ink-900">{f.cyclomatic}</Td>
                  <Td>{f.cognitive}</Td>
                  <Td>{f.function_count}</Td>
                  <Td>{f.class_count}</Td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

function Th({ children }: { children: React.ReactNode }) {
  return <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-ink-500">{children}</th>;
}
function Td({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <td className={`px-3 py-2 ${className}`}>{children}</td>;
}
