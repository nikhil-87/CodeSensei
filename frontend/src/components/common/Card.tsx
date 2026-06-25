import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/format";

export interface CardProps extends Omit<HTMLAttributes<HTMLDivElement>, "title"> {
  title?: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
  padded?: boolean;
  contentClassName?: string;
}

export function Card({
  title,
  description,
  action,
  padded = true,
  className,
  contentClassName,
  children,
  ...rest
}: CardProps) {
  return (
    <section className={cn("surface", className)} {...rest}>
      {(title || action) && (
        <header className="flex items-start justify-between gap-4 border-b border-ink-100 px-5 py-4">
          <div className="min-w-0">
            {title && <h2 className="text-base font-semibold text-ink-900">{title}</h2>}
            {description && (
              <p className="mt-1 text-sm text-ink-500">{description}</p>
            )}
          </div>
          {action && <div className="shrink-0">{action}</div>}
        </header>
      )}
      <div className={cn(padded && "p-5", contentClassName)}>{children}</div>
    </section>
  );
}
