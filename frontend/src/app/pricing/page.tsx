"use client";

import { useMutation } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useAuth } from "@/hooks/use-auth";
import { billingApi } from "@/lib/api/endpoints";
import { getApiErrorMessage } from "@/lib/api/client";

const plans = [
  {
    name: "Free",
    price: "R$ 0",
    features: ["3 assessments/mes", "Score + breakdown", "Sem roadmap IA"]
  },
  {
    name: "Pro",
    price: "R$ 149/mes",
    features: [
      "Assessments ilimitados",
      "Roadmaps completos com checklist",
      "Processamento prioritario"
    ]
  }
];

export default function PricingPage(): JSX.Element {
  const { status } = useAuth();
  const router = useRouter();

  const checkoutMutation = useMutation({
    mutationFn: async () => {
      if (typeof window === "undefined") {
        return;
      }

      const session = await billingApi.createCheckoutSession({
        plan_code: "pro",
        success_url: `${window.location.origin}/settings/subscription?success=1`,
        cancel_url: `${window.location.origin}/pricing?canceled=1`
      });

      window.location.href = session.checkout_url;
    }
  });

  const handleUpgrade = (): void => {
    if (status !== "authenticated") {
      router.push("/login?next=/pricing");
      return;
    }

    checkoutMutation.mutate();
  };

  return (
    <section className="space-y-6 reveal">
      <div className="max-w-3xl">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted">Planos</p>
        <h1 className="mt-2 font-serif text-5xl leading-tight">Escale do score para execucao.</h1>
        <p className="mt-3 text-muted">
          Free para validar potencial. Pro para transformar gaps em roteiro com prioridade e prazo.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {plans.map((plan) => (
          <Card key={plan.name} className={plan.name === "Pro" ? "border-brand" : undefined}>
            <h2 className="font-serif text-3xl">{plan.name}</h2>
            <p className="mt-1 text-2xl font-semibold">{plan.price}</p>
            <ul className="mt-5 space-y-2 text-sm text-muted">
              {plan.features.map((feature) => (
                <li key={feature}>- {feature}</li>
              ))}
            </ul>
            {plan.name === "Pro" ? (
              <Button
                className="mt-6"
                fullWidth
                onClick={handleUpgrade}
                disabled={checkoutMutation.isPending}
              >
                {checkoutMutation.isPending ? "Redirecionando..." : "Assinar Pro"}
              </Button>
            ) : (
              <Link href="/onboarding" className="mt-6 block">
                <Button className="w-full" variant="ghost">
                  Usar Free
                </Button>
              </Link>
            )}
          </Card>
        ))}
      </div>

      {checkoutMutation.isError ? (
        <p className="text-sm text-danger">{getApiErrorMessage(checkoutMutation.error)}</p>
      ) : null}
    </section>
  );
}
