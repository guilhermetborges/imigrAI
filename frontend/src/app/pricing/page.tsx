"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { CardSkeleton } from "@/components/states/loading-skeletons";
import { PageState } from "@/components/states/page-state";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useAuth } from "@/hooks/use-auth";
import { useSubscription } from "@/hooks/use-subscription";
import { getApiErrorMessage } from "@/lib/api/client";
import { formatCurrencyBRL } from "@/lib/formatters";

export default function PricingPage(): JSX.Element {
  const { status } = useAuth();
  const router = useRouter();
  const { plansQuery, checkoutMutation } = useSubscription({ includePlans: true });

  const handleUpgrade = (): void => {
    if (status !== "authenticated") {
      router.push("/login?next=/pricing");
      return;
    }

    if (globalThis.window === undefined) {
      return;
    }

    const origin = globalThis.window.location.origin;

    checkoutMutation.mutate(
      {
        planCode: "pro",
        successUrl: `${origin}/settings/subscription?success=1`,
        cancelUrl: `${origin}/pricing?canceled=1`
      },
      {
        onSuccess: (session) => {
          globalThis.window.location.href = session.checkout_url;
        }
      }
    );
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

      {plansQuery.isLoading ? (
        <div className="grid gap-4 md:grid-cols-2">
          <CardSkeleton />
          <CardSkeleton />
        </div>
      ) : null}

      {plansQuery.isError ? (
        <PageState
          title="Erro ao buscar planos"
          description={getApiErrorMessage(plansQuery.error)}
          actionLabel="Tentar novamente"
          onAction={() => plansQuery.refetch()}
        />
      ) : null}

      {plansQuery.data?.length ? (
        <div className="grid gap-4 md:grid-cols-2">
          {plansQuery.data.map((plan) => (
            <Card key={plan.id} className={plan.code === "pro" ? "border-brand" : undefined}>
              <h2 className="font-serif text-3xl">{plan.name}</h2>
              <p className="mt-1 text-2xl font-semibold">
                {plan.is_free ? "R$ 0" : `${formatCurrencyBRL(plan.price_cents / 100)}/${plan.billing_interval}`}
              </p>
              <p className="mt-3 text-sm text-muted">{plan.description ?? "Plano sem descricao."}</p>

              {plan.code === "pro" ? (
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
      ) : null}

      {checkoutMutation.isError ? (
        <div className="rounded-xl border border-danger/30 bg-danger/5 p-3">
          <p className="text-sm text-danger">{getApiErrorMessage(checkoutMutation.error)}</p>
          <Button className="mt-2" variant="ghost" size="sm" onClick={handleUpgrade}>
            Tentar novamente
          </Button>
        </div>
      ) : null}
    </section>
  );
}
