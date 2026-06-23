import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

interface CardProps extends HTMLAttributes<HTMLElement> {
  children: React.ReactNode;
}

export function Card({ children, className, ...props }: Readonly<CardProps>): JSX.Element {
  return (
    <article
      className={cn(
        "rounded-2xl border border-ink/10 bg-surface p-6 shadow-card sm:p-8",
        className
      )}
      {...props}
    >
      {children}
    </article>
  );
}
