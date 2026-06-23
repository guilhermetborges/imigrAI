import { Skeleton } from "@/components/ui/skeleton";

export function CardSkeleton(): JSX.Element {
  return (
    <div className="rounded-2xl border border-ink/10 bg-white p-6 shadow-card">
      <Skeleton className="h-4 w-28" />
      <Skeleton className="mt-3 h-10 w-2/3" />
      <Skeleton className="mt-4 h-4 w-full" />
      <Skeleton className="mt-2 h-4 w-4/5" />
    </div>
  );
}

interface ListSkeletonProps {
  rows?: number;
}

export function ListSkeleton({ rows = 4 }: Readonly<ListSkeletonProps>): JSX.Element {
  return (
    <div className="space-y-3">
      {Array.from({ length: rows }).map((_, index) => (
        <div key={index} className="rounded-xl border border-ink/10 bg-white p-4">
          <Skeleton className="h-4 w-1/3" />
          <Skeleton className="mt-3 h-3 w-full" />
          <Skeleton className="mt-2 h-3 w-5/6" />
        </div>
      ))}
    </div>
  );
}
