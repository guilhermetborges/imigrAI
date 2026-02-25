"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";

import { AuthGuard } from "@/components/guards/auth-guard";
import { PrivateShell } from "@/components/layout/private-shell";
import { PageState } from "@/components/states/page-state";
import { Card } from "@/components/ui/card";
import { useAuth } from "@/hooks/use-auth";
import { getApiErrorMessage } from "@/lib/api/client";
import { billingApi } from "@/lib/api/endpoints";

export default function DashboardPage(): JSX.Element {
  const { user } = useAuth();

  const entitlementsQuery = useQuery({
    queryKey: ["entitlements", "me"],
    queryFn: billingApi.getMyEntitlements
  });

  return (
    <AuthGuard>
      <PrivateShell>
        {entitlementsQuery.isLoading ? (
          <PageState
            title="Carregando dashboard"
            description="Buscando dados de plano e consumo da sua conta."
          />
        ) : entitlementsQuery.isError ? (
          <PageState
            title="Erro no dashboard"
            description={getApiErrorMessage(entitlementsQuery.error)}
            actionLabel="Tentar novamente"
            onAction={() => entitlementsQuery.refetch()}
          />
        ) : (
          <section className="space-y-4 reveal">
            <Card>
              <p className="text-xs uppercase tracking-[0.18em] text-muted">Dashboard</p>
              <h1 className="mt-2 font-serif text-4xl">Ola, {user?.email}</h1>
              <p className="mt-2 text-sm text-muted">
                Acompanhe plano, limites e acesse rapidamente seus fluxos principais.
              </p>
            </Card>

            <div className="grid gap-4 md:grid-cols-2">
              <Card>
                <h2 className="font-semibold">Plano atual</h2>
                <p className="mt-3 text-2xl font-semibold">
                  {entitlementsQuery.data?.plan?.name ?? "Sem plano ativo"}
                </p>
                <p className="mt-1 text-sm text-muted">
                  Status da assinatura: {entitlementsQuery.data?.subscription?.status ?? "-"}
                </p>
                <Link href="/settings/subscription" className="mt-4 inline-block text-sm font-medium text-brand">
                  Gerenciar assinatura
                </Link>
              </Card>

              <Card>
                <h2 className="font-semibold">Consumo</h2>
                {entitlementsQuery.data?.usage_counters.length ? (
                  <ul className="mt-3 space-y-2 text-sm text-muted">
                    {entitlementsQuery.data.usage_counters.map((counter) => (
                      <li key={counter.id}>
                        {counter.feature_key}: {counter.used_count}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-3 text-sm text-muted">Nenhum contador de uso retornado ainda.</p>
                )}
              </Card>
            </div>

            <Card>
              <h2 className="font-semibold">Atalhos</h2>
              <div className="mt-4 grid gap-2 text-sm md:grid-cols-3">
                <Link className="rounded-xl border border-ink/10 p-3 hover:bg-ink/5" href="/onboarding">
                  Novo onboarding
                </Link>
                <Link className="rounded-xl border border-ink/10 p-3 hover:bg-ink/5" href="/pricing">
                  Ver planos
                </Link>
                <Link
                  className="rounded-xl border border-ink/10 p-3 hover:bg-ink/5"
                  href="/settings/subscription"
                >
                  Configuracoes de assinatura
                </Link>
              </div>
            </Card>
          </section>
        )}
      </PrivateShell>
    </AuthGuard>
  );
}
