interface ProgressProps {
  value: number;
}

export function Progress({ value }: Readonly<ProgressProps>): JSX.Element {
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-ink/10">
      <div
        className="h-full rounded-full bg-brand transition-all"
        style={{ width: `${Math.max(0, Math.min(value, 100))}%` }}
      />
    </div>
  );
}
