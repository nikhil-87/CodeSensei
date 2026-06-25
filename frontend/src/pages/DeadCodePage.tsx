import { useParams } from "react-router-dom";

import { useAnalysisGate } from "@/components/analysis/AnalysisGate";
import { Card } from "@/components/common/Card";
import { ErrorState } from "@/components/common/ErrorState";
import { PageHeaderSkeleton, TableSkeleton } from "@/components/common/Skeleton";
import { DeadCodeTable } from "@/components/dead-code/DeadCodeTable";
import { useDeadCode } from "@/hooks/useInsights";

export function DeadCodePage() {
  const { repositoryId } = useParams<{ repositoryId: string }>();
  const gate = useAnalysisGate(repositoryId);
  const { data, isLoading, isError, error, refetch } = useDeadCode(
    repositoryId,
    gate.ready,
  );

  if (gate.blocker) return gate.blocker;
  if (isLoading && !data) {
    return (
      <div className="mx-auto max-w-7xl space-y-6 p-4 sm:p-6">
        <PageHeaderSkeleton />
        <TableSkeleton rows={10} cols={6} />
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
        <h1 className="text-xl font-semibold text-ink-900">Dead code</h1>
        <p className="text-sm text-ink-500">
          {data.items.length} unused symbols detected.
        </p>
      </header>
      {Object.keys(data.summary).length > 0 && (
        <div className="flex flex-wrap gap-2">
          {Object.entries(data.summary).map(([kind, count]) => (
            <span
              key={kind}
              className="rounded-full bg-warning-100 px-3 py-1 text-xs font-medium text-warning-500"
            >
              {kind}: {count}
            </span>
          ))}
        </div>
      )}
      <Card title="Findings" padded>
        <DeadCodeTable items={data.items} />
      </Card>
    </div>
  );
}
