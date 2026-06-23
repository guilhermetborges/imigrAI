import { Card } from "@/components/ui/card";

interface GapsListProps {
  gaps: string[];
}

export function GapsList({ gaps }: Readonly<GapsListProps>): JSX.Element {
  return (
    <Card>
      <h3 className="font-semibold">Gaps criticos</h3>
      {gaps.length ? (
        <ul className="mt-3 space-y-2 text-sm text-muted">
          {gaps.map((gap) => (
            <li key={gap}>- {gap}</li>
          ))}
        </ul>
      ) : (
        <p className="mt-3 text-sm text-muted">Nenhum gap critico detectado.</p>
      )}
    </Card>
  );
}
