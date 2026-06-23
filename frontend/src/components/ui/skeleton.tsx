import { cn } from "@/lib/utils";

interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className }: Readonly<SkeletonProps>): JSX.Element {
  return <div className={cn("animate-pulse rounded-lg bg-ink/10", className)} />;
}
