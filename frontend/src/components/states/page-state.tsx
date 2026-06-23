import { Button } from "@/components/ui/button";

interface PageStateProps {
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
}

export function PageState({
  title,
  description,
  actionLabel,
  onAction
}: Readonly<PageStateProps>): JSX.Element {
  return (
    <section className="mx-auto flex max-w-2xl flex-col items-center rounded-2xl border border-dashed border-ink/20 bg-white/70 p-8 text-center">
      <h2 className="text-2xl font-semibold">{title}</h2>
      <p className="mt-2 text-sm text-muted">{description}</p>
      {actionLabel && onAction ? (
        <Button className="mt-6" onClick={onAction}>
          {actionLabel}
        </Button>
      ) : null}
    </section>
  );
}
