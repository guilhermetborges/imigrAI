"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useMemo } from "react";

import { AuthGuard } from "@/components/guards/auth-guard";
import { PrivateShell } from "@/components/layout/private-shell";
import { PageState } from "@/components/states/page-state";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { getApiErrorMessage } from "@/lib/api/client";
import { assessmentsApi, billingApi, roadmapsApi } from "@/lib/api/endpoints";
import { formatDate, toNumber } from "@/lib/formatters";
import { generateIdempotencyKey } from "@/lib/utils";

interface ResultsPageProps {
  params: {
    assessmentId: string;
  };
}

const terminalStatuses = ["completed", "failed", "canceled"];

export default function ResultsPage({ params }: ResultsPageProps): JSX.Element {
  const router = useRouter();
  const assessmentId = params.assessmentId;

  const assessmentStatusQuery = useQuery({
    queryKey: ["assessment-status", assessmentId],
    queryFn: () => assessmentsApi.getStatus(assessmentId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status && terminalStatuses.includes(status)) {
        return false;
      }
      return 3000;
    }
  });

  const breakdownQuery = useQuery({
    queryKey: ["assessment-breakdown", assessmentId],
    queryFn: () => assessmentsApi.getBreakdown(assessmentId),
    enabled: assessmentStatusQuery.data?.status === "completed"
  });

  const entitlementsQuery = useQuery({
    queryKey: ["entitlements", "me"],
    queryFn: billingApi.getMyEntitlements
  });

  const createRoadmapMutation = useMutation({
    mutationFn: () =>
      roadmapsApi.create({
        assessment_id: assessmentId,
        idempotency_key: generateIdempotencyKey()
      }),
    onSuccess: (data) => {
      router.push(`/roadmaps/${data.roadmap_id}`);
    }
  });

  const canGenerateRoadmap = useMemo(() => {
    return Boolean(
      entitlementsQuery.data?.entitlements.some(
        (entitlement) => entitlement.feature_key === "roadmap.pro" && entitlement.is_enabled
      )
    );
  }, [entitlementsQuery.data]);

  const groupedBreakdown = useMemo(() => {
    if (!breakdownQuery.data) {
      return [];
    }

    const map = new Map<string, { code: string; score: number; applied: number; blocking: number }>();

    for (const item of breakdownQuery.data.items) {
      const current = map.get(item.rule_group_code) ?? {
        code: item.rule_group_code,
        score: 0,
        applied: 0,
        blocking: 0
      };

      current.score += toNumber(item.score_delta);
      current.applied += item.applied ? 1 : 0;
      current.blocking += item.is_blocking ? 1 : 0;
      map.set(item.rule_group_code, current);
    }

    return Array.from(map.values()).sort((a, b) => b.score - a.score);
  }, [breakdownQuery.data]);

  if (assessmentStatusQuery.isLoading) {
    return (
      <AuthGuard>
        <PrivateShell>
          <PageState
            title="Buscando avaliacao"
            description="Carregando status inicial do assessment selecionado."
          />
        </PrivateShell>
      </AuthGuard>
    );
  }

  if (assessmentStatusQuery.isError) {
    return (
      <AuthGuard>
        <PrivateShell>
          <PageState
            title="Falha ao carregar status"
            description={getApiErrorMessage(assessmentStatusQuery.error)}
            actionLabel="Tentar novamente"
            onAction={() => assessmentStatusQuery.refetch()}
          />
        </PrivateShell>
      </AuthGuard>
    );
  }

  const status = assessmentStatusQuery.data?.status;

  if (status && !terminalStatuses.includes(status)) {
    return (
      <AuthGuard>
        <PrivateShell>
          <PageState
            title="Score em processamento"
            description={`Status atual: ${status}. Estamos atualizando automaticamente.`}
          />
        </PrivateShell>
      </AuthGuard>
    );
  }

  if (status === "failed" || status === "canceled") {
    return (
      <AuthGuard>
        <PrivateShell>
          <PageState
            title="Avaliacao nao concluida"
            description={`Status final: ${status}. Revise o onboarding e tente novamente.`}
            actionLabel="Refazer onboarding"
            onAction={() => router.push("/onboarding")}
          />
        </PrivateShell>
      </AuthGuard>
    );
  }

  if (breakdownQuery.isLoading) {
    return (
      <AuthGuard>
        <PrivateShell>
          <PageState
            title="Montando breakdown"
            description="Seu score foi concluido e estamos carregando os criterios detalhados."
          />
        </PrivateShell>
      </AuthGuard>
    );
  }

  if (breakdownQuery.isError || !breakdownQuery.data) {
    return (
      <AuthGuard>
        <PrivateShell>
          <PageState
            title="Nao foi possivel carregar o resultado"
            description={breakdownQuery.isError ? getApiErrorMessage(breakdownQuery.error) : "Sem dados"}
            actionLabel="Atualizar"
            onAction={() => breakdownQuery.refetch()}
          />
        </PrivateShell>
      </AuthGuard>
    );
  }

  if (groupedBreakdown.length === 0) {
    return (
      <AuthGuard>
        <PrivateShell>
          <PageState
            title="Resultado vazio"
            description="A avaliacao foi concluida, mas nao retornou itens de breakdown."
          />
        </PrivateShell>
      </AuthGuard>
    );
  }

  const score = Math.max(0, Math.min(100, toNumber(breakdownQuery.data.score_final)));

  return (
    <AuthGuard>
      <PrivateShell>
        <section className="space-y-4 reveal">
          <Card className="bg-gradient-to-r from-brand-soft via-white to-accent-soft">
            <p className="text-xs uppercase tracking-[0.18em] text-muted">Resultado do score</p>
            <h1 className="mt-2 font-serif text-5xl">{score.toFixed(1)}</h1>
            <p className="mt-2 text-sm text-muted">Faixa: {breakdownQuery.data.faixa}</p>
            <p className="mt-1 text-xs text-muted">
              Ultima atualizacao: {formatDate(assessmentStatusQuery.data?.completed_at ?? null)}
            </p>
          </Card>

          <div className="grid gap-4 lg:grid-cols-[1fr_300px]">
            <Card>
              <h2 className="font-serif text-2xl">Breakdown por criterio</h2>
              <div className="mt-4 space-y-3">
                {groupedBreakdown.map((criterion) => (
                  <div
                    key={criterion.code}
                    className="rounded-xl border border-ink/10 bg-white p-4 text-sm"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <p className="font-semibold">{criterion.code}</p>
                      <p className="text-brand">{criterion.score.toFixed(2)} pts</p>
                    </div>
                    <p className="mt-1 text-xs text-muted">
                      Regras aplicadas: {criterion.applied} | Bloqueios: {criterion.blocking}
                    </p>
                  </div>
                ))}
              </div>
            </Card>

            <div className="space-y-4">
              <Card>
                <h3 className="font-semibold">Gaps criticos</h3>
                {breakdownQuery.data.gaps_criticos.length ? (
                  <ul className="mt-3 space-y-2 text-sm text-muted">
                    {breakdownQuery.data.gaps_criticos.map((gap) => (
                      <li key={gap}>- {gap}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-3 text-sm text-muted">Nenhum gap critico detectado.</p>
                )}
              </Card>

              <Card>
                <h3 className="font-semibold">Proxima acao</h3>
                <p className="mt-2 text-sm text-muted">
                  {canGenerateRoadmap
                    ? "Voce tem acesso Pro para gerar roadmap contextual deste score."
                    : "Roadmap completo disponivel no plano Pro."}
                </p>

                <Button
                  className="mt-4"
                  fullWidth
                  variant={canGenerateRoadmap ? "primary" : "secondary"}
                  disabled={createRoadmapMutation.isPending}
                  onClick={() => {
                    if (!canGenerateRoadmap) {
                      router.push("/pricing");
                      return;
                    }

                    createRoadmapMutation.mutate();
                  }}
                >
                  {canGenerateRoadmap
                    ? createRoadmapMutation.isPending
                      ? "Gerando roadmap..."
                      : "Gerar roadmap Pro"
                    : "Desbloquear roadmap Pro"}
                </Button>

                {createRoadmapMutation.isError ? (
                  <p className="mt-2 text-xs text-danger">
                    {getApiErrorMessage(createRoadmapMutation.error)}
                  </p>
                ) : null}
              </Card>
            </div>
          </div>
        </section>
      </PrivateShell>
    </AuthGuard>
  );
}
