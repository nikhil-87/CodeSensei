import { useParams } from "react-router-dom";

import { useAnalysisGate } from "@/components/analysis/AnalysisGate";
import { Card } from "@/components/common/Card";
import { ChatPanel } from "@/components/ai-chat/ChatPanel";

export function AIAssistantPage() {
  const { repositoryId } = useParams<{ repositoryId: string }>();
  const gate = useAnalysisGate(repositoryId);
  if (!repositoryId) return null;
  if (gate.blocker) return gate.blocker;

  return (
    <div className="mx-auto flex h-full max-w-6xl flex-col p-3 sm:p-6">
      <header className="mb-4">
        <h1 className="text-xl font-semibold text-ink-900">AI assistant</h1>
        <p className="text-sm text-ink-500">
          Ask anything about this repository. Conversations are saved privately to
          your account and answers are grounded in indexed code chunks.
        </p>
      </header>
      <Card
        padded={false}
        className="flex min-h-0 flex-1 flex-col p-2 sm:p-4"
        contentClassName="flex min-h-0 flex-1 flex-col"
      >
        <ChatPanel repositoryId={repositoryId} />
      </Card>
    </div>
  );
}
