import { Link } from "react-router-dom";

import { Button } from "@/components/common/Button";

export function NotFoundPage() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-4 p-12 text-center">
      <p className="text-6xl font-bold text-ink-300">404</p>
      <h1 className="text-xl font-semibold text-ink-900">Page not found</h1>
      <p className="max-w-sm text-sm text-ink-500">
        The page you&apos;re looking for doesn&apos;t exist or the repository ID is invalid.
      </p>
      <Link to="/">
        <Button>Back to repositories</Button>
      </Link>
    </div>
  );
}
