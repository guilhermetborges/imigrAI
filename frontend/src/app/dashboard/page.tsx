"use client";

import Link from "next/link";

import { AuthGuard } from "@/components/guards/auth-guard";
import { PrivateShell } from "@/components/layout/private-shell";
import { CardSkeleton, ListSkeleton } from "@/components/states/loading-skeletons";
import { PageState } from "@/components/states/page-state";
import { Card } from "@/components/ui/card";
import { useAssessmentHistory } from "@/hooks/use-assessment";
import { useAuth } from "@/hooks/use-auth";
import { useSubscription } from "@/hooks/use-subscription";
import { getApiErrorMessage } from "@/lib/api/client";
import { formatDate } from "@/lib/formatters";

export default function DashboardPage(): JSX.Element {
  const { user } = useAuth();
  const { entitlementsQuery } = useSubscription();
  const historyQuery = useAssessmentHistory();

  return (
    <AuthGuard>
      <PrivateShell>
        {entitlementsQuery.isLoading || historyQuery.isLoading ? (
          <section className="space-y-4">
            <CardSkeleton />
            <div className="grid gap-4 md:grid-cols-2">
              <CardSkeleton />
              <CardSkeleton />
            </div>
            <ListSkeleton rows={4} />
          </section>
        ) : entitlementsQuery.isError ? (
          <PageState
            title="Erro no dashboard"
            description={getApiErrorMessage(entitlementsQuery.error)}
            actionLabel="Tentar novamente"
            onAction={() => entitlementsQuery.refetch()}
          />
        ) : historyQuery.isError ? (
          <PageState
            title="Erro ao carregar historico"
            description={getApiErrorMessage(historyQuery.error)}
            actionLabel="Tentar novamente"
            onAction={() => historyQuery.refetch()}
          />
        ) : (
          <section className="space-y-4 reveal">
            <Card>
              <p className="text-xs uppercase tracking-[0.18em] text-muted">Dashboard</p>
              <h1 className="mt-2 font-serif text-4xl">Ola, {user?.email}</h1>
              <p className="mt-2 text-sm text-muted">
                Acompanhe plano, limites e avance nos fluxos principais.
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
                <h2 className="font-semibold">Consumo atual</h2>
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
              <h2 className="font-semibold">Historico de assessments</h2>
              {historyQuery.data?.length ? (
                <div className="mt-4 space-y-2">
                  {historyQuery.data.map((item) => (
                    <Link
                      key={item.assessment_id}
                      href={`/results/${item.assessment_id}`}
                      className="block rounded-xl border border-ink/10 bg-white p-3 text-sm hover:bg-ink/5"
                    >
                      <p className="font-medium">Assessment {item.assessment_id.slice(0, 8)}...</p>
                      <p className="mt-1 text-xs text-muted">
                        Status: {item.status} | Criado em {formatDate(item.created_at ?? null)}
                      </p>
                    </Link>
                  ))}
                </div>
              ) : (
                <p className="mt-3 text-sm text-muted">
                  Nenhum assessment encontrado ainda. Comece um novo onboarding.
                </p>
              )}
            </Card>

            <Card>
              <h2 className="font-semibold">Atalhos</h2>
              <div className="mt-4 grid gap-2 text-sm md:grid-cols-3">
                <Link className="rounded-xl border border-ink/10 p-3 hover:bg-ink/5" href="/onboarding">
                  Novo onboarding
                </Link>
                <Link className="rounded-xl border border-ink/10 p-3 hover:bg-ink/5" href="/pricing">
                  Ver planos
                </Link>
                <Link className="rounded-xl border border-ink/10 p-3 hover:bg-ink/5" href="/settings/subscription">
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
