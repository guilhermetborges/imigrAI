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

function getCheckoutLabel(isPending: boolean): string {
  return isPending ? "Abrindo checkout..." : "Fazer upgrade para Pro";
}

export default function SubscriptionSettingsPage(): JSX.Element {
  const searchParams = useSearchParams();
  const { entitlementsQuery, checkoutMutation } = useSubscription();

  const success = searchParams.get("success") === "1";
  const canceled = searchParams.get("canceled") === "1";

  const handleUpgrade = (): void => {
    if (globalThis.window === undefined) {
      return;
    }

    const origin = globalThis.window.location.origin;

    checkoutMutation.mutate(
      {
        planCode: "pro",
        successUrl: `${origin}/settings/subscription?success=1`,
        cancelUrl: `${origin}/settings/subscription?canceled=1`
      },
      {
        onSuccess: (checkout) => {
          globalThis.window.location.href = checkout.checkout_url;
        }
      }
    );
  };

  const plan = entitlementsQuery.data?.plan;
  const subscription = entitlementsQuery.data?.subscription;
  const entitlements = entitlementsQuery.data?.entitlements ?? [];
  const usageCounters = entitlementsQuery.data?.usage_counters ?? [];
  const canUpgrade = !plan || plan.is_free;
  const checkoutLabel = getCheckoutLabel(checkoutMutation.isPending);
  const subscriptionStatus = subscription?.status ?? "-";
  const currentPeriodEnd = formatDate(subscription?.current_period_end ?? null);

  let content: JSX.Element;
  if (entitlementsQuery.isLoading) {
    content = (
      <section className="space-y-4">
        <CardSkeleton />
        <CardSkeleton />
      </section>
    );
  } else if (entitlementsQuery.isError) {
    content = (
      <PageState
        title="Erro ao carregar assinatura"
        description={getApiErrorMessage(entitlementsQuery.error)}
        actionLabel="Tentar novamente"
        onAction={() => entitlementsQuery.refetch()}
      />
    );
  } else {
    content = (
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
          <h1 className="mt-2 font-serif text-4xl">{plan?.name ?? "Plano nao identificado"}</h1>
          <p className="mt-2 text-sm text-muted">Status: {subscriptionStatus}</p>
          <p className="mt-1 text-sm text-muted">Periodo atual ate: {currentPeriodEnd}</p>

          {canUpgrade ? (
            <Button className="mt-6" onClick={handleUpgrade} disabled={checkoutMutation.isPending}>
              {checkoutLabel}
            </Button>
          ) : null}
        </Card>

        <Card>
          <h2 className="font-semibold">Limites e entitlements</h2>
          {entitlements.length ? (
            <ul className="mt-3 space-y-2 text-sm text-muted">
              {entitlements.map((entitlement) => (
                <li key={entitlement.id}>
                  {entitlement.feature_key} | habilitado: {entitlement.is_enabled ? "sim" : "nao"}
                  {entitlement.limit_value === null ? "" : ` | limite: ${entitlement.limit_value}`}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-3 text-sm text-muted">Nenhum entitlement retornado.</p>
          )}

          {usageCounters.length ? (
            <ul className="mt-4 space-y-2 text-sm text-muted">
              {usageCounters.map((counter) => (
                <li key={counter.id}>Uso {counter.feature_key}: {counter.used_count}</li>
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
    );
  }

  return (
    <AuthGuard>
      <PrivateShell>
        {content}
      </PrivateShell>
    </AuthGuard>
  );
}
