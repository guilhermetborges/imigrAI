"use client";

import { useSearchParams } from "next/navigation";

import { AuthGuard } from "@/components/guards/auth-guard";
import { PrivateShell } from "@/components/layout/private-shell";
import { CardSkeleton } from "@/components/states/loading-skeletons";
import { PageState } from "@/components/states/page-state";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useSubscription } from "@/hooks/use-subscription";
import { getApiErrorMessage } from "@/lib/api/client";
import { formatDate } from "@/lib/formatters";

export default function SubscriptionSettingsPage(): JSX.Element {
  const searchParams = useSearchParams();
  const { entitlementsQuery, checkoutMutation } = useSubscription();

  const success = searchParams.get("success") === "1";
  const canceled = searchParams.get("canceled") === "1";

  const handleUpgrade = (): void => {
    if (typeof window === "undefined") {
      return;
    }

    checkoutMutation.mutate(
      {
        planCode: "pro",
        successUrl: `${window.location.origin}/settings/subscription?success=1`,
        cancelUrl: `${window.location.origin}/settings/subscription?canceled=1`
      },
      {
        onSuccess: (checkout) => {
          window.location.href = checkout.checkout_url;
        }
      }
    );
  };

  return (
    <AuthGuard>
      <PrivateShell>
        {entitlementsQuery.isLoading ? (
          <section className="space-y-4">
            <CardSkeleton />
            <CardSkeleton />
          </section>
        ) : entitlementsQuery.isError ? (
          <PageState
            title="Erro ao carregar assinatura"
            description={getApiErrorMessage(entitlementsQuery.error)}
            actionLabel="Tentar novamente"
            onAction={() => entitlementsQuery.refetch()}
          />
        ) : (
          <section className="space-y-4 reveal">
            {success ? (
              <p className="rounded-xl border border-brand/30 bg-brand-soft px-4 py-3 text-sm text-ink">
                Checkout concluido. Atualize em alguns segundos para ver seu novo plano.
              </p>
            ) : null}
            {canceled ? (
              <p className="rounded-xl border border-accent/50 bg-accent-soft px-4 py-3 text-sm text-ink">
                Checkout cancelado. Nenhuma cobranca realizada.
              </p>
            ) : null}

            <Card>
              <p className="text-xs uppercase tracking-[0.18em] text-muted">Assinatura</p>
              <h1 className="mt-2 font-serif text-4xl">
                {entitlementsQuery.data?.plan?.name ?? "Plano nao identificado"}
              </h1>
              <p className="mt-2 text-sm text-muted">
                Status: {entitlementsQuery.data?.subscription?.status ?? "-"}
              </p>
              <p className="mt-1 text-sm text-muted">
                Periodo atual ate: {formatDate(entitlementsQuery.data?.subscription?.current_period_end ?? null)}
              </p>

              {!entitlementsQuery.data?.plan || entitlementsQuery.data.plan.is_free ? (
                <Button
                  className="mt-6"
                  onClick={handleUpgrade}
                  disabled={checkoutMutation.isPending}
                >
                  {checkoutMutation.isPending ? "Abrindo checkout..." : "Fazer upgrade para Pro"}
                </Button>
              ) : null}
            </Card>

            <Card>
              <h2 className="font-semibold">Limites e entitlements</h2>
              {entitlementsQuery.data?.entitlements.length ? (
                <ul className="mt-3 space-y-2 text-sm text-muted">
                  {entitlementsQuery.data.entitlements.map((entitlement) => (
                    <li key={entitlement.id}>
                      {entitlement.feature_key} | habilitado: {entitlement.is_enabled ? "sim" : "nao"}
                      {entitlement.limit_value !== null ? ` | limite: ${entitlement.limit_value}` : ""}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-3 text-sm text-muted">Nenhum entitlement retornado.</p>
              )}

              {entitlementsQuery.data?.usage_counters.length ? (
                <ul className="mt-4 space-y-2 text-sm text-muted">
                  {entitlementsQuery.data.usage_counters.map((counter) => (
                    <li key={counter.id}>
                      Uso {counter.feature_key}: {counter.used_count}
                    </li>
                  ))}
                </ul>
              ) : null}
            </Card>

            {checkoutMutation.isError ? (
              <div className="rounded-xl border border-danger/30 bg-danger/5 p-3">
                <p className="text-sm text-danger">{getApiErrorMessage(checkoutMutation.error)}</p>
                <Button className="mt-2" size="sm" variant="ghost" onClick={handleUpgrade}>
                  Tentar novamente
                </Button>
              </div>
            ) : null}
          </section>
        )}
      </PrivateShell>
    </AuthGuard>
  );
}
