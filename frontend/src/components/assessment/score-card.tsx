import { Card } from "@/components/ui/card";
import { formatDate } from "@/lib/formatters";

interface ScoreCardProps {
  score: number;
  faixa: string;
  completedAt: string | null;
}

export function ScoreCard({ score, faixa, completedAt }: Readonly<ScoreCardProps>): JSX.Element {
  const cappedScore = Math.max(0, Math.min(100, score));

  return (
    <Card className="bg-gradient-to-r from-brand-soft via-white to-accent-soft">
      <p className="text-xs uppercase tracking-[0.18em] text-muted">Resultado do score</p>
      <h1 className="mt-2 font-serif text-5xl">{cappedScore.toFixed(1)}</h1>
      <p className="mt-2 text-sm text-muted">Faixa: {faixa}</p>
      <p className="mt-1 text-xs text-muted">Ultima atualizacao: {formatDate(completedAt)}</p>
    </Card>
  );
}
