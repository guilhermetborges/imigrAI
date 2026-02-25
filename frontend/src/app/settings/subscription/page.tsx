"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";

import { AuthGuard } from "@/components/guards/auth-guard";
import { PrivateShell } from "@/components/layout/private-shell";
import { PageState } from "@/components/states/page-state";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { getApiErrorMessage } from "@/lib/api/client";
import { billingApi } from "@/lib/api/endpoints";
import { formatDate } from "@/lib/formatters";

export default function SubscriptionSettingsPage(): JSX.Element {
  const searchParams = useSearchParams();

  const entitlementsQuery = useQuery({
    queryKey: ["entitlements", "me"],
    queryFn: billingApi.getMyEntitlements
  });

  const checkoutMutation = useMutation({
    mutationFn: async () => {
      if (typeof window === "undefined") {
        return;
      }

      const checkout = await billingApi.createCheckoutSession({
        plan_code: "pro",
        success_url: `${window.location.origin}/settings/subscription?success=1`,
        cancel_url: `${window.location.origin}/settings/subscription?canceled=1`
      });

      window.location.href = checkout.checkout_url;
    }
  });

  const success = searchParams.get("success") === "1";
  const canceled = searchParams.get("canceled") === "1";

  return (
    <AuthGuard>
      <PrivateShell>
        {entitlementsQuery.isLoading ? (
          <PageState
            title="Carregando assinatura"
            description="Consultando plano atual e detalhes da assinatura."
          />
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
                  onClick={() => checkoutMutation.mutate()}
                  disabled={checkoutMutation.isPending}
                >
                  {checkoutMutation.isPending ? "Abrindo checkout..." : "Fazer upgrade para Pro"}
                </Button>
              ) : null}
            </Card>

            <Card>
              <h2 className="font-semibold">Entitlements ativos</h2>
              {entitlementsQuery.data?.entitlements.length ? (
                <ul className="mt-3 space-y-2 text-sm text-muted">
                  {entitlementsQuery.data.entitlements.map((entitlement) => (
                    <li key={entitlement.id}>
                      {entitlement.feature_key} | habilitado: {entitlement.is_enabled ? "sim" : "nao"}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-3 text-sm text-muted">Nenhum entitlement retornado.</p>
              )}
            </Card>

            {checkoutMutation.isError ? (
              <p className="text-sm text-danger">{getApiErrorMessage(checkoutMutation.error)}</p>
            ) : null}
          </section>
        )}
      </PrivateShell>
    </AuthGuard>
  );
}
