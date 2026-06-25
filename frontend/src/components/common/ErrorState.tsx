import { AlertTriangle } from "lucide-react";

import { Button } from "./Button";

export interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
}

export function ErrorState({
  title = "Something went wrong",
  message,
  onRetry,
}: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-danger-100 bg-red-50 p-8 text-center">
      <AlertTriangle className="h-8 w-8 text-danger-500" />
      <h3 className="text-base font-semibold text-ink-900">{title}</h3>
      {message && <p className="max-w-md text-sm text-ink-600">{message}</p>}
      {onRetry && (
        <Button variant="secondary" size="sm" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}
