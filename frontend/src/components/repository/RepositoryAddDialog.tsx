import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { AnalysisApi } from "@/api/analysis";
import { Button } from "@/components/common/Button";
import { useCreateRepository } from "@/hooks/useRepositories";
import { ApiError } from "@/lib/api";

interface RepositoryAddDialogProps {
  open: boolean;
  onClose: () => void;
}

/**
 * Lightweight client-side check mirroring the backend's accepted form
 * (`https://github.com/<owner>/<repo>`). Gives instant feedback so a typo
 * doesn't require a server round-trip to discover.
 */
function describeUrlProblem(raw: string): string | null {
  const value = raw.trim();
  if (!value) return null; // don't nag before they've typed
  let parsed: URL;
  try {
    parsed = new URL(value);
  } catch {
    return "Enter a full URL, e.g. https://github.com/owner/name";
  }
  if (parsed.protocol !== "https:") return "The URL must start with https://";
  const host = parsed.hostname.replace(/^www\./, "");
  if (host !== "github.com") return "Only github.com repositories are supported";
  const segments = parsed.pathname.split("/").filter(Boolean);
  if (segments.length < 2) return "Include both the owner and repository name";
  return null;
}

export function RepositoryAddDialog({ open, onClose }: RepositoryAddDialogProps) {
  const [url, setUrl] = useState("");
  const [branch, setBranch] = useState("");
  // When the user re-submits a repo they already analyzed, we don't create a
  // duplicate — we surface a choice (open existing vs. refresh).
  const [duplicateId, setDuplicateId] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const navigate = useNavigate();
  const create = useCreateRepository();

  if (!open) return null;

  const urlProblem = describeUrlProblem(url);
  const canSubmit = url.trim().length > 0 && !urlProblem && !create.isPending;

  const reset = () => {
    setUrl("");
    setBranch("");
    setDuplicateId(null);
    setRefreshing(false);
  };

  const close = () => {
    reset();
    onClose();
  };

  const goTo = (repositoryId: string) => {
    reset();
    onClose();
    navigate(`/repos/${repositoryId}/overview`);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim() || urlProblem) return;
    try {
      const job = await create.mutateAsync({
        url: url.trim(),
        branch: branch.trim() || null,
      });
      goTo(job.repository_id);
    } catch (err) {
      if (err instanceof ApiError && typeof err.details?.repository_id === "string") {
        const repoId = err.details.repository_id as string;
        // Already analyzed by this user → offer open vs. refresh.
        if (err.code === "repository_already_exists") {
          setDuplicateId(repoId);
          return;
        }
        // Already being analyzed → take them straight to the live progress.
        if (err.code === "analysis_already_running") {
          goTo(repoId);
          return;
        }
      }
      // Other errors surface via mutation.error below.
    }
  };

  const handleRefresh = async () => {
    if (!duplicateId) return;
    setRefreshing(true);
    try {
      await AnalysisApi.trigger(duplicateId);
      goTo(duplicateId);
    } catch {
      // If a refresh can't start (e.g. it just started elsewhere), still open
      // the existing analysis rather than dead-ending the user.
      goTo(duplicateId);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal
      aria-labelledby="add-repo-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink-900/40 p-4"
      onClick={(e) => e.target === e.currentTarget && close()}
    >
      <div className="w-full max-w-md rounded-lg bg-surface p-6 shadow-elev">
        {duplicateId ? (
          <>
            <h2 id="add-repo-title" className="text-lg font-semibold text-ink-900">
              You&apos;ve already analyzed this repository
            </h2>
            <p className="mt-2 text-sm text-ink-500">
              You have already analyzed this repository. If you want the latest
              insights based on the current repository state, you can refresh /
              re-analyze it.
            </p>
            <div className="mt-6 flex flex-col gap-2">
              <Button
                variant="primary"
                loading={refreshing}
                onClick={() => void handleRefresh()}
              >
                Refresh analysis
              </Button>
              <Button
                variant="secondary"
                disabled={refreshing}
                onClick={() => goTo(duplicateId)}
              >
                Open existing analysis
              </Button>
              <Button variant="ghost" disabled={refreshing} onClick={close}>
                Cancel
              </Button>
            </div>
          </>
        ) : (
          <>
            <h2 id="add-repo-title" className="text-lg font-semibold text-ink-900">
              Analyze a GitHub repository
            </h2>
            <p className="mt-1 text-sm text-ink-500">
              We&apos;ll clone and analyze the repository in the background.
            </p>

            <form className="mt-5 flex flex-col gap-4" onSubmit={handleSubmit}>
              <Field
                id="repo-url"
                label="Repository URL"
                placeholder="https://github.com/owner/name"
                value={url}
                onChange={setUrl}
                required
                autoFocus
                error={urlProblem}
              />
              <Field
                id="repo-branch"
                label="Branch (optional)"
                placeholder="main"
                value={branch}
                onChange={setBranch}
              />

              {create.isError && (
                <p className="rounded-md bg-danger-100 px-3 py-2 text-sm text-danger-500">
                  {(create.error as Error).message}
                </p>
              )}

              <div className="mt-2 flex justify-end gap-2">
                <Button type="button" variant="ghost" onClick={close}>
                  Cancel
                </Button>
                <Button type="submit" loading={create.isPending} disabled={!canSubmit}>
                  Start analysis
                </Button>
              </div>
            </form>
          </>
        )}
      </div>
    </div>
  );
}

function Field(props: {
  id: string;
  label: string;
  placeholder?: string;
  value: string;
  onChange: (v: string) => void;
  required?: boolean;
  autoFocus?: boolean;
  error?: string | null;
}) {
  return (
    <label htmlFor={props.id} className="flex flex-col gap-1.5">
      <span className="text-xs font-medium text-ink-700">{props.label}</span>
      <input
        id={props.id}
        type="text"
        value={props.value}
        placeholder={props.placeholder}
        required={props.required}
        autoFocus={props.autoFocus}
        aria-invalid={props.error ? true : undefined}
        onChange={(e) => props.onChange(e.target.value)}
        className={
          "focus-ring h-10 rounded-md border bg-surface px-3 text-sm text-ink-900 placeholder:text-ink-400 " +
          (props.error ? "border-danger-300" : "border-ink-200")
        }
      />
      {props.error && (
        <span className="text-xs text-danger-500">{props.error}</span>
      )}
    </label>
  );
}
