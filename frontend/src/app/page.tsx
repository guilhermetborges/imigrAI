import Link from "next/link";

import { Card } from "@/components/ui/card";

const planComparison = [
  {
    name: "Free",
    points: ["3 assessments por mes", "Resultado com score e gaps", "Sem roadmap IA"],
    cta: "Comecar gratis",
    href: "/onboarding"
  },
  {
    name: "Pro",
    points: [
      "Assessments ilimitados",
      "Roadmap com passos priorizados",
      "Processamento prioritario"
    ],
    cta: "Ver plano Pro",
    href: "/pricing"
  }
];

export default function LandingPage(): JSX.Element {
  return (
    <section className="space-y-8">
      <Card className="reveal overflow-hidden bg-gradient-to-br from-brand-soft via-white to-accent-soft">
        <div className="grid gap-6 md:grid-cols-[1.2fr_1fr] md:items-center">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted">
              Planejamento de imigracao orientado por score
            </p>
            <h1 className="mt-3 font-serif text-4xl leading-tight sm:text-5xl">
              Entenda sua chance real de imigrar e os proximos passos com clareza.
            </h1>
            <p className="mt-4 max-w-xl text-muted">
              Preencha seu perfil, calcule score por programa e transforme gaps em acoes com
              roadmap pratico.
            </p>
            <Link
              className="mt-6 inline-flex h-12 items-center justify-center rounded-xl bg-brand px-6 text-sm font-semibold text-brand-contrast transition hover:bg-[#0f7d8f]"
              href="/onboarding"
            >
              Calcular Score Gratis
            </Link>
          </div>
          <div className="grid gap-3 rounded-2xl border border-brand/20 bg-white/90 p-5">
            <p className="text-sm font-semibold text-muted">Como funciona</p>
            <div className="rounded-xl bg-brand-soft px-4 py-3 text-sm">1. Informe perfil em 4 etapas</div>
            <div className="rounded-xl bg-accent-soft px-4 py-3 text-sm">
              2. Receba score (0-100) + breakdown
            </div>
            <div className="rounded-xl bg-brand-soft px-4 py-3 text-sm">
              3. Gere roadmap priorizado no Pro
            </div>
          </div>
        </div>
      </Card>

      <section className="grid gap-4 md:grid-cols-2">
        {planComparison.map((plan, index) => (
          <Card key={plan.name} className="reveal" style={{ animationDelay: `${index * 120}ms` }}>
            <h2 className="font-serif text-3xl">{plan.name}</h2>
            <ul className="mt-4 space-y-2 text-sm text-muted">
              {plan.points.map((point) => (
                <li key={point}>- {point}</li>
              ))}
            </ul>
            <Link
              href={plan.href}
              className="mt-6 inline-flex h-11 items-center justify-center rounded-xl border border-ink/15 px-4 text-sm font-semibold text-ink transition hover:bg-ink/5"
            >
              {plan.cta}
            </Link>
          </Card>
        ))}
      </section>
    </section>
  );
}
